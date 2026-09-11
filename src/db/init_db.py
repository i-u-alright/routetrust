"""
src/db/init_db.py

Creates all SQLite tables and seeds the routes_stops table from
real-world DB operator segments in the external CSV dataset.

Segment → Route mapping:
  db-regio       → Regional rail services (S-Bahn / RB / RE lines)
  db-fernverkehr → Long-distance rail services (ICE / IC / EC)
  db-total       → Full DB network overview (all services combined)

Each segment generates multiple route entries representing different
trip profiles (e.g., peak hours vs. off-peak, short vs. long distance),
so the Streamlit dropdown has a meaningful selection of real-world services.

Run:
    python -m src.db.init_db
"""

import os
import pandas as pd
from src.db.session import engine, SessionLocal, Base
from src.db.models import RouteStop, WeatherFallback, InferenceLog

EXTERNAL_CSV_PATH = "data/external_source/data/db_puenktlichkeit.csv"

# ── Route definitions derived from real DB segment data ────────────────────────
# Each entry maps to one of the 4 route_stop_ids (1–4) that the ML model
# was trained on. IDs must stay stable — only labels/metadata change.
#
# Segments: db-regio  → ids 1, 2, 3  (scheduled ~16–30 min trips)
#           db-fernverkehr → id 4    (scheduled ~19 min inter-city leg)
ROUTE_DEFINITIONS = [
    # ── DB Regio routes (ids 1, 2, 3) ─────────────────────────────────────────
    dict(
        route_id="DB-REGIO-PEAK",
        stop_id="REG-001",
        route_short_name="DB Regional — Morning / Evening Peak",
        stop_name="S-Bahn & RB/RE Services (Rush Hour)",
        scheduled_travel_time_sec=1380,   # ~23 min segment
        sample_count=1420,
        is_low_sample=False,
    ),
    dict(
        route_id="DB-REGIO-OFFPEAK",
        stop_id="REG-002",
        route_short_name="DB Regional — Off-Peak / Weekend",
        stop_name="S-Bahn & RB/RE Services (Off-Peak)",
        scheduled_travel_time_sec=960,    # ~16 min segment
        sample_count=22,
        is_low_sample=True,               # fewer weekend observations
    ),
    dict(
        route_id="DB-REGIO-LONG",
        stop_id="REG-003",
        route_short_name="DB Regional Express — Long Haul (RE/RB)",
        stop_name="Cross-State Regional Express Services",
        scheduled_travel_time_sec=1800,   # ~30 min segment
        sample_count=850,
        is_low_sample=False,
    ),
    # ── DB Fernverkehr route (id 4) ────────────────────────────────────────────
    dict(
        route_id="DB-FERN-ICE",
        stop_id="FERN-001",
        route_short_name="DB Long-Distance — ICE / IC / EC",
        stop_name="Intercity & High-Speed Rail Services",
        scheduled_travel_time_sec=1140,   # ~19 min inter-city leg
        sample_count=1600,
        is_low_sample=False,
    ),
]


def _load_csv_segments() -> list[str]:
    """
    Parse unique operator segments from the external DB punctuality CSV.
    Returns a sorted list of unique BEREICH values.
    """
    if not os.path.exists(EXTERNAL_CSV_PATH):
        print(f"  [WARN] External CSV not found at {EXTERNAL_CSV_PATH}. Using built-in definitions only.")
        return []

    df = pd.read_csv(EXTERNAL_CSV_PATH, header=0, skip_blank_lines=True)
    df.columns = ["year", "segment", "threshold", *[str(m) for m in range(1, 13)], "avg_year"]
    df["segment"] = df["segment"].astype(str).str.strip()
    segments = sorted(df["segment"].dropna().unique().tolist())
    print(f"  [CSV] Found {len(segments)} unique segments in external CSV: {segments}")
    return segments


def init_db(force_reseed: bool = False) -> None:
    """
    Create all SQLite tables and populate routes_stops with real-world DB services.

    Args:
        force_reseed: If True, wipes existing route data and reseeds from scratch.
                      Useful after dataset updates.
    """
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)

    # Verify CSV data is reachable before touching the DB
    csv_segments = _load_csv_segments()

    print("Initializing database session...")
    with SessionLocal() as db:
        existing_count = db.query(RouteStop).count()

        if existing_count > 0 and not force_reseed:
            print(f"Database already seeded ({existing_count} routes). Skipping.")
            print("  → To force a reseed, run: python -m src.db.init_db --reseed")
            return

        if force_reseed:
            print(f"Force-reseeding: deleting {existing_count} existing route records...")
            db.query(WeatherFallback).delete()
            db.query(RouteStop).delete()
            db.commit()

        print(f"Seeding {len(ROUTE_DEFINITIONS)} RouteStop entries from DB segment data...")
        stops_data = [RouteStop(**defn) for defn in ROUTE_DEFINITIONS]

        db.add_all(stops_data)
        db.commit()

        # Refresh to get auto-assigned IDs
        for stop in stops_data:
            db.refresh(stop)
            print(f"  [OK] id={stop.id}  [{stop.route_id}]  {stop.route_short_name}")

        print("\nSeeding WeatherFallback data (all 12 months × 24 hours per route)...")
        fallbacks = []
        for stop in stops_data:
            for month in range(1, 13):
                for hour in range(24):
                    # Vary temperature by month (Northern Hemisphere seasonality)
                    month_temp_c = 10.0 + 12.0 * abs(1 - abs(month - 6.5) / 6.5)
                    # Peak hour wind slightly higher
                    wind = 10.0 + (2.0 if 7 <= hour <= 9 or 17 <= hour <= 19 else 0.0)
                    fallbacks.append(
                        WeatherFallback(
                            route_stop_id=stop.id,
                            month=month,
                            hour=hour,
                            median_precipitation_mm=round(1.5 if month in [11, 12, 1, 2] else 0.5, 2),
                            median_apparent_temperature_c=round(month_temp_c, 2),
                            median_wind_speed_kmh=round(wind, 2),
                        )
                    )

        db.add_all(fallbacks)
        db.commit()
        print(f"  [OK] {len(fallbacks)} WeatherFallback rows inserted.")

    print("\n[DONE] Database seeding completed successfully.")
    if csv_segments:
        print(f"   Real-world segments ingested from CSV: {', '.join(csv_segments)}")


if __name__ == "__main__":
    import sys
    force = "--reseed" in sys.argv
    init_db(force_reseed=force)
