# RouteTrust — Security, Access Control, and Resilience Blueprint

**Document Version:** 1.0.0  
**Target Audience:** Founder, Product Leads, Engineering Team, and External Auditors  
**Scope:** Early-Stage Web Application, FastAPI Backend, Streamlit Presentation Layer, SQLite Ledger, Hugging Face Spaces Deployment  
**Author:** Senior Product Security Engineer  

---

## Executive Summary & Security Philosophy

As an early-stage founder, security often feels like a checklist of expensive enterprise tools, complex identity providers, or paralyzing jargon. In reality, **great security is simply good system design applied with discipline**. Security is about making sure that:
1. People can only do what you intend them to do.
2. Bad data or malicious actors cannot crash your app or steal proprietary data.
3. When things break (and external services like weather APIs or hosting providers eventually will), the system fails safely, gracefully, and informatively rather than silently giving dangerous advice.

RouteTrust is a decision-support platform that tells transit riders when they need to leave to catch their bus or train reliably. In version 1 (v1), the app is deployed in a single container running Streamlit and FastAPI with SQLite. While v1 has zero private user accounts (it is completely anonymous and stateless for public commuters), **security is still paramount**:
* Your internal administration dashboards and machine learning diagnostic logs must never be tampered with or read by the public.
* Bad input (like past timestamps or malicious queries) must not exhaust server memory or crash the single-container backend.
* Your proprietary trained machine learning model artifacts (`.joblib`) and SQLite audit logs must remain tamper-proof.
* As RouteTrust evolves to user accounts, saved commutes, and team roles, the access model must scale cleanly without having to rewrite the database.

This document lays out the security architecture in plain English: how authentication works now and next, what each user role can touch, how we safeguard the database, how the system survives critical failures, and the exact checklist of edge cases you must test before launching.

---

## 1. Authentication Strategy: Right-Sized for Your Stage

### 1.1 The Plain-English Explanation
Authentication answers one simple question: *"Who are you, and how do you prove it?"*

A common trap for non-technical founders is building a heavyweight login system before anyone is even using the core product. If users have to sign up with a password just to check bus departure times, 90% of them will leave immediately.

According to your Product Requirements Document (PRD), **RouteTrust v1 is explicitly stateless for public riders**. This means riders do not need to log in to get a recommendation. However, your platform **does** have two distinct operational areas that require strict protection:
1. **Public Rider Area (Inference Flow):** Anyone can query route recommendations.
2. **Internal Operator & Diagnostics Area:** Only you, your engineers, or your academic/portfolio evaluators should be able to view raw performance metrics, inspect model weights, download system logs, or inspect the underlying SQLite database.

### 1.2 The Strategy: Dual-Track Authentication

To keep v1 lean yet completely secure, we implement a two-tiered authentication architecture:

```
+-----------------------------------------------------------------------------------+
|                                ROUTETRUST GATEWAY                                 |
+-----------------------------------------------------------------------------------+
           |                                                       |
           v                                                       v
 [ Public Commuter Traffic ]                            [ Administrative / Auditor Traffic ]
           |                                                       |
 No Login Required (Zero Friction)                       Cryptographic Bearer Token or API Key
           |                                                       |
 Strict IP Rate-Limiting & Input Validation             Full Access to Calibration & Diagnostics
 (Guards against abuse & scraping)                     (Protected via FastAPI Security Dependencies)
```

1. **For Public Riders (Commuters):**
   * **Mechanism:** Anonymous, stateless requests.
   * **Security Layer:** Cryptographic HTTP headers, anti-bot rate limiting, and strict input validation via FastAPI Pydantic models. We never store personal identifiable information (PII) like names, emails, home addresses, or phone numbers. This drastically reduces your legal risk (GDPR, CCPA) because you cannot lose data you never collected.

2. **For Internal Operators & Evaluators (Admins / Auditors):**
   * **Mechanism:** Pre-shared Cryptographic Secret Keys (Bearer Token Auth via HTTP Headers).
   * **How it works:** When you or an evaluator access private endpoints (like `/api/v1/diagnostics/raw-calibration` or administrative database metrics), the request must include a secret token in the header (`Authorization: Bearer <SECURE_ADMIN_TOKEN>`).
   * **Token Management:** The token is generated using cryptographically secure random bytes (`secrets.token_urlsafe(32)`) and passed into the application runtime via environment variables (`ADMIN_API_KEY`). It is never committed to Git.

### 1.3 The Path to v2: Transitioning to Passwordless Magic Links / OAuth
When RouteTrust introduces saved personal commutes and push notifications in v2, **do not build custom password storage**. Handling passwords safely requires salting, hashing (Argon2/bcrypt), reset workflows, brute-force protections, and Multi-Factor Authentication (MFA).

Instead, RouteTrust will adopt **Passwordless Magic Links** or **OAuth 2.0 (Sign in with Google / Apple)** via standard, battle-tested OpenID Connect (OIDC) providers (e.g., Supabase Auth, Clerk, or Firebase):
* **Why this fits your business:** Users do not want another password to remember. A single-use link sent to their email or a one-click Google login is frictionless and offloads credential theft risk entirely onto third-party infrastructure certified for SOC 2 Type II.

---

## 2. Role-Based Access Control (RBAC) Matrix

To prevent unauthorized actions, the system operates on the **Principle of Least Privilege**: every user and background process has access only to the exact resources strictly necessary to do their job.

### 2.1 The Four System Roles

1. **Anonymous Commuter (Public Rider):** Any person using the web app to find a reliable departure time.
2. **Technical Auditor / Evaluator:** A stakeholder, professor, or partner examining model calibration, pinball-loss metrics, and dataset provenance without administrative control.
3. **System Administrator (Founder / DevOps):** You and trusted engineers who control deployments, update baseline route schedules, trigger retraining, and inspect error logs.
4. **Internal Microservice (FastAPI Backend / Streamlit Runner):** The automated code running inside the container that reads databases, calls weather APIs, and executes machine learning inference.

### 2.2 Permissions Matrix

The table below details exactly what each role **can** and **cannot** do:

| System Resource / Action | Anonymous Commuter | Technical Auditor | System Administrator | Internal Service (Backend) |
|---|:---:|:---:|:---:|:---:|
| **Query Leave-By Recommendation** (`/api/v1/optimize-decision`) | Allowed (Rate-limited) | Allowed | Allowed | Allowed |
| **View Route Reliability Grade (A-F)** | Allowed | Allowed | Allowed | Allowed |
| **Inspect Feature Importance & Baseline Loss** (`/diagnostics`) | Denied (Aggregated UI only) | Allowed (Detailed view) | Allowed | Allowed |
| **Download Historical GTFS-RT Parquet Files** | Denied | Allowed (Read-only) | Allowed | Allowed |
| **Inspect Raw `inference_logs` Table** | Denied | Denied (Privacy/Tamper) | Allowed | Read / Append |
| **Insert / Update / Delete `routes_stops`** | Denied | Denied | Allowed | System Seed Only |
| **Trigger Model Retraining / Reload Weights** | Denied | Denied | Allowed | Denied |
| **Read Server Environment Variables (`.env`)** | Denied | Denied | Allowed (Via host only) | Read-only at boot |
| **Direct Shell Access to Docker Container** | Denied | Denied | Allowed (SSH/Console) | Denied |

### 2.3 Explicit "Can and Cannot Do" Rules in Plain English

#### Anonymous Commuter
* **CAN:** Select any existing transit route and stop from the dropdown; request a calculated departure time for a future hour today; view the calculated risk grade (A through F); view system warnings (e.g., if weather fallback is active or the route has low sample counts).
* **CANNOT:** View internal database IDs; view other people's query history; make more than 60 requests per minute; write or alter anything in the database; access debug tracebacks if an error occurs.

#### Technical Auditor
* **CAN:** View the complete calibration curve (how well predicted quantiles match actual delay rates); inspect the pinball-loss comparison against the groupby-median baseline; view feature importance charts; verify that chronological holdout splits were used.
* **CANNOT:** Modify model artifacts (`model_q*.joblib`); delete historical query logs; execute arbitrary database queries; view server secrets or hosting configuration keys.

#### System Administrator
* **CAN:** Deploy new Docker images; inspect container health and resource usage; rotate API keys; trigger manual database backups; seed new transit schedules into `routes_stops`; update fallback weather tables.
* **CANNOT:** Bypass audit logging for system modifications; hardcode administrative credentials into source code.

#### Internal Service (Backend / Machine Learning Pipeline)
* **CAN:** Read model artifacts from disk; execute SQL queries against SQLite; append new inference records into `inference_logs`; call external weather APIs with strict timeouts.
* **CANNOT:** Execute shell commands outside its container; modify its own code files at runtime; expose internal port 8000 directly to the public internet (all traffic must flow through verified application handlers).

---

## 3. Row-Level Security (RLS) & Database Isolation Rules

### 3.1 What is Row-Level Security (RLS)?
Imagine a filing cabinet where everyone puts their paperwork into the same drawer. Without security, opening the drawer lets anyone see everyone else's documents. **Row-Level Security (RLS)** is like putting a physical lock on every single folder inside the drawer. Even if a user can open the cabinet, the database engine checks: *"Does this specific user have the key to open this specific folder?"*

### 3.2 The SQLite Architectural Reality
RouteTrust uses **SQLite in WAL (Write-Ahead Logging) mode** inside a single Docker container. Unlike multi-tenant PostgreSQL, SQLite does not have a native, built-in SQL `ENABLE ROW LEVEL SECURITY` engine. 

Therefore, in RouteTrust, **security isolation is enforced at the Data Access Layer (FastAPI + SQLAlchemy 2.0 ORM)**. This is a battle-tested software engineering pattern where all database queries must pass through secure query builders that automatically enforce isolation.

### 3.3 The Three Core Tables & Their Isolation Rules

```
+---------------------------------------------------------------------------------------+
|                                SQLITE DATABASE ENGINE                                 |
+---------------------------------------------------------------------------------------+
|  TABLE: routes_stops          |  TABLE: weather_fallbacks    |  TABLE: inference_logs |
|  - PUBLIC READ-ONLY           |  - INTERNAL SYSTEM ONLY      |  - APPEND-ONLY LEDGER  |
|  - Controlled by Admin Seed   |  - Read by Weather Service   |  - Blind to Commuters  |
+---------------------------------------------------------------------------------------+
```

#### Rule 1: Public Route Table (`routes_stops`) — Read-Only Isolation
* **Access Mode:** Universally readable by all users and services, but strictly **immutable** at runtime.
* **Database Constraint:** Normal API connections open SQLite with the read-only flag (`sqlite3.connect('file:routetrust.db?mode=ro', uri=True)`) or execute queries using SQLAlchemy sessions configured with `autocommit=False` and zero update methods exposed on public routes.
* **Enforcement:** No commuter query can pass an `UPDATE`, `INSERT`, or `DELETE` statement. Only administrative migration scripts executed during deployment (`start.sh`) can alter this table.

#### Rule 2: Weather Cache Table (`weather_fallbacks`) — Service-Isolated
* **Access Mode:** Internal system use only.
* **Enforcement:** This table contains precomputed historical weather medians. It is never queried directly based on raw commuter input. The internal `weather.py` service looks up entries strictly by `(route_stop_id, month, hour)` derived from validated server timestamps, preventing commuters from injecting unexpected queries.

#### Rule 3: Decision Audit Table (`inference_logs`) — Write-Only / Append-Only Ledger
* **Access Mode:** Public users can write to it indirectly via predictions, but **can never read from it**.
* **The "Blind Ledger" Principle:** When a commuter asks for a leave-by time, the server writes a log entry containing the input parameters, model predictions, and calculated delay. However, the commuter is only returned the current calculation response in memory. They cannot query past entries, search by `request_uuid`, or enumerate other riders' commutes.
* **Tamper Prevention:** The database connection used by the inference API is granted `INSERT` rights only on this table. `UPDATE` and `DELETE` queries are banned in the application layer. This guarantees that your model calibration audit trail cannot be manipulated or erased after the fact.

#### Rule 4: Preparation for Multi-Tenant User Commutes (v2 Schema)
When RouteTrust introduces saved user accounts, the database schema will require an explicit `user_id` foreign key on every personal record:

```sql
-- Architectural Requirement for v2 Personalization
CREATE TABLE user_saved_commutes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(64) NOT NULL,
    route_stop_id INTEGER NOT NULL REFERENCES routes_stops(id),
    target_arrival_time TIME NOT NULL,
    risk_alpha FLOAT NOT NULL DEFAULT 0.10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**The SQLAlchemy Scoping Rule:**
Every query fetching saved commutes must be hard-scoped to the authenticated session user:
```python
# Application-Enforced Isolation
def get_user_commutes(db: Session, authenticated_user_id: str):
    return db.query(UserSavedCommute).filter(
        UserSavedCommute.user_id == authenticated_user_id  # Mandatory tenant filter
    ).all()
```
*A user can never query saved commutes without this filter, completely eliminating Cross-Tenant Data Leaks.*

---

## 4. Complete Error Handling & Resilience Guide

### 4.1 Security Principle: Safe Failure Without Data Leakage
When software encounters an unexpected condition (a network drops, a file is missing, or a number is invalid), it can fail in two ways:
1. **Unsafe Failure:** The server crashes, displays an ugly red screen showing Python code, database passwords, and server file paths, or silently guesses a bad answer that strands a commuter.
2. **Safe Failure (RouteTrust Standard):** The system detects the anomaly immediately, falls back to a safe backup state, logs the full technical diagnostic internally for the engineers, and displays a calm, polite, plain-English message to the user.

### 4.2 Error Handling Matrix for All Major Failure Points

| Failure Point | Root Cause | Impact | System Defensive Action | What the User Sees |
|---|---|---|---|---|
| **1. Weather API Down / Rate-Limited** | Open-Meteo returns HTTP 429, 500, or times out after 2.0 seconds. | Live weather data unavailable for ML delay prediction. | 1. Catch `httpx.TimeoutException`.<br>2. Fall back to `weather_fallbacks` table using route/month/hour median.<br>3. Tag inference record as `historical_fallback`. | Leave-by time is displayed normally, with an inline badge: *"Weather estimated from historical averages."* |
| **2. Target Arrival Time in the Past** | User's phone clock is desynchronized, or user picked 8:00 AM at 9:15 AM. | Negative travel duration; mathematical impossibility. | 1. FastAPI Pydantic validator catches `required_arrival_time <= current_time`.<br>2. Rejects request with HTTP 422 Unprocessable Entity before calling ML models. | *"Please pick a future arrival time. We cannot calculate travel for trips that have already passed."* |
| **3. Machine Learning Quantile Crossing** | Random tree noise produces $Q_{0.90} < Q_{0.50}$ under weird weather conditions. | Corrupted confidence calculations and illogical risk advice. | 1. Backend executes Monotonic Rearrangement: $\mathbf{Q}^* = 	ext{sort}([Q_{0.10}, Q_{0.50}, Q_{0.90}])$.<br>2. Logs calibration anomaly to internal metrics. | Rider sees a mathematically guaranteed, physically coherent leave-by time. No error shown. |
| **4. Early Departure Guard Triggered** | Aggressive negative delay (bus running super early) causes leave-by to be later than scheduled departure. | Rider misses their bus because they were told to leave too late. | 1. Early Departure Guard clamps the leave-by time: $	ext{leave\_by} = \min(	ext{leave\_by}_{	ext{raw}}, t_{	ext{arrive}} - S)$.<br>2. Sets `guard_triggered = TRUE`. | Clear inline advisory: *"Conservative departure buffer applied to ensure you don't miss an early-running vehicle."* |
| **5. Model Artifact Corrupted / Missing** | Disk read error or missing `.joblib` file in single container. | The inference engine cannot compute predictions. | 1. Application boot check verifies all 3 models exist.<br>2. If missing at runtime, log high-severity alert.<br>3. Return HTTP 503 Service Unavailable. | *"Our prediction engine is temporarily undergoing maintenance. Please check back in a few minutes."* |
| **6. SQLite Database Locked** | Concurrent write collision during burst traffic. | Unable to append transaction to `inference_logs`. | 1. SQLite configured with WAL mode and `timeout=15.0`.<br>2. If locked, catch exception, return inference result to user immediately, and queue log write asynchronously. | Commuter gets their departure time instantly without delay. User experience is never blocked by logging. |
| **7. Malicious SQL / Script Injection Attempt** | Attacker enters `'; DROP TABLE routes; --` into route search. | Risk of database corruption or arbitrary code execution. | 1. Input must match strict regex schema (alphanumeric route codes).<br>2. SQLAlchemy uses parameterized prepared statements. | Input rejected with HTTP 400: *"Invalid route identifier format."* |
| **8. Memory Exhaustion / Denial of Service** | Bot script floods API with 10,000 rapid requests. | Container runs out of RAM, crashing both API and UI. | 1. In-memory IP rate limiter throttles client to 60 requests/minute.<br>2. Returns HTTP 429 Too Many Requests. | *"You have checked routes too many times recently. Please wait 60 seconds before trying again."* |

---

## 5. Pre-Launch Edge Case & Security Checklist

Before you announce RouteTrust to public commuters, academic reviewers, or investors, run through this comprehensive pre-launch checklist. Every single item must be verified in your staging or testing environment.

### 5.1 Temporal & Timezone Edge Cases
- [ ] **Midnight Journey Wrap-Around:** If a user queries at 11:45 PM for an arrival time of 12:15 AM the next morning, verify that the calculation correctly handles the date change rather than interpreting it as 23 hours in the past.
- [ ] **Daylight Saving Time (DST) Transition:** Test trips planned across the 2:00 AM clock shift (spring forward / fall back) to ensure time differences are calculated using absolute UTC timestamps before converting to local display time.
- [ ] **Client vs. Server Clock Drift:** Ensure that arrival times are validated against the server's authoritative UTC clock, not the user's browser clock (which can be set incorrectly by the user).

### 5.2 Transit & Operational Edge Cases
- [ ] **Low-Sample Route Flagging:** Verify that routes with fewer than 30 historical data rows (`sample_count < 30`) still provide a recommendation, but clearly display the `confidence: low` badge as mandated by the PRD.
- [ ] **Severe Weather Outliers:** Test model behavior with extreme weather inputs (e.g., 50 mm/hr torrential rain, -20°C temperatures). Verify that predictions do not produce infinite (`Inf`) or `NaN` values, and that monotonic sorting holds.
- [ ] **Zero-Length or Instant Journeys:** If a user accidentally selects the origin terminal as their destination stop, the system must reject it with a friendly notification rather than calculating a 0-second journey with broken division.

### 5.3 Infrastructure, Container & Network Security
- [ ] **Debug Mode Disabled (`DEBUG=false`):** Verify that FastAPI does not run with reload mode in production and that Streamlit does not show interactive developer tracebacks on errors.
- [ ] **Secret Hygiene:** Confirm that `.env` is listed in `.gitignore` and that no API keys or private tokens are hardcoded inside Git history.
- [ ] **Port Isolation:** In the Docker container, confirm that only the Streamlit UI port (port 7860 on Hugging Face) is exposed to the public web. The FastAPI backend (port 8000) should bind only to `127.0.0.1` (localhost) so that external attackers cannot bypass the frontend UI or hit raw endpoints directly unless intentionally routed.
- [ ] **Read-Only Container Filesystem (Where Applicable):** Ensure that the machine learning model files (`artifacts/*.joblib`) have file permissions set to read-only (`chmod 444`) so that an exploited process cannot overwrite or poison the trained models.
- [ ] **Graceful Degradation Drill:** Manually disconnect internet access or block the Open-Meteo URL in your test environment. Confirm that the app seamlessly switches to `weather_fallbacks` without showing a single error popup.

---

## 6. Security Architecture Blueprint Diagram

Below is the complete data flow and security boundary map for RouteTrust:

```
                      +------------------------------------------+
                      |         PUBLIC INTERNET (Commuter)       |
                      +------------------------------------------+
                                           |
                                    HTTPS Port 7860
                                           |
                      +--------------------v---------------------+
                      |       DOCKER CONTAINER BOUNDARY          |
                      |                                          |
                      |   +----------------------------------+   |
                      |   |    Streamlit Frontend (UI)       |   |
                      |   |    - Input Sanitization          |   |
                      |   |    - Friendly Error Display      |   |
                      |   +----------------------------------+   |
                      |                    |                     |
                      |            Loopback HTTP (127.0.0.1)     |
                      |                    |                     |
                      |   +----------------v------------------+  |
                      |   |      FastAPI Backend Engine       |  |
                      |   |  - Pydantic Schema Validation     |  |
                      |   |  - Bearer Token Auth (Admin Only) |  |
                      |   |  - IP Rate Limiting Engine        |  |
                      |   |  - Monotonic Quantile Sorter      |  |
                      |   |  - Early Departure Guard Clamp    |  |
                      |   +----------------------------------+  |
                      |          |                     |         |
                      |          v                     v         |
                      |  +---------------+     +--------------+  |
                      |  | SQLite (WAL)  |     | ML Artifacts |  |
                      |  | - routes_stop |     | - q10,50,90  |  |
                      |  | - fallback_wx |     | - Read-Only  |  |
                      |  | - audit_logs  |     +--------------+  |
                      |  +---------------+                       |
                      +------------------------------------------+
                                         |
                               External HTTPS (2.0s timeout)
                                         v
                      +------------------------------------------+
                      |       Open-Meteo Weather Service         |
                      +------------------------------------------+
```

---

## 7. Founder Action Plan: Immediate Next Steps

To implement this security and access architecture without slowing down your build schedule, execute these steps in order:

1. **Step 1 (Day 1): Environment Configuration**
   * Set your `SECRET_KEY` and `ADMIN_API_KEY` in Hugging Face Spaces Secrets or your local `.env` file.
   * Ensure `DEBUG=false` is enforced in production code.

2. **Step 2 (Day 2): FastAPI Dependency Shields**
   * Wrap administrative diagnostics routes with a FastAPI dependency that checks the `Authorization` header.
   * Wrap the prediction route with Pydantic validation rules that catch invalid or past timestamps immediately.

3. **Step 3 (Day 3): Resilience & Fallback Verification**
   * Test the Open-Meteo 2.0-second timeout mechanism by temporarily giving it an invalid domain.
   * Verify that the database falls back to historical median weather and displays the inline badge.
   * Verify that monotonic sorting guarantees $Q_{0.10} \le Q_{0.50} \le Q_{0.90}$ on every single run.

---
*End of Document. Maintain this document alongside your Technical Architecture and Product Requirements Documents.*