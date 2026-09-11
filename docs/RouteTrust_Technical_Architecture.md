# RouteTrust — Technical Architecture Document

## Recommended Tech Stack

| Layer | Selection | Technical Rationale & Trade-offs |
|---|---|---|
| **Inference API** | **FastAPI + Uvicorn** (Python 3.11) | High-throughput ASGI framework using **Pydantic v2** for type validation and serialization. It provides native OpenAPI spec generation, sub-millisecond route dispatching, and seamless integration with NumPy/Pandas pipelines in the same runtime. |
| **Presentation** | **Streamlit** | Eliminates JavaScript/CSS build overhead to fit the strict 3-day build window while delivering interactive controls (sliders, dynamic metric cards, Vega-Lite charts) natively in Python. Communicates with FastAPI over loopback HTTP. |
| **ML Engine** | **LightGBM Quantile Regressors** | Trains fast gradient-boosted trees optimized for pinball loss (`objective="quantile"`) across quantiles $\tau \in \{0.10, 0.50, 0.90\}$. Handles non-linear interactions (e.g., precipitation $\times$ peak rush hour) with minimal memory footprint compared to deep learning baselines. Quantile crossing is fixed via monotonic rearrangement ($Q'_{0.10} \le Q'_{0.50} \le Q'_{0.90}$). |
| **Persistence Engine** | **SQLite + SQLAlchemy 2.0 (WAL Mode)** | Zero-maintenance, file-based relational storage. When configured with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`), SQLite delivers non-blocking concurrent reads during writes. Ideal for a single-container deployment handling inference logs, audit trails, and training data caches without requiring an external database cluster. |
| **External Ingestion** | **HTTPX (Async)** | Non-blocking async client for live Open-Meteo weather API calls with connection pooling, automatic 2.0s timeouts, and deterministic fallback mechanics. |
| **Packaging & Orchestration** | **Single Docker Container + Supervisord / POSIX Bash** | Bundles FastAPI (port 8000) and Streamlit (port 7860) into an isolated Alpine/Debian base image tailored for Hugging Face Spaces. |

---

## Project Structure

```text
routetrust/
├── .env.example
├── .gitignore
├── Dockerfile
├── README.md
├── requirements.txt
├── start.sh
│
├── artifacts/
│   ├── model_q10.joblib
│   ├── model_q50.joblib
│   ├── model_q90.joblib
│   ├── metadata.json
│   └── feature_pipeline.joblib
│
├── data/
│   ├── raw/
│   │   └── gtfs_rt_archive.parquet
│   └── processed/
│       ├── historical_weather_lookup.parquet
│       └── route_stop_priors.parquet
│
├── src/
│   ├── __init__.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── dependencies.py
│   │   ├── schemas.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── optimize.py
│   │       ├── diagnostics.py
│   │       └── health.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py
│   │   └── models.py
│   │
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── train.py
│   │   ├── evaluate.py
│   │   ├── predict.py
│   │   └── postprocess.py
│   │   └── features.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── weather.py
│   │   └── decision_optimizer.py
│   │
│   └── ui/
│       ├── app.py
│       ├── components/
│       │   ├── controls.py
│       │   ├── decision_card.py
│       │   └── charts.py
│       └── views/
│           ├── dashboard.py
│           └── diagnostics_view.py
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_api.py
    ├── test_optimizer.py
    └── test_quantiles.py
```

---

## Database Architecture & Data Dictionary

The persistence layer uses SQLite with SQLAlchemy 2.0 ORM models. It serves three purposes: static route/stop references, offline weather fallback caches, and an immutable log of every decision made for calibration auditing.

```
  +------------------+         +--------------------------+
  |   routes_stops   | 1     * |     inference_logs       |
  |------------------|---------|--------------------------|
  | id (PK)          |         | id (PK)                  |
  | route_id         |         | route_stop_id (FK)       |
  | stop_id          |         | ...                      |
  +------------------+         +--------------------------+
           |
           | 1
           |
           | *
  +--------------------------+
  |   weather_fallbacks      |
  |--------------------------|
  | id (PK)                  |
  | route_stop_id (FK)       |
  | month, hour              |
  +--------------------------+
```

### 1. `routes_stops`
Stores canonical metadata for each route-stop pair, including historical sample counts used to trigger low-confidence flags.

* **`id`** (INTEGER, Primary Key, Autoincrement): Synthetic unique record identifier.
* **`route_id`** (VARCHAR(64), Indexed, Not Null): Public route identifier (e.g., `"M15-SBS"`).
* **`stop_id`** (VARCHAR(64), Indexed, Not Null): Specific bus/train stop identifier (e.g., `"401923"`).
* **`route_short_name`** (VARCHAR(128), Not Null): Human-readable route identifier for UI display.
* **`stop_name`** (VARCHAR(256), Not Null): Human-readable stop location name.
* **`scheduled_travel_time_sec`** (INTEGER, Not Null): Baseline scheduled travel duration in seconds between the origin terminal and this stop.
* **`sample_count`** (INTEGER, Not Null, Default: 0): Total training observations available for this segment.
* **`is_low_sample`** (BOOLEAN, Computed/Not Null, Default: FALSE): Flag set to `TRUE` if `sample_count < 30`.
* **`created_at`** (TIMESTAMP, Default: UTC Now): Ingestion timestamp.

### 2. `weather_fallbacks`
Precomputed historical medians for weather variables per route, month, and hour of day, used whenever Open-Meteo fails or hits rate limits.

* **`id`** (INTEGER, Primary Key, Autoincrement): Synthetic identifier.
* **`route_stop_id`** (INTEGER, Foreign Key -> `routes_stops.id`, Indexed, Not Null): Associated route-stop record.
* **`month`** (SMALLINT, Not Null): Month of the year ($1-12$).
* **`hour`** (SMALLINT, Not Null): Hour of the day ($0-23$).
* **`median_precipitation_mm`** (FLOAT, Not Null, Default: 0.0): Median historical precipitation for this slice.
* **`median_apparent_temperature_c`** (FLOAT, Not Null): Median apparent temperature in Celsius.
* **`median_wind_speed_kmh`** (FLOAT, Not Null): Median wind speed in km/h.

### 3. `inference_logs`
Immutable append-only ledger of every prediction executed by `/api/v1/optimize-decision`. Enables offline evaluation of model drift and calibration stability.

* **`id`** (INTEGER, Primary Key, Autoincrement): Unique query identifier.
* **`request_uuid`** (VARCHAR(36), Unique, Indexed, Not Null): Client or gateway correlation ID.
* **`route_stop_id`** (INTEGER, Foreign Key -> `routes_stops.id`, Not Null): Target route segment.
* **`required_arrival_time`** (TIMESTAMP, Not Null): Target arrival time specified by the user.
* **`alpha`** (FLOAT, Not Null): Target risk tolerance parameter ($\alpha \in \{0.20, 0.10, 0.05\}$).
* **`raw_q10_delay_sec`** (FLOAT, Not Null): Raw LightGBM $\tau=0.10$ delay prediction in seconds.
* **`raw_q50_delay_sec`** (FLOAT, Not Null): Raw LightGBM $\tau=0.50$ delay prediction in seconds.
* **`raw_q90_delay_sec`** (FLOAT, Not Null): Raw LightGBM $\tau=0.90$ delay prediction in seconds.
* **`adjusted_q_delay_sec`** (FLOAT, Not Null): Final delay value used after monotonic rearrangement: $\hat{Q}_{1-\alpha}(\text{delay}\mid x)$.
* **`recommended_leave_by`** (TIMESTAMP, Not Null): Output leave-by recommendation.
* **`reliability_grade`** (VARCHAR(2), Not Null): Assigned reliability grade (`A`, `B`, `C`, `D`, or `F`).
* **`weather_source`** (VARCHAR(32), Not Null): `"live"` or `"historical_fallback"`.
* **`guard_triggered`** (BOOLEAN, Not Null, Default: FALSE): `TRUE` if the early departure guard clamped the leave-by time.
* **`low_confidence_flag`** (BOOLEAN, Not Null, Default: FALSE): `TRUE` if route has $<30$ historical samples.
* **`latency_ms`** (FLOAT, Not Null): Execution time from request ingestion to response completion.
* **`created_at`** (TIMESTAMP, Default: UTC Now): Transaction timestamp.

---

## Configuration & Environment Variables

Create a `.env` file in the project root:

```ini
# Application Runtime
APP_ENV=production
DEBUG=false
API_HOST=127.0.0.1
API_PORT=8000
UI_PORT=7860
SECRET_KEY=change-this-to-a-secure-random-token-in-production

# Database Settings
DATABASE_URL=sqlite:///./routetrust.db
SQL_ECHO=false

# Model Artifact Paths
MODEL_DIR=./artifacts
MODEL_Q10_PATH=./artifacts/model_q10.joblib
MODEL_Q50_PATH=./artifacts/model_q50.joblib
MODEL_Q90_PATH=./artifacts/model_q90.joblib
METADATA_PATH=./artifacts/metadata.json

# External Ingestion & Guardrails
WEATHER_API_TIMEOUT_SEC=2.0
WEATHER_API_BASE_URL=https://api.open-meteo.com/v1/forecast
LOW_SAMPLE_THRESHOLD=30

# Streamlit Client Configuration
BACKEND_INTERNAL_URL=http://127.0.0.1:8000
```

---

## Implementation & Execution Directives

### Monotonic Quantile Rearrangement
LightGBM optimizes each quantile regressor independently. Under unseen feature combinations, predictions can cross ($Q_{0.90} < Q_{0.50}$). Before calculating the leave-by time or reliability grade, apply sorting across the predicted vector:

$$\mathbf{Q}^* = \text{sort}\left(\left[\hat{Q}_{0.10},\, \hat{Q}_{0.50},\, \hat{Q}_{0.90}\right]\right)$$

### Chance-Constrained Leave-By Calculation
Given target arrival $t_{\text{arrive}}$, scheduled run duration $S$, risk level $\alpha$, and delay quantile $\hat{Q}_{1-\alpha}$:

$$\text{leave\_by}_{\text{raw}} = t_{\text{arrive}} - S - \hat{Q}_{1-\alpha}(\text{delay}\mid x)$$

### Early Departure Guard
If the computed leave-by recommendation falls after scheduled departure (i.e., if negative delays/early arrivals cause $\text{leave\_by} > t_{\text{arrive}} - S$):

$$\text{leave\_by}_{\text{final}} = \min\left(\text{leave\_by}_{\text{raw}},\, t_{\text{arrive}} - S\right)$$

Set `guard_triggered = TRUE` whenever clamping alters the output.

### Container Startup Script (`start.sh`)
```bash
#!/usr/bin/env bash
set -e

# Run database migrations and seed baseline records
python -m src.db.init_db

# Start FastAPI backend daemon on localhost
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 &

# Wait for API health check
until curl -s http://127.0.0.1:8000/api/v1/health | grep '"status":"healthy"' > /dev/null; do
    echo "Waiting for API startup..."
    sleep 0.5
done

# Start Streamlit UI on Hugging Face target port 7860
exec streamlit run src/ui/app.py \
    --server.port=7860 \
    --server.address=0.0.0.0 \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
```