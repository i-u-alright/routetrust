# RouteTrust — Complete Feature Ticket Backlog & AI Implementation Prompts

**Document Version:** 1.0.0  
**Role:** Senior Engineering Lead / Systems Architect  
**Project:** RouteTrust — Probabilistic Transit Reliability & Leave-By Advisor  
**Target Runtime:** FastAPI (Python 3.11) + Streamlit Web Client + SQLite (WAL Mode)  
**Deployment Target:** Single Docker Container on Hugging Face Spaces (Port 7860)  

---

## Ticket Overview & Dependency Flow

```
+-----------------------------------------------------------------------------------------------+
|                                      ARCHITECTURE & TICKETS                                    |
+-----------------------------------------------------------------------------------------------+
|  [TICK-001] SQLite Database & Schema (WAL Mode)                                              |
|      |                                                                                        |
|      +---> [TICK-002] GTFS-RT & Open-Meteo Data Ingestion Pipeline                            |
|      |         |                                                                              |
|      |         +---> [TICK-003] ML Quantile Regressors & Chronological Holdout                |
|      |                   |                                                                    |
|      +-------------------+---> [TICK-004] Quantile Postprocessing & Optimizer Engine          |
|      |                             |                                                          |
|      +---> [TICK-005] Async Open-Meteo Weather Service with Fallback                          |
|                |                   |                                                          |
|                +-------------------+---> [TICK-006] FastAPI Core Endpoints & Pydantic V2      |
|                                              |                                                |
|                                              +---> [TICK-007] Security, Rate Limit & Admin   |
|                                              |                                                |
|                                              +---> [TICK-008] Streamlit Input Controls        |
|                                              |         |                                      |
|                                              +---------+---> [TICK-009] Streamlit Decision Card|
|                                              |                   |                            |
|                                              +-------------------+---> [TICK-010] Diagnostics |
|                                                                            |                  |
|                                              +-----------------------------+                  |
|                                              |                                                |
|                                              v                                                |
|                                   [TICK-011] Docker & Orchestration (start.sh)                |
|                                              |                                                |
|                                              v                                                |
|                                   [TICK-012] End-to-End Test Suite & Edge Cases               |
|                                              |                                                |
|                                              v                                                |
|                                   [TICK-013 & TICK-014] Advanced / Future Features (v2)        |
+-----------------------------------------------------------------------------------------------+
```

---

## Must-Have Tickets (Launch Critical)

### TICK-001: SQLite Database Architecture, ORM Models & Seeding Framework
* **Feature Name:** SQLite Database Layer & Schema Initialization
* **Priority:** Must-have for launch
* **Dependencies:** None (Foundation Ticket)
* **Description:**  
  Set up the persistence layer using SQLite configured with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) and SQLAlchemy 2.0 ORM models. Create three core tables: `routes_stops` (catalog of transit segments with sample counts), `weather_fallbacks` (precomputed monthly/hourly medians for offline resilience), and `inference_logs` (immutable append-only decision ledger). Implement an automated initialization script (`src/db/init_db.py`) that creates tables and seeds seed data if absent.
* **Acceptance Criteria:**
  1. `src/db/session.py` initializes a thread-safe SQLAlchemy 2.0 engine connected to `sqlite:///./routetrust.db` with `PRAGMA journal_mode=WAL;` and `busy_timeout=15000`.
  2. `src/db/models.py` defines `RouteStop`, `WeatherFallback`, and `InferenceLog` matching all field types, constraints, and indexes specified in the Technical Architecture.
  3. `is_low_sample` is automatically computed as `True` when `sample_count < 30`.
  4. `src/db/init_db.py` can be executed idempotently via `python -m src.db.init_db`, ensuring tables and seed records are created without duplicating entries.
* **AI Coding Prompt:**
  ```text
  You are an expert Python backend engineer. Implement the persistence layer for RouteTrust using SQLAlchemy 2.0 and SQLite in WAL mode.
  
  Create the following files:
  1. `src/db/session.py`:
     - Initialize SQLAlchemy `create_engine` with SQLite URL `sqlite:///./routetrust.db`.
     - Configure SQLite pragmas on connection: `PRAGMA journal_mode=WAL;`, `PRAGMA synchronous=NORMAL;`, `PRAGMA busy_timeout=15000;`.
     - Export `SessionLocal` and a FastAPI dependency generator `get_db()`.
  
  2. `src/db/models.py`:
     - Base = declarative_base()
     - Model `RouteStop`:
       - `id`: Integer PK autoincrement
       - `route_id`: String(64), indexed, nullable=False
       - `stop_id`: String(64), indexed, nullable=False
       - `route_short_name`: String(128), nullable=False
       - `stop_name`: String(256), nullable=False
       - `scheduled_travel_time_sec`: Integer, nullable=False
       - `sample_count`: Integer, default=0, nullable=False
       - `is_low_sample`: Boolean, default=False, nullable=False
       - `created_at`: DateTime UTC default
     - Model `WeatherFallback`:
       - `id`: Integer PK autoincrement
       - `route_stop_id`: Integer, ForeignKey('routes_stops.id'), indexed, nullable=False
       - `month`: SmallInteger (1-12), nullable=False
       - `hour`: SmallInteger (0-23), nullable=False
       - `median_precipitation_mm`: Float, default=0.0, nullable=False
       - `median_apparent_temperature_c`: Float, nullable=False
       - `median_wind_speed_kmh`: Float, nullable=False
     - Model `InferenceLog`:
       - `id`: Integer PK autoincrement
       - `request_uuid`: String(36), unique, indexed, nullable=False
       - `route_stop_id`: Integer, ForeignKey('routes_stops.id'), nullable=False
       - `required_arrival_time`: DateTime, nullable=False
       - `alpha`: Float, nullable=False
       - `raw_q10_delay_sec`: Float, nullable=False
       - `raw_q50_delay_sec`: Float, nullable=False
       - `raw_q90_delay_sec`: Float, nullable=False
       - `adjusted_q_delay_sec`: Float, nullable=False
       - `recommended_leave_by`: DateTime, nullable=False
       - `reliability_grade`: String(2), nullable=False
       - `weather_source`: String(32), nullable=False
       - `guard_triggered`: Boolean, default=False, nullable=False
       - `low_confidence_flag`: Boolean, default=False, nullable=False
       - `latency_ms`: Float, nullable=False
       - `created_at`: DateTime UTC default
  
  3. `src/db/init_db.py`:
     - Script that creates all tables using `Base.metadata.create_all(bind=engine)`.
     - Populates initial realistic mock/seed rows for at least 4 route stops (including 1 low-sample route with sample_count=22 and 3 normal routes with sample_count > 1000).
     - Populates 24-hour historical weather fallbacks for September for each seeded route stop.
     - Is idempotent: checks if rows exist before inserting.
  
  Follow strict typing, SQLAlchemy 2.0 syntax, and robust error handling.
  ```

---

### TICK-002: Transit Archive Processing & Feature Engineering Pipeline
* **Feature Name:** GTFS-RT Archive Cleaning & Feature Preparation Pipeline
* **Priority:** Must-have for launch
* **Dependencies:** TICK-001
* **Description:**  
  Build the offline data processing and feature engineering script (`src/ml/features.py`) that loads raw transit records (e.g. Parquet extracts from traines.eu / TfNSW) and joins them with historical Open-Meteo weather records. Build the feature transformation pipeline (handling categorical encoding, cyclic hour/day transforms, and scheduled duration) and export clean datasets for training and holdout evaluation.
* **Acceptance Criteria:**
  1. Script loads raw transit parquet data and filters out corrupted or negative travel duration records.
  2. Features engineered: `scheduled_travel_time_sec`, `hour_of_day`, `day_of_week`, `precipitation_mm`, `apparent_temperature_c`, `wind_speed_kmh`.
  3. Target variable `delay_sec` computed cleanly as $	ext{actual\_arrival} - 	ext{scheduled\_arrival}$.
  4. Train/test split uses **strictly chronological ordering** (earliest 80% train, latest 20% test holdout). Zero random shuffling to prevent temporal data leakage.
  5. Exports `feature_pipeline.joblib` containing scikit-learn transformers / column transformers.
* **AI Coding Prompt:**
  ```text
  You are an expert ML data engineer. Implement `src/ml/features.py` for RouteTrust.
  
  Requirements:
  1. Load raw transit records from `data/raw/gtfs_rt_archive.parquet` (or generate synthetic representative transit delay data if file is absent for local dev).
  2. Synthesize or join hourly historical weather variables: precipitation (mm), apparent temperature (°C), wind speed (km/h).
  3. Feature set:
     - `scheduled_travel_time_sec` (int/float)
     - `hour_of_day` (0-23)
     - `day_of_week` (0-6)
     - `precipitation_mm` (float >= 0)
     - `apparent_temperature_c` (float)
     - `wind_speed_kmh` (float >= 0)
     - `route_stop_id` (categorical / int)
  4. Chronological Holdout Split:
     - Sort dataset strictly by timestamp ascending.
     - Split first 80% into `train_df`, last 20% into `holdout_df`.
     - Add assertion verifying `train_df['timestamp'].max() <= holdout_df['timestamp'].min()`.
  5. Fit a Scikit-Learn `ColumnTransformer` or Pipeline (`feature_pipeline.joblib`) that processes numerical features and standard encodings.
  6. Save clean training and test matrices to `data/processed/`.
  Provide clean CLI execution (`python -m src.ml.features`).
  ```

---

### TICK-003: Multi-Quantile LightGBM Regressors & Model Training
* **Feature Name:** LightGBM Quantile Delay Models ($	au \in \{0.10, 0.50, 0.90\}$)
* **Priority:** Must-have for launch
* **Dependencies:** TICK-002
* **Description:**  
  Train three independent LightGBM gradient-boosted decision trees optimizing pinball loss (`objective="quantile"`, `alpha=tau`) for $	au \in \{0.10, 0.50, 0.90\}$. Evaluate empirical quantile coverage on the holdout set, compare model pinball loss against a groupby-median baseline (verifying $\ge 10\%$ loss reduction), and serialize model artifacts (`model_q10.joblib`, `model_q50.joblib`, `model_q90.joblib`) and `metadata.json` into `artifacts/`.
* **Acceptance Criteria:**
  1. LightGBM models trained with hyperparameters suited for tabular data (e.g. `n_estimators=150`, `learning_rate=0.05`, `max_depth=6`).
  2. Pinball loss computed for each quantile $	au$: $L_	au(y, \hat{y}) = rac{1}{N}\sum \max(	au(y - \hat{y}), (1 - 	au)(\hat{y} - y))$.
  3. Holdout empirical coverage validated: $	au=0.10 \in [0.05, 0.15]$, $	au=0.50 \in [0.45, 0.55]$, $	au=0.90 \in [0.85, 0.95]$.
  4. Models show $\ge 10\%$ pinball loss improvement over naive route/hour median baseline.
  5. Serializes `artifacts/model_q10.joblib`, `model_q50.joblib`, `model_q90.joblib`, and `metadata.json` containing holdout loss, feature importances, and training timestamp.
* **AI Coding Prompt:**
  ```text
  You are an applied ML engineer specializing in quantile regression. Implement `src/ml/train.py` and `src/ml/evaluate.py` for RouteTrust.
  
  Requirements:
  1. Train 3 `lightgbm.LGBMRegressor` models:
     - Model 1: `objective='quantile'`, `alpha=0.10`
     - Model 2: `objective='quantile'`, `alpha=0.50`
     - Model 3: `objective='quantile'`, `alpha=0.90`
  2. Implement baseline: calculate median delay grouped by `(route_stop_id, hour_of_day)`.
  3. Calculate Pinball loss for both LightGBM models and the baseline on the chronological holdout set.
  4. Calculate Empirical Coverage: fraction of actual holdout delays where $y \le \hat{y}_	au$.
  5. Verify that LightGBM achieves >= 10% pinball loss reduction over baseline.
  6. Compute feature importances (gain-based) for the models.
  7. Save models using `joblib.dump()` to:
     - `artifacts/model_q10.joblib`
     - `artifacts/model_q50.joblib`
     - `artifacts/model_q90.joblib`
  8. Save `artifacts/metadata.json` with structure:
     {
       "model_version": "1.2.0-lightgbm",
       "training_timestamp": "<ISO-UTC>",
       "metrics": {
         "pinball_loss": { "model_loss": float, "baseline_loss": float, "improvement_percentage": float },
         "coverage_calibration": { "q10": float, "q50": float, "q90": float }
       },
       "feature_importance": [{"feature": str, "importance_score": float}],
       "provenance": {"source": "traines.eu GTFS-RT", "split": "chronological_holdout_non_shuffled"}
     }
  Ensure deterministic seeds and clean execution via `python -m src.ml.train`.
  ```

---

### TICK-004: Quantile Postprocessing & Chance-Constrained Optimizer
* **Feature Name:** Monotonic Rearrangement, Leave-By Calculation & Early Departure Guard
* **Priority:** Must-have for launch
* **Dependencies:** TICK-003
* **Description:**  
  Implement the core mathematical decision engine in `src/ml/postprocess.py` and `src/services/decision_optimizer.py`. This includes monotonic rearrangement to prevent quantile crossing ($\mathbf{Q}^* = 	ext{sort}([\hat{Q}_{0.10}, \hat{Q}_{0.50}, \hat{Q}_{0.90}])$), mapping user risk tolerance $lpha \in \{0.20, 0.10, 0.05\}$ to the appropriate upper quantile ($1-lpha$), calculating the chance-constrained leave-by time, applying the early departure guard clamp, and deriving the dynamic reliability grade ($A-F$) from normalized interquantile spread.
* **Acceptance Criteria:**
  1. Monotonic Rearrangement guarantees $\hat{Q}^*_{0.10} \le \hat{Q}^*_{0.50} \le \hat{Q}^*_{0.90}$ under any input perturbation.
  2. Alpha mapping: $lpha=0.20 	o \hat{Q}_{0.50} 	ext{ (or interpolated)}$, $lpha=0.10 	o \hat{Q}_{0.90}$, $lpha=0.05 	o \hat{Q}_{0.90} 	imes 1.25$ (or extreme upper buffer).
  3. Formula: $	ext{leave\_by}_{	ext{raw}} = t_{	ext{arrive}} - S - \hat{Q}_{1-lpha}(	ext{delay}\mid x)$.
  4. Early Departure Guard: If $	ext{leave\_by}_{	ext{raw}} > t_{	ext{arrive}} - S$, clamp $	ext{leave\_by}_{	ext{final}} = t_{	ext{arrive}} - S$ and set `guard_triggered = True`.
  5. Normalized Spread: $	ext{Spread} = (\hat{Q}^*_{0.90} - \hat{Q}^*_{0.10}) / \max(\hat{Q}^*_{0.50}, 60.0)$.
  6. Reliability Grade Buckets:
     - Grade A: $	ext{Spread} \le 0.15$
     - Grade B: $0.15 < 	ext{Spread} \le 0.30$
     - Grade C: $0.30 < 	ext{Spread} \le 0.50$
     - Grade D: $0.50 < 	ext{Spread} \le 0.75$
     - Grade F: $	ext{Spread} > 0.75$
* **AI Coding Prompt:**
  ```text
  You are a senior algorithmic software engineer. Implement `src/ml/postprocess.py` and `src/services/decision_optimizer.py`.
  
  Functions to implement:
  1. `enforce_monotonic_quantiles(q10: float, q50: float, q90: float) -> Tuple[float, float, float]`:
     - Returns sorted tuple so that q10 <= q50 <= q90.
  
  2. `compute_reliability_grade(q10: float, q50: float, q90: float) -> Tuple[str, float]`:
     - Spread = (q90 - q10) / max(q50, 60.0)  # Avoid div by zero or negative
     - Return (grade, spread) where:
       Spread <= 0.15 -> 'A'
       0.15 < Spread <= 0.30 -> 'B'
       0.30 < Spread <= 0.50 -> 'C'
       0.50 < Spread <= 0.75 -> 'D'
       Spread > 0.75 -> 'F'
  
  3. `calculate_leave_by(target_arrival: datetime, scheduled_travel_sec: int, risk_delay_sec: float) -> Tuple[datetime, bool]`:
     - raw_leave_by = target_arrival - timedelta(seconds=(scheduled_travel_sec + risk_delay_sec))
     - scheduled_departure = target_arrival - timedelta(seconds=scheduled_travel_sec)
     - If raw_leave_by > scheduled_departure:
         return scheduled_departure, True (guard triggered)
     - Else:
         return raw_leave_by, False (normal)
  
  4. `optimize_commute_decision(...) -> DecisionResult`:
     - Integrates model prediction loading, monotonic ordering, alpha quantile selection, leave-by clamping, and grade assignment.
  
  Add comprehensive unit test assertions in a test block at the bottom.
  ```

---

### TICK-005: Async Weather Ingestion Service with SQLite Fallback Cache
* **Feature Name:** Resilient Open-Meteo Weather Service & Median Fallback
* **Priority:** Must-have for launch
* **Dependencies:** TICK-001
* **Description:**  
  Build the external weather client in `src/services/weather.py` using `httpx.AsyncClient`. Call the Open-Meteo API for real-time precipitation, apparent temperature, and wind speed at stop coordinates. Enforce a strict **2.0-second connection timeout**. If the API fails, times out, or returns 4xx/5xx, seamlessly query the `weather_fallbacks` SQLite table for the route/stop’s historical monthly/hourly median and tag the response `weather_source = "historical_fallback"`. Never crash or default to dummy zero-weather without tagging.
* **Acceptance Criteria:**
  1. `get_weather(latitude: float, longitude: float, route_stop_id: int, target_time: datetime, db: Session)` executes async HTTP request with `timeout=2.0`.
  2. On success: returns live atmospheric metrics with `weather_source = "live"`.
  3. On `httpx.TimeoutException`, `httpx.HTTPStatusError`, or network failure: catches exception cleanly, queries `weather_fallbacks` table for matching `route_stop_id`, `month`, and `hour`.
  4. Returns median weather with `weather_source = "historical_fallback"`.
  5. Logs warning internally without propagating unhandled errors to the caller.
* **AI Coding Prompt:**
  ```text
  You are an expert Python systems engineer. Implement `src/services/weather.py` for RouteTrust.
  
  Specifications:
  - Base URL: `https://api.open-meteo.com/v1/forecast`
  - Parameters: `latitude`, `longitude`, `hourly=precipitation,apparent_temperature,wind_speed_10m`, `timezone=auto`.
  - HTTP Client: Use `httpx.AsyncClient(timeout=2.0)`.
  - Function signature:
    async def get_route_weather(
        lat: float,
        lon: float,
        route_stop_id: int,
        arrival_time: datetime,
        db: Session
    ) -> WeatherPayload:
  
  Behavior:
  1. Attempt to fetch forecast for the hour matching arrival_time.
  2. If HTTP 200 and valid JSON:
     return WeatherPayload(
         precipitation_mm=val,
         apparent_temperature_c=val,
         wind_speed_kmh=val,
         weather_source="live"
     )
  3. If timeout (>2.0s), network error, or HTTP status != 200:
     Query SQLite `WeatherFallback` table:
       filter by `route_stop_id == route_stop_id`, `month == arrival_time.month`, `hour == arrival_time.hour`.
     If found:
       return WeatherPayload(
           precipitation_mm=fallback.median_precipitation_mm,
           apparent_temperature_c=fallback.median_apparent_temperature_c,
           wind_speed_kmh=fallback.median_wind_speed_kmh,
           weather_source="historical_fallback"
       )
     If fallback record missing:
       use global conservative default (e.g. 1.0mm rain, 20.0C, 15km/h) with weather_source="historical_fallback".
  
  Write clean, async-safe, robust code with logging.
  ```

---

### TICK-006: FastAPI Inference API, Endpoints & Pydantic V2 Schemas
* **Feature Name:** FastAPI REST API Layer & Route Handlers
* **Priority:** Must-have for launch
* **Dependencies:** TICK-001, TICK-004, TICK-005
* **Description:**  
  Construct the production FastAPI backend service in `src/api/`. Implement Pydantic v2 schemas in `src/api/schemas.py` and routes in `src/api/routes/`:
  - `GET /api/v1/health`: Returns API status and model loaded status.
  - `GET /api/v1/routes-stops`: Returns list of available route-stop pairs, sample counts, and low-sample flags.
  - `POST /api/v1/optimize-decision`: Main inference endpoint that validates input, queries weather, calculates quantile delay, clamps departure time, logs to `inference_logs`, and returns the decision object.
* **Acceptance Criteria:**
  1. Pydantic v2 schemas strictly validate: `route_stop_id` (int), `required_arrival_time` (ISO-8601 UTC string), `alpha` (restricted to `[0.20, 0.10, 0.05]`).
  2. If `required_arrival_time <= datetime.now(timezone.utc)`, endpoint immediately rejects request with HTTP 422 Unprocessable Entity and error message `"Target arrival time must be in the future."`.
  3. Latency instrumentation tracks end-to-end execution time in milliseconds (`latency_ms < 350ms`).
  4. Successful response appends an immutable transaction record to `inference_logs`.
  5. Returns HTTP 200 with complete JSON matching Frontend Specification Section 5.
* **AI Coding Prompt:**
  ```text
  You are an expert FastAPI engineer. Implement `src/api/schemas.py`, `src/api/main.py`, and `src/api/routes/optimize.py` using FastAPI and Pydantic v2.
  
  Schemas in `src/api/schemas.py`:
  - `OptimizeDecisionRequest`:
    - `route_stop_id`: int
    - `required_arrival_time`: datetime (must include validator: must be at least 2 minutes in the future)
    - `alpha`: float (field validator: must be one of [0.20, 0.10, 0.05])
  - `PredictionsObject`: q10_delay_sec, q50_delay_sec, q90_delay_sec, selected_quantile_delay_sec, interquantile_spread_sec
  - `DecisionObject`: recommended_leave_by, scheduled_travel_time_sec, risk_buffer_applied_sec, total_transit_allocation_sec, reliability_grade, guard_triggered
  - `TelemetryObject`: weather_source, weather_condition (dict), low_confidence_flag, latency_ms
  - `OptimizeDecisionResponse`: request_uuid, route_stop_id, route_short_name, stop_name, required_arrival_time, alpha, predictions, decision, telemetry
  
  Route Handlers:
  - `GET /api/v1/health`: returns {"status": "healthy", "models_loaded": True, "timestamp": "<UTC>"}
  - `GET /api/v1/routes-stops`: returns all active `RouteStop` rows from SQLite.
  - `POST /api/v1/optimize-decision`:
    1. Start timer.
    2. Lookup `RouteStop`. If not found, raise HTTP 404.
    3. Call `get_route_weather` (with 2.0s timeout + fallback).
    4. Assemble feature vector and run quantile predictions (q10, q50, q90).
    5. Apply monotonic rearrangement.
    6. Pick risk delay based on alpha.
    7. Compute leave_by time and check early departure guard.
    8. Compute reliability grade (A-F).
    9. Calculate latency.
    10. Log transaction to `InferenceLog` table.
    11. Return `OptimizeDecisionResponse`.
  
  Include dependency injection for database session (`get_db`).
  ```

---

### TICK-007: API Security, IP Rate Limiting & Admin Authorization Guard
* **Feature Name:** In-Memory Rate Limiting & Bearer Token Authentication
* **Priority:** Must-have for launch
* **Dependencies:** TICK-006
* **Description:**  
  Implement the dual-track security model specified in the Security Blueprint. Enforce an in-memory IP sliding-window rate limiter on `/api/v1/optimize-decision` (max 60 requests/minute per IP, returning HTTP 429 when exceeded). Implement Bearer Token authorization (`Authorization: Bearer <ADMIN_API_KEY>`) for internal diagnostic and audit endpoints (`/api/v1/diagnostics/*`). Ensure anonymous commuter queries cannot access raw logs or database tables.
* **Acceptance Criteria:**
  1. Client IP rate limiter restricts any single IP to 60 queries per 60-second sliding window; 61st query receives HTTP 429 Too Many Requests.
  2. Public inference endpoint `/api/v1/optimize-decision` requires zero login or token (stateless anonymous access).
  3. Administrative diagnostics endpoint requires valid `ADMIN_API_KEY` passed via HTTP Bearer Header; invalid or missing token returns HTTP 401/403.
  4. Response headers omit internal framework versions (`server_tokens` disabled).
* **AI Coding Prompt:**
  ```text
  You are a product security engineer. Implement security middleware and dependencies for RouteTrust in `src/api/dependencies.py` and `src/core/security.py`.
  
  Requirements:
  1. Implement an in-memory sliding-window IP rate limiter middleware for FastAPI:
     - Allow maximum 60 requests per minute per client IP for `POST /api/v1/optimize-decision`.
     - Return HTTP 429 with JSON `{"error_code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests. Please wait 60 seconds."}` if exceeded.
  
  2. Implement Bearer Token security dependency `verify_admin_token`:
     - Read `ADMIN_API_KEY` from environment (`src/core/config.py`).
     - Inspect incoming `Authorization: Bearer <token>` header using `fastapi.security.HTTPBearer`.
     - Use `secrets.compare_digest` for constant-time comparison to prevent timing attacks.
     - Raise HTTP 403 Forbidden if token does not match.
  
  3. Apply `verify_admin_token` to `/api/v1/diagnostics/model` and any raw log inspection endpoints.
  4. Ensure all public endpoints sanitize input against SQL injection through SQLAlchemy parameterization.
  ```

---

### TICK-008: Streamlit Commute Control Panel & Input Form
* **Feature Name:** Commuter Input Dashboard & Parameter Form
* **Priority:** Must-have for launch
* **Dependencies:** TICK-006
* **Description:**  
  Build Screen 1 (Commute Parameters Panel) in `src/ui/components/controls.py` and `src/ui/views/dashboard.py` according to the Frontend Specification. Include route & stop selector dropdowns (populated from `/api/v1/routes-stops`), target arrival time picker, and a 3-option segmented toggle for risk tolerance $lpha$ ("High Reliability (5% risk)", "Standard Commute (10% risk)", "Aggressive (20% risk)"). Perform client-side pre-validation to prevent past arrival times.
* **Acceptance Criteria:**
  1. Dynamic dropdown selectors load route and stop metadata on app launch via `/api/v1/routes-stops`.
  2. Risk tolerance selector provides 3 clear options with explanatory plain-language tooltips: $lpha=0.05, 0.10, 0.20$.
  3. Target arrival picker enforces future times; if a user selects a past time, an error banner renders immediately and disables submission.
  4. "Calculate Leave-By" primary CTA button displays loading spinner during backend computation.
  5. UI adheres strictly to Design System tokens (Navy `#0F172A`, Blue `#2563EB`, Slate `#F8FAFC`).
* **AI Coding Prompt:**
  ```text
  You are an expert Streamlit and frontend Python developer. Implement the Commute Control Panel for RouteTrust in `src/ui/components/controls.py`.
  
  UI Specifications based on RouteTrust Design System:
  - Colors: Slate canvas `#F8FAFC`, Primary Blue `#2563EB`, Slate Text `#0F172A`.
  - Layout: Left sidebar or left column (5 cols on wide screens).
  
  Features:
  1. Fetch active route-stops from `http://127.0.0.1:8000/api/v1/routes-stops` using `requests` or `httpx`.
  2. Create a clean dropdown `st.selectbox` displaying formatted route names (e.g. "M15-SBS Southbound — 2nd Ave & E 34th St").
  3. Arrival Time Input:
     - `st.time_input` and `st.date_input` defaulting to current local time + 45 minutes.
     - Validate that combined datetime is > now. If not, render `st.error("Target arrival time must be in the future.")`.
  4. Risk Tolerance Stepper:
     - Use `st.radio` with horizontal layout or custom segmented button:
       - "Standard (10% risk)" -> alpha = 0.10 (Default)
       - "High Reliability (5% risk)" -> alpha = 0.05
       - "Aggressive / Fast (20% risk)" -> alpha = 0.20
  5. Primary CTA: `st.button("Calculate Leave-By", type="primary", use_container_width=True)`.
  6. Return selected parameters as a clean dictionary ready for API submission.
  ```

---

### TICK-009: Streamlit Hero Decision Card & Inline Advisory Indicators
* **Feature Name:** Leave-By Hero Decision Console & Risk Decomposition
* **Priority:** Must-have for launch
* **Dependencies:** TICK-006, TICK-008
* **Description:**  
  Build Screen 2 (Decision Console) in `src/ui/components/decision_card.py`. Render the hero recommended "Leave-By Time" in high-contrast display font (`36px` Bold), flanked by the dynamic Reliability Grade Badge ($A$ to $F$) with color-coded fills. Display the transit time breakdown: Scheduled Travel Duration, Risk Buffer Applied ($Q_{1-lpha}$ delay), and Total Transit Allocation. Display inline advisory banners for active flags: Early Departure Guard triggered, Historical Weather Fallback active, or Low Historical Sample route.
* **Acceptance Criteria:**
  1. Hero Leave-By time prominently displayed in bold numerical font (e.g. `08:14 AM`).
  2. Dynamic Reliability Grade Badge rendered with proper CSS token backgrounds:
     - Grade A: `#059669` (Emerald)
     - Grade B: `#2563EB` (Blue)
     - Grade C: `#D97706` (Amber)
     - Grade D: `#EA580C` (Orange)
     - Grade F: `#DC2626` (Red)
  3. Inline alert banners render conditionally with clear microcopy:
     - Early Departure Guard: `"Early Departure Guard Applied: Recommended departure clamped to prevent missing early vehicle."`
     - Weather Fallback: `"Historical Weather Estimate: Live weather unavailable; using 5-year September medians."`
     - Low Samples: `"Limited Historical Data: This route segment has <30 logged trips. Buffer is conservative."`
  4. Displays a horizontal stacked breakdown bar or metric columns showing Scheduled Travel vs. Delay Risk Buffer.
* **AI Coding Prompt:**
  ```text
  You are an expert UI developer. Implement the Hero Decision Card for RouteTrust in `src/ui/components/decision_card.py` using Streamlit and custom HTML/CSS.
  
  Specifications:
  - Input: Decision response object from `POST /api/v1/optimize-decision`.
  - Design Tokens:
    - Display font: Inter / Monospace for clock times.
    - Grade A: bg `#ECFDF5`, border `#A7F3D0`, text `#065F46`
    - Grade B: bg `#EFF6FF`, border `#BFDBFE`, text `#1E40AF`
    - Grade C: bg `#FFFBEB`, border `#FDE68A`, text `#92400E`
    - Grade D: bg `#FFF7ED`, border `#FED7AA`, text `#9A3412`
    - Grade F: bg `#FEF2F2`, border `#FECACA`, text `#991B1B`
  
  Components to render:
  1. Hero Card Container with subtle drop shadow and left accent border.
  2. Leave-By Departure Recommendation in 36px bold text with clock icon.
  3. Reliability Grade Pill Badge with letter grade and descriptive subtext (e.g. "Grade A — High Predictability").
  4. Metrics Row (`st.columns(3)`):
     - Metric 1: Target Arrival (HH:MM AM/PM)
     - Metric 2: Scheduled Duration (X mins)
     - Metric 3: Risk Buffer Added (+Y mins)
  5. Conditional Inline Warning Alerts:
     - If `decision.guard_triggered`: render info callout with shield icon.
     - If `telemetry.weather_source == "historical_fallback"`: render amber warning callout.
     - If `telemetry.low_confidence_flag`: render amber warning callout regarding low sample size.
  6. Quantile Spread Accordion: expandable section showing Q10 (-XXs), Q50 (+XXs), and Q90 (+XXs).
  
  Inject clean CSS via `st.markdown("<style>...</style>", unsafe_allow_html=True)`.
  ```

---

### TICK-010: Diagnostics & Explainability Console
* **Feature Name:** Technical Auditor Screen & Model Calibration Telemetry
* **Priority:** Must-have for launch
* **Dependencies:** TICK-003, TICK-006, TICK-007
* **Description:**  
  Build Screen 3 (Diagnostics Console) in `src/ui/views/diagnostics_view.py` and `src/api/routes/diagnostics.py`. Provide technical evaluators and auditors with transparent model calibration statistics: Pinball loss table comparing LightGBM against the Groupby-Median baseline ($\ge 10\%$ improvement verification), empirical quantile calibration figures ($Q_{0.10}, Q_{0.50}, Q_{0.90}$ coverage), gain-based feature importance bar charts, and data provenance disclosures.
* **Acceptance Criteria:**
  1. Endpoint `/api/v1/diagnostics/model` returns metadata, metrics, and feature importances from `artifacts/metadata.json`.
  2. Diagnostics view displays:
     - Pinball loss comparison table highlighting the percentage improvement over baseline.
     - Coverage calibration table verifying empirical coverage vs nominal target (e.g. target 90% vs empirical 89.4%).
     - Altair or Plotly horizontal bar chart displaying feature importance rankings.
     - Data provenance card stating source archives (`traines.eu GTFS-RT` + `Open-Meteo`) and known limitations (direct route segments only).
  3. Protected by admin token in API; Streamlit view provides simple evaluator access key input or local loopback bypass.
* **AI Coding Prompt:**
  ```text
  You are an ML visualization engineer. Implement the Diagnostics View for RouteTrust in `src/ui/views/diagnostics_view.py` and backend route in `src/api/routes/diagnostics.py`.
  
  Requirements:
  1. Backend `src/api/routes/diagnostics.py`:
     - `GET /api/v1/diagnostics/model`: reads and returns `artifacts/metadata.json`.
  
  2. Frontend `src/ui/views/diagnostics_view.py`:
     - Render Header: "RouteTrust Model Calibration & Diagnostics"
     - Section 1: Pinball Loss vs. Groupby-Median Baseline:
       Display dataframe / metric card showing:
       - Model Pinball Loss
       - Baseline Groupby-Median Loss
       - Relative Improvement % (Highlight green if >= 10.0%)
     - Section 2: Empirical Coverage Calibration:
       Render a calibration comparison table:
       - Quantile (q10, q50, q90)
       - Target Coverage (10%, 50%, 90%)
       - Empirical Holdout Coverage (e.g. 10.8%, 51.2%, 89.4%)
       - Status badge ("Calibrated" if within ±5pp)
     - Section 3: Feature Importance:
       Plot horizontal bar chart using Streamlit `st.bar_chart` or `altair` charting feature importance scores.
     - Section 4: Data Provenance & Limitations:
       Render markdown callout noting:
       - Historical archive: traines.eu GTFS-RT Archive + Open-Meteo Weather
       - Holdout strategy: Non-shuffled chronological split
       - Scope limitations: Direct route segments only. Detours and walking transfers excluded.
  ```

---

### TICK-011: Docker Containerization & Multi-Service Entrypoint
* **Feature Name:** Dockerfile & Supervisord / Bash Startup Orchestration
* **Priority:** Must-have for launch
* **Dependencies:** TICK-001 through TICK-010
* **Description:**  
  Construct the production containerization setup for Hugging Face Spaces deployment. Create a Debian/Ubuntu Python 3.11 `Dockerfile` and a robust startup script (`start.sh`). The container must initialize SQLite migrations/seeds, launch the FastAPI daemon on `127.0.0.1:8000`, poll the `/api/v1/health` endpoint until healthy, and launch Streamlit on public port `7860`.
* **Acceptance Criteria:**
  1. `Dockerfile` installs dependencies from `requirements.txt` with locked versions.
  2. `start.sh` executes database initialization (`python -m src.db.init_db`).
  3. Launches Uvicorn running FastAPI on `127.0.0.1:8000` in the background.
  4. Employs a curl polling loop that blocks until `http://127.0.0.1:8000/api/v1/health` returns HTTP 200 `{"status": "healthy"}`.
  5. Launches Streamlit on `0.0.0.0:7860` with `--server.enableCORS=false` and `--server.enableXsrfProtection=false`.
  6. Port 8000 is bound strictly to `127.0.0.1` (not exposed to internet); only port 7860 is exposed externally.
* **AI Coding Prompt:**
  ```text
  You are a DevOps and containerization specialist. Create `Dockerfile` and `start.sh` for deploying RouteTrust to Hugging Face Spaces.
  
  File 1: `Dockerfile`
  - Base image: `python:3.11-slim-bullseye`
  - Install system dependencies: curl, build-essential.
  - Set working directory `/app`.
  - Copy `requirements.txt` and install via `pip install --no-cache-dir -r requirements.txt`.
  - Copy project repository into `/app`.
  - Make `start.sh` executable (`chmod +x start.sh`).
  - Set environment variables: `PYTHONPATH=.`, `APP_ENV=production`.
  - Expose port `7860`.
  - ENTRYPOINT: `["./start.sh"]`
  
  File 2: `start.sh`
  - Bash script with `set -e`.
  - Step 1: Run DB migrations: `python -m src.db.init_db`
  - Step 2: Launch FastAPI: `uvicorn src.api.main:app --host 127.0.0.1 --port 8000 &`
  - Step 3: Health check wait loop:
      until curl -s http://127.0.0.1:8000/api/v1/health | grep '"status":"healthy"' > /dev/null; do
          echo "Waiting for FastAPI engine startup..."
          sleep 0.5
      done
  - Step 4: Launch Streamlit on HF port:
      exec streamlit run src/ui/app.py           --server.port=7860           --server.address=0.0.0.0           --server.enableCORS=false           --server.enableXsrfProtection=false           --server.headless=true
  
  Ensure clean signal trapping and POSIX standard compatibility.
  ```

---

### TICK-012: Automated Integration Testing & Edge Case Suite
* **Feature Name:** Pytest Integration Test Suite & Failure Edge Cases
* **Priority:** Must-have for launch
* **Dependencies:** TICK-001 through TICK-011
* **Description:**  
  Implement the comprehensive test suite in `tests/` covering API contracts, quantile monotonicity, decision clamping, and network failure resilience. Automate tests for all pre-launch edge cases defined in the Security and PRD documents: past arrival time rejection, Open-Meteo 2.0s timeout fallback, negative delay clamping (early departure guard), low-sample flagging, and rate limiting.
* **Acceptance Criteria:**
  1. `tests/test_quantiles.py` validates that monotonic rearrangement strictly prevents quantile crossing across 10,000 synthetic random draws.
  2. `tests/test_optimizer.py` verifies that whenever $	ext{leave\_by} > t_{	ext{arrive}} - S$, the early departure guard clamps the time and sets `guard_triggered = True`.
  3. `tests/test_api.py` mocks Open-Meteo timeout and verifies that API returns HTTP 200 with `weather_source = "historical_fallback"`.
  4. Tests verify that requests with past arrival times receive HTTP 422.
  5. Tests verify that routes with sample count $<30$ return `low_confidence_flag = True`.
  6. All tests pass with `pytest tests/ -v`.
* **AI Coding Prompt:**
  ```text
  You are a senior QA / Test Automation engineer. Write a complete pytest test suite in `tests/` for RouteTrust.
  
  Files to create:
  1. `tests/conftest.py`:
     - Test client fixture using `fastapi.testclient.TestClient`.
     - In-memory SQLite DB session fixture with pre-seeded route stops (normal and low-sample).
  
  2. `tests/test_quantiles.py`:
     - Test `enforce_monotonic_quantiles` with normal, reversed (q90 < q10), and identical quantile values.
     - Test `compute_reliability_grade` for each boundary threshold (A through F).
  
  3. `tests/test_optimizer.py`:
     - Test `calculate_leave_by`:
       - Case A: Normal positive delay (leave_by < scheduled departure, guard=False).
       - Case B: Negative delay / early arrival (raw leave_by > scheduled departure, guard clamps to scheduled departure, guard=True).
  
  4. `tests/test_api.py`:
     - Test `GET /api/v1/health` -> 200 OK.
     - Test `GET /api/v1/routes-stops` -> 200 OK with list of routes.
     - Test `POST /api/v1/optimize-decision`:
       - Happy path calculation.
       - Past arrival time validation -> 422 Unprocessable Entity.
       - Low-sample route (sample_count < 30) -> returns `telemetry.low_confidence_flag == True`.
     - Test Weather Timeout Mock:
       - Mock `httpx.AsyncClient.get` to raise `httpx.TimeoutException`.
       - Assert response returns 200 OK with `telemetry.weather_source == "historical_fallback"`.
  
  Ensure 100% test pass rate with clear assertion error messages.
  ```

---

## Should-Have Tickets (Post-Launch Polish)

### TICK-013: Model Drift Telemetry & Calibration Monitoring
* **Feature Name:** Offline Drift Monitor & Coverage Divergence Tracker
* **Priority:** Should-have
* **Dependencies:** TICK-001, TICK-006
* **Description:**  
  Build a background analytics utility in `src/ml/drift.py` that queries `inference_logs` and compares logged predictions against real-world outcome delays (when GTFS updates are backfilled). Compute empirical coverage divergence ($\Delta 	ext{Coverage} = |	ext{Target} - 	ext{Empirical}|$) and raise an administrative warning flag if divergence exceeds 10 percentage points.
* **Acceptance Criteria:**
  1. Computes rolling 7-day empirical coverage for $Q_{0.10}, Q_{0.50}, Q_{0.90}$.
  2. Generates an alert dictionary if $|	ext{Coverage}_{0.90} - 0.90| > 0.10$.
  3. Exposes metrics via an admin-authenticated endpoint `/api/v1/diagnostics/drift`.
* **AI Coding Prompt:**
  ```text
  You are an MLOps engineer. Implement `src/ml/drift.py` to evaluate model calibration drift on logged inference records.
  
  Requirements:
  1. Create a function `evaluate_calibration_drift(db: Session, lookback_days: int = 7)`:
     - Query `InferenceLog` records from the past `lookback_days`.
     - Compute empirical coverage for each quantile tau in [0.10, 0.50, 0.90].
     - If divergence between empirical coverage and nominal tau > 0.10 (10pp), set `alert: True` and include warning message.
  2. Create FastAPI endpoint in `src/api/routes/diagnostics.py`:
     - `GET /api/v1/diagnostics/drift`
     - Protected by `verify_admin_token`.
     - Returns JSON report containing rolling sample count, empirical coverage, and drift alert status.
  ```

---

## Nice-to-Have Tickets (v2 Extensions)

### TICK-014: Cost-Weighted Asymmetric Risk Utility Optimizer
* **Feature Name:** Custom Early vs. Late Cost Weighting Optimizer
* **Priority:** Nice-to-have
* **Dependencies:** TICK-004, TICK-006
* **Description:**  
  Extend the decision engine to accept user-specified cost weights for arriving late ($c_{	ext{late}}$) versus waiting early ($c_{	ext{early}}$). Implement numerical minimization over the discrete delay distribution to compute the cost-optimal departure time $rg\min_t \mathbb{E}[C(t)]$, providing a personalized alternative to standard fixed quantiles.
* **Acceptance Criteria:**
  1. Accepts ratio $R = c_{	ext{late}} / c_{	ext{early}} \in [1.0, 20.0]$.
  2. Calculates optimal risk quantile $	au^* = rac{R}{R + 1}$ and maps to custom leave-by recommendation.
  3. Provides an interactive UI toggle in Streamlit allowing users to switch between "Fixed Risk Percentage" and "Cost Ratio".
* **AI Coding Prompt:**
  ```text
  You are an applied mathematician and ML engineer. Extend `src/services/decision_optimizer.py` with cost-weighted asymmetric risk optimization.
  
  Requirements:
  1. Given user penalty weights:
     - $c_{late}$: penalty per minute arriving after required time.
     - $c_{early}$: penalty per minute arriving before required time (idle waiting time).
     - Asymmetric critical fractile: $	au^* = rac{c_{late}}{c_{late} + c_{early}}$.
  2. Interpolate or extrapolate the predicted delay quantile for $	au^*$ from the existing $[\hat{Q}_{0.10}, \hat{Q}_{0.50}, \hat{Q}_{0.90}]$ predictions using piecewise linear interpolation.
  3. Return the calculated leave-by recommendation alongside expected asymmetric loss.
  4. Add unit test verifying that when $c_{late} \gg c_{early}$, recommended departure time shifts earlier.
  ```

---

## Summary Matrix

| Ticket ID | Feature Name | Priority | Dependencies | Target Artifacts |
|---|---|:---:|:---:|---|
| **TICK-001** | SQLite Database & Schema (WAL Mode) | **Must-have** | None | `src/db/session.py`, `models.py`, `init_db.py` |
| **TICK-002** | Transit Archive Processing & Feature Pipeline | **Must-have** | TICK-001 | `src/ml/features.py`, `feature_pipeline.joblib` |
| **TICK-003** | Multi-Quantile LightGBM Regressors | **Must-have** | TICK-002 | `src/ml/train.py`, `artifacts/model_q*.joblib` |
| **TICK-004** | Quantile Postprocessing & Optimizer | **Must-have** | TICK-003 | `src/ml/postprocess.py`, `src/services/decision_optimizer.py` |
| **TICK-005** | Async Weather Service & Fallback Cache | **Must-have** | TICK-001 | `src/services/weather.py` |
| **TICK-006** | FastAPI Endpoints & Pydantic V2 Schemas | **Must-have** | TICK-001, 004, 005 | `src/api/schemas.py`, `src/api/main.py`, `routes/` |
| **TICK-007** | Security, Rate Limiting & Admin Guard | **Must-have** | TICK-006 | `src/api/dependencies.py`, `src/core/security.py` |
| **TICK-008** | Streamlit Commuter Control Panel | **Must-have** | TICK-006 | `src/ui/components/controls.py`, `src/ui/app.py` |
| **TICK-009** | Streamlit Hero Decision Card | **Must-have** | TICK-006, 008 | `src/ui/components/decision_card.py` |
| **TICK-010** | Diagnostics & Explainability Console | **Must-have** | TICK-003, 006, 007 | `src/ui/views/diagnostics_view.py`, `routes/diagnostics.py` |
| **TICK-011** | Docker Container & Startup Script | **Must-have** | TICK-001 - 010 | `Dockerfile`, `start.sh` |
| **TICK-012** | Automated Integration Test Suite | **Must-have** | TICK-001 - 011 | `tests/test_api.py`, `tests/test_optimizer.py` |
| **TICK-013** | Model Drift Telemetry & Monitoring | Should-have | TICK-001, 006 | `src/ml/drift.py`, `routes/diagnostics.py` |
| **TICK-014** | Cost-Weighted Asymmetric Risk Optimizer | Nice-to-have | TICK-004, 006 | `src/services/decision_optimizer.py` |

---
*End of Feature Ticket List. Every ticket is structured for immediate execution by an AI coding agent or development team.*
