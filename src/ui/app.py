import streamlit as st
import requests

from src.ui.components.controls import render_commuter_controls
from src.ui.components.decision_card import render_decision_card

# 1. Streamlit Page Configuration
st.set_page_config(
    page_title="RouteTrust Commuter Intelligence",
    page_icon="🚍",
    layout="wide"
)

# Constants
API_ENDPOINT = "http://127.0.0.1:8000/api/v1/predict"

def main():
    # Header and description
    st.title("🚍 RouteTrust Commuter Intelligence")
    st.markdown(
        "Leverage high-confidence machine learning quantiles, localized live weather conditions, and your personal risk tolerance "
        "to perfectly optimize your daily transit departure times."
    )
    st.divider()

    # 2. Render Sidebar Commuter Controls
    request_payload = render_commuter_controls()
    
    # 3. Handle API Requests
    if request_payload:
        # Render a nice loading spinner while waiting for the FastAPI backend
        with st.spinner("Analyzing ML quantiles and querying weather conditions..."):
            try:
                # 4. HTTP Request with Error Handling
                response = requests.post(API_ENDPOINT, json=request_payload, timeout=10.0)
                
                if response.status_code == 200:
                    prediction_data = response.json()
                    
                    # Render the primary Hero Decision Card
                    render_decision_card(prediction_data)
                    
                    # Optional Expandable Raw JSON for debugging
                    with st.expander("🛠️ View Raw API Response Payload"):
                        st.json(prediction_data)
                        
                elif response.status_code == 500:
                    st.error("🚨 **Backend Error**: The ML models have not been loaded. Make sure you successfully ran the training pipeline.")
                elif response.status_code == 404:
                    st.error("🚨 **Backend Error**: Route Stop ID not found in the SQLite database.")
                elif response.status_code == 422:
                    st.error("🚨 **Validation Error**: The API rejected the payload structure.")
                    st.json(response.json())
                else:
                    st.error(f"⚠️ **Error**: Server responded with HTTP {response.status_code}.")
                    st.json(response.text)
                    
            except requests.exceptions.ConnectionError:
                st.error("🔌 **Connection Failed**: Could not connect to the FastAPI backend. Is it running on `http://127.0.0.1:8000`?")
            except requests.exceptions.Timeout:
                st.error("⏱️ **Timeout**: The backend API took too long to respond (exceeded 10s).")
            except Exception as e:
                st.error(f"❌ **Unexpected Error**: {str(e)}")
    else:
        # Default state when the user hasn't submitted yet
        st.info("👈 Use the **Commute Settings** sidebar to configure your trip and click **Calculate Leave-By**.")

if __name__ == "__main__":
    main()
