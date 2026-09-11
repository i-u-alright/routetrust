import os
import json
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
METADATA_PATH = "artifacts/metadata.json"


def render_commuter_intelligence():
    """Renders the main predictive routing interface."""
    st.title("🚍 RouteTrust Commuter Intelligence")
    st.markdown(
        "Leverage high-confidence machine learning quantiles, localized live weather conditions, and your personal risk tolerance "
        "to perfectly optimize your daily transit departure times."
    )
    st.divider()

    # Render Sidebar Commuter Controls
    request_payload = render_commuter_controls()
    
    # Handle API Requests
    if request_payload:
        with st.spinner("Analyzing ML quantiles and querying weather conditions..."):
            try:
                response = requests.post(API_ENDPOINT, json=request_payload, timeout=10.0)
                
                if response.status_code == 200:
                    prediction_data = response.json()
                    
                    # Render the primary Hero Decision Card
                    render_decision_card(prediction_data)
                    
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
        st.info("👈 Use the **Commute Settings** sidebar to configure your trip and click **Calculate Leave-By**.")


def render_model_diagnostics():
    """Renders a dashboard inspecting the underlying model performance and metrics."""
    st.title("📊 Model Diagnostics")
    st.markdown("Inspect the underlying machine learning model performance, calibration metrics, and global feature importances.")
    st.divider()
    
    if not os.path.exists(METADATA_PATH):
        st.warning("⚠️ Could not find `artifacts/metadata.json`. Make sure you've run the training pipeline (`src.ml.train`).")
        return
        
    try:
        with open(METADATA_PATH, "r") as f:
            metadata = json.load(f)
            
        metrics = metadata.get("metrics", {})
        coverage = metrics.get("coverage", {})
        feature_importances = metadata.get("feature_importances_q50", {})
        
        # --- 1. Quantile Calibration ---
        st.subheader("Quantile Calibration")
        st.markdown("Comparison of our target quantile confidence intervals against the empirical holdout set coverage. Closer is better.")
        
        col1, col2, col3 = st.columns(3)
        q10_cov = coverage.get("q10", 0.0)
        q50_cov = coverage.get("q50", 0.0)
        q90_cov = coverage.get("q90", 0.0)
        
        col1.metric("10th Percentile (Target 10%)", f"{q10_cov * 100:.1f}%")
        col2.metric("50th Percentile (Target 50%)", f"{q50_cov * 100:.1f}%")
        col3.metric("90th Percentile (Target 90%)", f"{q90_cov * 100:.1f}%")
        
        st.divider()
        
        # --- 2. Pinball Loss Accuracy ---
        st.subheader("Pinball Loss Accuracy")
        st.markdown("Measures the raw predictive power of our LightGBM framework against a naive Groupby-Median baseline.")
        
        lgbm_loss = metrics.get("average_pinball_loss_lgbm", 0.0)
        base_loss = metrics.get("average_pinball_loss_baseline", 0.0)
        improvement = metrics.get("improvement_pct", 0.0)
        
        col_lgb, col_base, col_imp = st.columns(3)
        col_lgb.metric("LightGBM Average Loss", f"{lgbm_loss:.4f}")
        col_base.metric("Naive Baseline Loss", f"{base_loss:.4f}")
        col_imp.metric("Overall System Improvement", f"{improvement:.1f}%")
        
        st.divider()
        
        # --- 3. Feature Importances ---
        st.subheader("Feature Importances")
        st.markdown("Relative weighting of engineered features used by the median (Q50) LightGBM model, ranked by total information gain.")
        if feature_importances:
            # Streamlit bar charts render automatically from dictionaries mapped to simple value lists
            st.bar_chart(data=list(feature_importances.values()))
            
            # Optionally show exact numbers in an expander
            with st.expander("View Exact Gain Values"):
                st.json(feature_importances)
                
        st.divider()
        
        # --- 4. Provenance Metadata ---
        st.subheader("Provenance")
        prov = metadata.get("provenance", {})
        st.json({
            "trained_at_timestamp": metadata.get("timestamp"),
            "training_set_size": prov.get("train_size"),
            "holdout_test_set_size": prov.get("holdout_size")
        })
            
    except Exception as e:
        st.error(f"❌ Failed to parse or load diagnostics metadata: {str(e)}")


def main():
    # Primary Sidebar Navigation
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.radio(
        "Choose a module to view:",
        ["🚍 Commuter Intelligence", "📊 Model Diagnostics"]
    )
    
    st.sidebar.divider()
    
    # Render the appropriate view based on selection
    if app_mode == "🚍 Commuter Intelligence":
        render_commuter_intelligence()
    elif app_mode == "📊 Model Diagnostics":
        render_model_diagnostics()


if __name__ == "__main__":
    main()
