import streamlit as st
from datetime import datetime, time

def render_commuter_controls():
    """
    Renders the commuter input controls in the Streamlit sidebar.
    Returns a dictionary of the selected values if the user clicks the submit button, 
    otherwise returns None.
    """
    st.sidebar.header("🗓️ Commute Settings")
    st.sidebar.markdown("Configure your destination and risk tolerance below.")
    
    with st.sidebar.form(key="commute_form"):
        # Route Stop Mapping based on the database seeds
        route_options = {
            "M15-SBS Southbound (2nd Ave & E 34th St)": 1,
            "B63 Westbound (5th Ave & 9th St)": 2,
            "Q32 Queens Blvd (Queens Blvd & 48th St)": 3,
            "BX12-SBS Crosstown (Pelham Pkwy & White Plains)": 4
        }
        
        selected_route_name = st.selectbox(
            "Select Route & Stop",
            options=list(route_options.keys()),
            help="Choose the transit route and destination stop."
        )
        
        # Target Arrival Date
        target_arrival_date = st.date_input(
            "Target Arrival Date",
            value=datetime.today().date()
        )
        
        # Target Arrival Time
        target_arrival_time = st.time_input(
            "Target Arrival Time",
            value=time(9, 0),
            help="What time do you absolutely need to arrive by?"
        )
        
        # Risk Appetite / Alpha Slider
        alpha_val = st.slider(
            "Risk Tolerance (Alpha)",
            min_value=0.01,
            max_value=0.99,
            value=0.20,
            step=0.01,
            help="Lower values (e.g. 0.05) mean you are highly intolerant of being late. 0.20 equates to targeting the 80th percentile worst-case delay."
        )
        
        # Form Submission
        submit_button = st.form_submit_button(label="Calculate Leave-By")
        
        if submit_button:
            # Combine the Streamlit date and time widgets into a single ISO datetime string
            # to be compatible with the FastAPI PredictionRequest schema.
            arrival_datetime = datetime.combine(target_arrival_date, target_arrival_time)
            
            return {
                "route_stop_id": route_options[selected_route_name],
                "target_arrival_time": arrival_datetime.isoformat(),
                "alpha": alpha_val
            }
            
    return None
