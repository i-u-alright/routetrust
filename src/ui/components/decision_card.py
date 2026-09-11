import streamlit as st
from datetime import datetime


# Grade → (emoji label, hex colour)
GRADE_META = {
    "A": ("Very Reliable  🟢", "#4CAF50"),
    "B": ("Mostly Reliable  🔵", "#2196F3"),
    "C": ("Somewhat Unpredictable  🟡", "#F9A825"),
    "D": ("Quite Variable  🟠", "#FF9800"),
    "F": ("Highly Unpredictable  🔴", "#F44336"),
}


def _format_duration(seconds: float) -> str:
    """Convert raw seconds to a friendly minutes string."""
    minutes = abs(seconds) / 60
    if minutes < 1:
        return "under 1 min"
    elif minutes < 2:
        return "~1 min"
    else:
        return f"~{round(minutes)} mins"


def render_decision_card(prediction_data: dict, admin_mode: bool = False):
    """
    Renders the hero recommendation card for regular commuters.
    In admin_mode=True, also shows the raw API JSON expander.
    """
    if not prediction_data:
        return

    # ── Parse core fields ──────────────────────────────────────────────────────
    leave_by_str = prediction_data.get("recommended_leave_by")
    scheduled_str = prediction_data.get("scheduled_departure")

    if not leave_by_str:
        st.error("No recommendation received from the server. Please try again.")
        return

    try:
        leave_by = datetime.fromisoformat(leave_by_str)
        leave_by_display = leave_by.strftime("%-I:%M %p") if hasattr(leave_by, "strftime") else leave_by_str
    except Exception:
        try:
            leave_by = datetime.fromisoformat(leave_by_str)
            leave_by_display = leave_by.strftime("%I:%M %p").lstrip("0")
        except Exception:
            leave_by_display = leave_by_str

    try:
        leave_by_display = datetime.fromisoformat(leave_by_str).strftime("%I:%M %p").lstrip("0")
    except Exception:
        leave_by_display = leave_by_str

    try:
        sched_display = datetime.fromisoformat(scheduled_str).strftime("%I:%M %p").lstrip("0")
    except Exception:
        sched_display = "—"

    grade = prediction_data.get("reliability_grade", "?")
    guard_triggered = prediction_data.get("guard_triggered", False)
    risk_delay_sec = prediction_data.get("risk_delay_sec", 0.0)
    spread = prediction_data.get("interquantile_spread", 0.0)
    weather_source = prediction_data.get("weather_source", "")
    low_confidence = prediction_data.get("low_confidence_flag", False)
    latency_ms = prediction_data.get("latency_ms", 0.0)
    quantiles = prediction_data.get("monotonic_quantiles", {})

    grade_label, color = GRADE_META.get(grade, ("Unknown", "gray"))

    # ── 1. Contextual Notice Banners ───────────────────────────────────────────
    if guard_triggered:
        st.info(
            "ℹ️ **Your trip is already on a tight schedule.** "
            "Our model suggested you might even arrive a little early, so we've set your departure "
            "to match the scheduled transit time — no need to rush!"
        )

    if low_confidence:
        st.warning(
            "⚠️ **Heads up:** Fewer historical trips were recorded for this route, "
            "so today's estimate is based on limited data. Consider adding extra buffer time manually."
        )

    # ── 2. Hero Card ───────────────────────────────────────────────────────────
    extra_time_str = _format_duration(risk_delay_sec)

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
            padding: 32px 36px;
            border-radius: 16px;
            border-left: 10px solid {color};
            margin-bottom: 24px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        ">
            <p style="margin: 0 0 4px 0; font-size: 1rem; color: #AAAACC; letter-spacing: 0.05em; text-transform: uppercase;">
                Leave no later than
            </p>
            <h1 style="margin: 0 0 8px 0; font-size: 4.5rem; color: #FFFFFF; font-weight: 800; line-height: 1.1;">
                {leave_by_display}
            </h1>
            <p style="margin: 0; font-size: 1.25rem; font-weight: 600; color: {color};">
                {grade_label}
            </p>
            <p style="margin: 8px 0 0 0; font-size: 0.95rem; color: #BBBBDD;">
                Scheduled transit departure: <strong>{sched_display}</strong>
                &nbsp;·&nbsp; Extra time added: <strong>{extra_time_str}</strong>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 3. Plain-English Metrics Row ───────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    # Convert spread to a human confidence percentage (inverted: lower spread = higher confidence)
    confidence_pct = max(0, min(100, round((1 - min(spread, 1.5) / 1.5) * 100)))

    with col1:
        st.metric(
            label="⏱️ Extra Time Added",
            value=extra_time_str,
            help="We added this extra time on top of the scheduled journey duration to keep you safely on time.",
        )

    with col2:
        st.metric(
            label="📊 Prediction Confidence",
            value=f"{confidence_pct}%",
            help=(
                "How consistent the timing predictions were for this route today. "
                "Higher means the model is more certain about the result."
            ),
        )

    with col3:
        weather_icon = "🌤️ Live conditions" if weather_source == "live" else "📂 Historical avg."
        st.metric(
            label="🌦️ Weather Data",
            value=weather_icon,
            help="Whether today's weather was fetched in real time or estimated from historical averages.",
        )

    # ── 4. Delay Range (plain language) ────────────────────────────────────────
    q10 = quantiles.get("q10", 0)
    q90 = quantiles.get("q90", 0)
    q10_min = _format_duration(q10)
    q90_min = _format_duration(q90)

    st.markdown(
        f"""
        <div style="background: #1a1a2a; border-radius: 10px; padding: 16px 20px; margin-top: 8px; border: 1px solid #333355;">
            <p style="margin: 0; color: #AAAACC; font-size: 0.9rem;">
                📉 <strong>Best case today:</strong> delays around {q10_min} &nbsp;&nbsp;
                📈 <strong>Worst case today:</strong> delays around {q90_min}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 5. Admin-only raw payload ───────────────────────────────────────────────
    if admin_mode:
        st.divider()
        with st.expander("🛠️ [Admin] Raw API Response"):
            st.json(prediction_data)
        st.caption(f"⚡ Response latency: {latency_ms:.1f} ms")
