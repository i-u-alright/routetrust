import os
import sqlite3
import streamlit as st
from datetime import datetime, time

DB_PATH = "routetrust.db"


def _db_mtime() -> float:
    """Return the last-modified timestamp of the DB file, or 0.0 if it doesn't exist."""
    try:
        return os.path.getmtime(DB_PATH)
    except OSError:
        return 0.0


@st.cache_data()
def load_routes_from_db(db_mtime: float = 0.0) -> dict[str, int]:
    """
    Dynamically queries the routes_stops table in SQLite and returns a dict
    mapping human-readable "{route_short_name} — {stop_name}" labels to their row IDs.

    The db_mtime argument is used purely as a cache-busting key:
    whenever the database file is modified (e.g. after a reseed), the cache
    automatically invalidates and this function re-runs to fetch fresh rows.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(
            "SELECT id, route_short_name, stop_name FROM routes_stops ORDER BY id ASC"
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {"No routes found — please seed the database": -1}

        return {
            f"{route_short_name} — {stop_name}": row_id
            for row_id, route_short_name, stop_name in rows
        }

    except Exception as e:
        return {f"Could not load routes: {e}": -1}


def render_commuter_controls():
    """
    Renders the commuter input controls in the Streamlit sidebar.
    Returns a dict payload for the FastAPI /predict endpoint on submit, otherwise None.
    All labels are written in plain English for everyday commuters.
    """
    st.sidebar.header("Plan My Trip")
    st.sidebar.markdown("Tell us where you're going and when you need to arrive.")

    with st.sidebar.form(key="commute_form"):

        # ── Dynamic Route Selector (always fresh from DB) ───────────────────────
        route_options = load_routes_from_db(db_mtime=_db_mtime())
        route_labels = list(route_options.keys())

        selected_route_label = st.selectbox(
            "Your Route & Stop",
            options=route_labels,
            help="Select the transit line and the stop you're travelling to.",
        )
        selected_route_stop_id = route_options.get(selected_route_label, -1)

        # ── Target Arrival Date & Time ──────────────────────────────────────────
        target_arrival_date = st.date_input(
            "Date You're Travelling",
            value=datetime.today().date(),
        )

        target_arrival_time = st.time_input(
            "Time You Must Arrive By",
            value=time(9, 0),
            help="Enter the latest time you can arrive at your destination.",
        )

        # ── Safety Buffer (alpha) Slider ────────────────────────────────────────
        # Exposed to users with fully plain-English framing.
        # Alpha is inverted for display: "Maximum Safety" = low alpha.
        alpha_val = st.slider(
            "How cautious do you want to be?",
            min_value=0.01,
            max_value=0.99,
            value=0.20,
            step=0.01,
            help=(
                "Move this slider to control how much extra time we add as a safety buffer.\n\n"
                "🛡️ **More Cautious (left)** — We add a bigger time buffer so you're very unlikely to be late.\n"
                "⚡ **Less Cautious (right)** — We suggest a tighter departure time with less buffer.\n\n"
                "The default (20%) gives you a comfortable buffer for most commutes."
            ),
        )

        # ── Display plain-English preview of the safety level ──────────────────
        if alpha_val <= 0.10:
            st.caption("🛡️ **Maximum caution** — Ideal if being late is not an option.")
        elif alpha_val <= 0.25:
            st.caption("✅ **Comfortable buffer** — Good for most daily commutes.")
        elif alpha_val <= 0.50:
            st.caption("⚡ **Lean schedule** — Works well on reliable, low-delay routes.")
        else:
            st.caption("⚠️ **Minimal buffer** — Only use this on very predictable routes.")

        # ── Submit ──────────────────────────────────────────────────────────────
        submit_button = st.form_submit_button(
            label="🚍 Get My Departure Time",
            use_container_width=True,
        )

        if submit_button:
            if selected_route_stop_id == -1:
                st.error("Please select a valid route before continuing.")
                return None

            arrival_datetime = datetime.combine(target_arrival_date, target_arrival_time)
            return {
                "route_stop_id": selected_route_stop_id,
                "target_arrival_time": arrival_datetime.isoformat(),
                "alpha": alpha_val,
            }

    return None
