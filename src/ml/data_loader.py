"""
src/ml/data_loader.py

Ingests the public-transport-statistics DB punctuality data from data/external_source/
and converts it into the RouteTrust feature schema required by src/ml/train.py.

External source: https://github.com/traines-source/public-transport-statistics
CSV: data/external_source/data/db_puenktlichkeit.csv

Schema of the external CSV:
  JAHR        - Year (2009-2024)
  BEREICH     - Operator segment (db-total, db-fernverkehr, db-regio)
  < VERSPÄTUNG - Threshold in minutes (5 or 15). We use 5-min threshold.
  1..12       - Monthly punctuality % (% of trains within threshold)
  AVG JAHR    - Annual average

We convert punctuality % at 5-min threshold into a mean delay_sec estimate using:
  on_time_rate = col_value / 100.0
  p_late = 1 - on_time_rate
  mean_delay_sec = p_late * EXPECTED_LATE_DELAY_SEC  (calibrated to real-world DB data)
  
We then map operator segments to our 4 route stops and augment with
synthetic (but realistic) hour/day/weather features to produce a full
training dataset compatible with the ML pipeline.

Run:
  python -m src.ml.data_loader
"""

import os
import sqlite3
import logging
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_DIR = "data"
RAW_PARQUET_PATH = os.path.join(DATA_DIR, "raw", "gtfs_rt_archive.parquet")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
TRAIN_PARQUET_PATH = os.path.join(PROCESSED_DIR, "train.parquet")
HOLDOUT_PARQUET_PATH = os.path.join(PROCESSED_DIR, "holdout.parquet")
EXTERNAL_CSV_PATH = os.path.join(DATA_DIR, "external_source", "data", "db_puenktlichkeit.csv")
DB_PATH = "routetrust.db"

# ── Constants ──────────────────────────────────────────────────────────────────
# When a train IS late (past the 5-min threshold), observed average delay
# for DB regional/long-distance services ranges from ~8–25 min.
# We model this as a mixture: some late trains hover near 5 min, others 20+ min.
EXPECTED_LATE_DELAY_SEC_BY_SEGMENT = {
    "db-fernverkehr": 18 * 60,   # Long-distance: 18 min mean when late
    "db-regio":       10 * 60,   # Regional: 10 min mean when late
    "db-total":       12 * 60,   # Network average: 12 min
}

# Map operator segments to our four RouteTrust route stops:
#   1 = M15-SBS Southbound  → urban bus (similar to db-regio short trip)
#   2 = B63 Westbound       → urban bus, lower frequency  → db-regio
#   3 = Q32 Queens Blvd     → express bus                 → db-regio
#   4 = BX12-SBS Crosstown  → bus rapid transit           → db-fernverkehr (inter-borough)
SEGMENT_TO_ROUTE_STOPS = {
    "db-regio":       [1, 2, 3],
    "db-fernverkehr": [4],
    "db-total":       [],        # Used only for baseline; not mapped to a stop
}

# Scheduled travel times (seconds) keyed by route_stop_id — matches init_db seeds
SCHEDULED_TRAVEL_TIME_SEC = {1: 1380, 2: 960, 3: 1800, 4: 1140}

# Number of synthetic observations to generate per (year, month, segment) row
SAMPLES_PER_CELL = 15


def load_external_punctuality_csv(path: str) -> pd.DataFrame:
    """
    Parse db_puenktlichkeit.csv and return a tidy DataFrame.
    Columns: year, month, segment, on_time_pct
    Only uses the 5-minute threshold rows.
    """
    logger.info(f"Loading external punctuality CSV from: {path}")
    
    # Read with natural header; actual column names are JAHR, BEREICH, < VERSPÄTUNG, 1..12, AVG JAHR
    raw = pd.read_csv(path, header=0, skip_blank_lines=True)
    
    # Normalise column names to safe identifiers
    raw.columns = ["year", "segment", "threshold", *[str(m) for m in range(1, 13)], "avg_year"]
    
    # Drop separator/blank rows (year is NaN for the blank row in the CSV)
    raw["year"] = pd.to_numeric(raw["year"], errors="coerce")
    raw = raw.dropna(subset=["year"])
    raw["year"] = raw["year"].astype(int)
    raw["threshold"] = pd.to_numeric(raw["threshold"], errors="coerce")
    
    # Keep only the 5-minute punctuality threshold
    df_5min = raw[raw["threshold"] == 5].copy()
    
    # Melt monthly columns into long format
    month_cols = [str(m) for m in range(1, 13)]
    df_long = df_5min.melt(
        id_vars=["year", "segment"],
        value_vars=month_cols,
        var_name="month",
        value_name="on_time_pct"
    )
    df_long["month"] = df_long["month"].astype(int)
    df_long["on_time_pct"] = pd.to_numeric(df_long["on_time_pct"], errors="coerce")
    
    # Drop rows where on_time_pct is missing (sparse cells in 2016-2017)
    df_long = df_long.dropna(subset=["on_time_pct"])
    df_long = df_long.sort_values(["year", "month", "segment"]).reset_index(drop=True)
    
    logger.info(f"  → {len(df_long)} valid (year, month, segment) punctuality records loaded.")
    return df_long


def punctuality_to_delay_sec(on_time_pct: float, segment: str) -> float:
    """
    Convert an on-time percentage to a mean delay estimate in seconds.

    Logic:
        E[delay] = p_on_time * 0  +  p_late * E[delay | late]
    where:
        p_late = 1 - (on_time_pct / 100)
        E[delay | late] = segment-specific constant (calibrated to German rail data)
    """
    p_late = max(0.0, 1.0 - on_time_pct / 100.0)
    expected_late_sec = EXPECTED_LATE_DELAY_SEC_BY_SEGMENT.get(segment, 12 * 60)
    return p_late * expected_late_sec


def generate_augmented_observations(row: pd.Series, rng: np.random.Generator) -> pd.DataFrame:
    """
    Given one punctuality data row (year, month, segment, on_time_pct),
    generate SAMPLES_PER_CELL synthetic observations with:
      - Realistic hour/day distribution for transit commute patterns
      - Condition-stratified weather features (clear/cloudy/rainy/snowy/stormy)
        drawn from per-condition distributions so every UI preset is
        well-represented in training data.
      - delay_sec computed with condition-aware impact multipliers so the
        model genuinely learns the difference between e.g. snow and rain.
    """
    route_stops = SEGMENT_TO_ROUTE_STOPS.get(row["segment"], [])
    if not route_stops:
        return pd.DataFrame()
    
    n = SAMPLES_PER_CELL
    mean_delay_sec = punctuality_to_delay_sec(row["on_time_pct"], row["segment"])
    
    # Assign each sample a route stop
    assigned_stops = rng.choice(route_stops, size=n)
    
    # Hours weighted toward commute peaks (7–9am, 5–7pm)
    all_hours = list(range(24))
    peak_weights = np.array([
        0.5, 0.3, 0.2, 0.2, 0.3, 0.6,   # 0-5 (early/late night)
        1.5, 3.0, 3.5, 2.0, 1.5, 1.5,   # 6-11 (morning peak)
        1.5, 1.5, 1.5, 1.8, 2.5, 3.2,   # 12-17 (midday + early evening peak)
        3.0, 2.0, 1.5, 1.0, 0.7, 0.5    # 18-23 (evening)
    ])
    peak_weights /= peak_weights.sum()
    hours = rng.choice(all_hours, size=n, p=peak_weights)
    
    day_of_week = rng.integers(0, 7, size=n)
    
    # ── Weather condition stratification ───────────────────────────────────────
    # Each observation is assigned one of 5 real-world conditions drawn with
    # realistic annual frequency weights for Germany (DWD climatology approx).
    # Seasonal shifts ensure winter months have more snowy samples and summer
    # has more clear days, matching the real-world calendar.
    #
    # This guarantees every condition that appears in the UI preset menu has
    # been seen many times by the model during training — so the presets are
    # never extrapolating outside the trained feature space.
    CONDITION_NAMES = ["clear", "cloudy", "rainy", "snowy", "stormy"]
    month = row["month"]
    if month in (12, 1, 2):          # Winter: more snow & cloud
        cond_weights = [0.15, 0.35, 0.18, 0.22, 0.10]
    elif month in (3, 4, 10, 11):    # Shoulder: balanced
        cond_weights = [0.25, 0.35, 0.22, 0.10, 0.08]
    else:                             # Summer: mostly clear
        cond_weights = [0.40, 0.35, 0.16, 0.01, 0.08]
    
    assigned_conditions = rng.choice(CONDITION_NAMES, size=n, p=cond_weights)
    
    # Per-condition distributions for the 3 weather model features.
    # Format: (precip_scale_mm, temp_mean_c, temp_std, wind_mean, wind_std, precip_prob)
    CONDITION_SPECS = {
        "clear":  (0.0,  20.0, 3.5,  8.0, 3.0, 0.00),
        "cloudy": (0.3,  15.0, 3.5, 14.0, 4.0, 0.20),
        "rainy":  (4.5,  11.0, 3.0, 22.0, 5.0, 1.00),
        "snowy":  (2.5,  -2.0, 3.0, 18.0, 5.0, 1.00),  # water-equivalent mm
        "stormy": (12.0,  8.0, 4.0, 45.0, 8.0, 1.00),
    }
    
    precipitation_mm       = np.zeros(n)
    apparent_temperature_c = np.zeros(n)
    wind_speed_kmh         = np.zeros(n)
    
    for cond, (p_scale, t_mean, t_std, w_mean, w_std, p_prob) in CONDITION_SPECS.items():
        mask = assigned_conditions == cond
        k = int(mask.sum())
        if k == 0:
            continue
        if p_prob > 0:
            precipitation_mm[mask] = rng.exponential(scale=p_scale, size=k)
        apparent_temperature_c[mask] = rng.normal(loc=t_mean, scale=t_std, size=k)
        wind_speed_kmh[mask] = np.clip(rng.normal(loc=w_mean, scale=w_std, size=k), 2.0, 80.0)
    
    # ── Delay model: condition-aware impact multipliers ────────────────────────
    # Rain and snow both add precipitation-driven delay, but snow also carries
    # an extra flat penalty (ice on tracks, slower boarding, de-icing stops).
    # Stormy adds a large disruption surge on top of heavy precipitation.
    # This teaches the model to genuinely differentiate all 5 conditions.
    is_snowy  = (assigned_conditions == "snowy").astype(float)
    is_stormy = (assigned_conditions == "stormy").astype(float)
    
    rain_impact  = precipitation_mm * rng.uniform(8, 35, size=n)
    snow_penalty = is_snowy  * rng.uniform(40, 120, size=n)   # ice/boarding extra (sec)
    wind_impact  = np.maximum(0, wind_speed_kmh - 15) * rng.uniform(2, 10, size=n)
    storm_surge  = is_stormy * rng.uniform(60, 180, size=n)   # signal failures / disruptions
    
    sigma = 0.9 if row["segment"] == "db-fernverkehr" else 0.7
    if mean_delay_sec > 1:
        mu = np.log(max(mean_delay_sec, 10)) - 0.5 * sigma ** 2
        base_delay = rng.lognormal(mean=mu, sigma=sigma, size=n)
    else:
        # Very high punctuality: mostly small negative/zero delays
        base_delay = np.maximum(0, rng.normal(loc=10, scale=30, size=n))
    
    delay_sec = base_delay + rain_impact + snow_penalty + wind_impact + storm_surge
    
    observations = pd.DataFrame({
        "route_stop_id":             assigned_stops,
        "scheduled_travel_time_sec": [SCHEDULED_TRAVEL_TIME_SEC[rs] for rs in assigned_stops],
        "hour_of_day":               hours,
        "day_of_week":               day_of_week,
        "precipitation_mm":          precipitation_mm,
        "apparent_temperature_c":    apparent_temperature_c,
        "wind_speed_kmh":            wind_speed_kmh,
        "delay_sec":                 delay_sec,
        # Provenance metadata
        "source_year":        row["year"],
        "source_month":       row["month"],
        "source_segment":     row["segment"],
        "source_on_time_pct": row["on_time_pct"],
        "weather_condition":  assigned_conditions,
    })
    
    return observations


def fetch_or_generate_dataset() -> None:
    """
    Main entry point.
    1. Loads the public-transport-statistics DB punctuality CSV.
    2. Converts punctuality rates to delay distributions.
    3. Augments with synthetic weather/temporal features.
    4. Saves raw parquet + chronological train/holdout splits.
    5. Seeds a subset into the local SQLite DB.
    """
    os.makedirs(os.path.join(DATA_DIR, "raw"), exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    # ── Step 1: Load external punctuality data ─────────────────────────────────
    if not os.path.exists(EXTERNAL_CSV_PATH):
        logger.warning(
            f"External CSV not found at {EXTERNAL_CSV_PATH}. "
            "Run: git clone https://github.com/traines-source/public-transport-statistics.git data/external_source"
        )
        logger.info("Falling back to pure synthetic data generation via src.ml.features...")
        import src.ml.features as feat_module
        feat_module.main()
        return

    punctuality_df = load_external_punctuality_csv(EXTERNAL_CSV_PATH)

    # ── Step 2: Generate augmented observations ────────────────────────────────
    logger.info("Generating augmented observations from punctuality statistics...")
    rng = np.random.default_rng(seed=42)
    
    all_frames = []
    for _, row in punctuality_df.iterrows():
        obs = generate_augmented_observations(row, rng)
        if not obs.empty:
            all_frames.append(obs)
    
    df = pd.concat(all_frames, ignore_index=True)
    logger.info(f"Generated {len(df):,} total observations from {len(punctuality_df)} punctuality cells.")

    # ── Step 3: Sort chronologically (year→month→hour) for correct holdout ────
    df = df.sort_values(["source_year", "source_month", "hour_of_day"]).reset_index(drop=True)

    # ── Step 4: Save raw parquet ───────────────────────────────────────────────
    df.to_parquet(RAW_PARQUET_PATH, index=False)
    logger.info(f"Saved raw parquet: {RAW_PARQUET_PATH} ({len(df):,} rows)")

    # ── Step 5: Chronological train/holdout split (80/20) ─────────────────────
    split_idx = int(len(df) * 0.80)
    train_df = df.iloc[:split_idx].copy()
    holdout_df = df.iloc[split_idx:].copy()
    
    train_df.to_parquet(TRAIN_PARQUET_PATH, index=False)
    holdout_df.to_parquet(HOLDOUT_PARQUET_PATH, index=False)
    logger.info(
        f"Saved train split: {TRAIN_PARQUET_PATH} ({len(train_df):,} rows) | "
        f"Holdout: {HOLDOUT_PARQUET_PATH} ({len(holdout_df):,} rows)"
    )
    
    # ── Step 6: Rebuild feature pipeline on the new training data ─────────────
    logger.info("Rebuilding feature pipeline on new training data...")
    num_features = [
        'scheduled_travel_time_sec', 'hour_of_day', 'day_of_week',
        'precipitation_mm', 'apparent_temperature_c', 'wind_speed_kmh'
    ]
    preprocessor = ColumnTransformer(
        transformers=[('num_scaler', StandardScaler(), num_features)],
        remainder='passthrough',
        verbose_feature_names_out=False
    )
    try:
        preprocessor.set_output(transform='pandas')
    except AttributeError:
        pass
    preprocessor.fit(train_df[num_features])
    os.makedirs("artifacts", exist_ok=True)
    joblib.dump(preprocessor, "artifacts/feature_pipeline.joblib")
    logger.info("Serialized fitted feature pipeline to artifacts/feature_pipeline.joblib")

    # ── Step 7: Seed SQLite historical_transit_logs ────────────────────────────
    seed_df = df[["route_stop_id", "scheduled_travel_time_sec", "hour_of_day",
                  "day_of_week", "precipitation_mm", "apparent_temperature_c",
                  "wind_speed_kmh", "delay_sec"]].head(1000)
    
    conn = sqlite3.connect(DB_PATH)
    seed_df.to_sql("historical_transit_logs", conn, if_exists="replace", index=False)
    conn.close()
    logger.info("Seeded 1,000 rows into SQLite historical_transit_logs table.")
    
    logger.info("✅ Data loading complete. Run: python -m src.ml.train")


if __name__ == "__main__":
    fetch_or_generate_dataset()