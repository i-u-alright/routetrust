import streamlit as st
from datetime import datetime

def render_decision_card(prediction_data: dict):
    """
    Renders the primary hero card with the commute recommendation,
    reliability grades, and contextual metrics.
    """
    if not prediction_data:
        return
        
    # Extract key data points
    leave_by_str = prediction_data.get("recommended_leave_by")
    if not leave_by_str:
        st.error("Invalid prediction data received.")
        return
        
    try:
        # Parse ISO 8601 string from FastAPI
        leave_by = datetime.fromisoformat(leave_by_str)
        leave_by_display = leave_by.strftime("%I:%M %p").lstrip('0')
    except ValueError:
        leave_by_display = "Unknown Time"
        
    grade = prediction_data.get("reliability_grade", "Unknown")
    guard_triggered = prediction_data.get("guard_triggered", False)
    risk_delay_sec = prediction_data.get("risk_delay_sec", 0.0)
    spread = prediction_data.get("interquantile_spread", 0.0)
    weather_source = prediction_data.get("weather_source", "Unknown")
    low_confidence = prediction_data.get("low_confidence_flag", False)
    
    # 1. Notification Banners
    if guard_triggered:
        st.warning(
            "🛡️ **Early Departure Guard Triggered**: The ML model predicted arriving early, "
            "but the leave-by time was safely clamped to the scheduled departure. Transit vehicles should not leave before their schedule!"
        )
        
    if low_confidence:
        st.info("⚠️ **Low Confidence**: This route has a low historical sample count in the database.")
        
    # 2. Main Hero Card
    st.markdown("### Optimized Commute Recommendation")
    
    # Color-coded Reliability Grade
    grade_colors = {
        'A': '#4CAF50', # Green
        'B': '#2196F3', # Blue
        'C': '#FFEB3B', # Yellow
        'D': '#FF9800', # Orange
        'F': '#F44336'  # Red
    }
    color = grade_colors.get(grade, 'gray')
    
    # Styled HTML box for high-impact visual
    st.markdown(
        f"""
        <div style="background-color: #262730; padding: 25px; border-radius: 10px; border-left: 10px solid {color}; margin-bottom: 25px;">
            <p style="margin: 0; font-size: 1.2rem; color: #E0E0E0;">You must leave by:</p>
            <h1 style="margin: 5px 0; font-size: 4rem; color: #FFFFFF;">{leave_by_display}</h1>
            <p style="margin: 0; font-size: 1.2rem; font-weight: bold; color: {color};">
                Reliability Grade: {grade}
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 3. Contextual Metrics Row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Risk Delay Buffer", 
            value=f"{int(risk_delay_sec)} sec",
            help="Additional buffer time allocated based on your risk tolerance (alpha)."
        )
        
    with col2:
        st.metric(
            label="Prediction Spread", 
            value=f"{spread:.2f}",
            help="The relative spread between the pessimistic and optimistic ML quantiles."
        )
        
    with col3:
        source_display = "Live API 🌤️" if weather_source == "live" else "SQLite Fallback 🗄️"
        st.metric(
            label="Weather Source", 
            value=source_display,
            help="Indicates whether conditions were fetched live via Open-Meteo or fell back to the local database."
        )
