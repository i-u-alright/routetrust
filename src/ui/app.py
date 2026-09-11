"""
src/ui/app.py

RouteTrust Streamlit Application — Main entry point.

Architecture:
  - Default view: Commuter Intelligence (clean, jargon-free, public-facing)
  - Admin view: Model Diagnostics (gated behind sidebar toggle, developer-only)
"""

import streamlit as st
import requests

from src.ui.components.controls import render_commuter_controls
from src.ui.components.decision_card import render_decision_card
from src.ui.components.diagnostics import render_model_diagnostics

# ── Page Configuration ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RouteTrust — Know When to Leave",
    page_icon="🚍",
    layout="wide",
    menu_items={
        "About": "RouteTrust uses machine learning to help you leave at exactly the right time."
    }
)

# ── Constants ──────────────────────────────────────────────────────────────────
API_ENDPOINT = "http://127.0.0.1:8000/api/v1/predict"
ADMIN_PASSCODE = "routetrust"  # Simple soft gate; change or remove for production


# ── Sidebar: Admin Toggle ─────────────────────────────────────────────────────
def render_sidebar_controls() -> bool:
    """
    Renders the admin mode toggle at the bottom of the sidebar.
    Uses session_state so admin mode persists across rerenders and can be
    explicitly exited via a button.
    Returns True if admin mode is currently active.
    """
    if "admin_mode" not in st.session_state:
        st.session_state.admin_mode = False

    with st.sidebar:
        st.sidebar.divider()

        if st.session_state.admin_mode:
            # Show active admin badge + exit button
            st.sidebar.success("🔧 Admin Mode Active")
            if st.sidebar.button("Exit Admin Mode", use_container_width=True):
                st.session_state.admin_mode = False
                st.rerun()
        else:
            # Hidden passcode entry inside a collapsed expander
            with st.expander("🔧 Developer Options"):
                admin_input = st.text_input(
                    "Admin passcode",
                    type="password",
                    placeholder="Enter passcode…",
                    help="Enter the admin passcode to access model diagnostics.",
                    key="admin_passcode_input",
                )
                if st.button("Unlock", use_container_width=True):
                    if admin_input == ADMIN_PASSCODE:
                        st.session_state.admin_mode = True
                        st.rerun()
                    else:
                        st.error("Incorrect passcode.")

    return st.session_state.admin_mode


# ── Commuter Intelligence View ────────────────────────────────────────────────
def render_commuter_intelligence(admin_mode: bool):
    """Main commuter-facing view. Clean, friendly, and completely jargon-free."""

    # Header
    st.markdown(
        """
        <div style="margin-bottom: 8px;">
            <h1 style="margin: 0; font-size: 2.4rem; font-weight: 800;">🚍 RouteTrust</h1>
            <p style="margin: 4px 0 0 0; font-size: 1.15rem; color: #AAAACC;">
                Know exactly when to leave so you arrive on time — every time.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    # Render sidebar form
    request_payload = render_commuter_controls()

    # Default state hint
    if not request_payload:
        st.markdown(
            """
            <div style="text-align: center; padding: 60px 20px; color: #888899;">
                <div style="font-size: 3rem;">🗺️</div>
                <h3 style="color: #BBBBDD;">Ready when you are</h3>
                <p>Choose your route and arrival time in the sidebar,<br>
                then tap <strong>Get My Departure Time</strong>.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # ── API call ───────────────────────────────────────────────────────────────
    with st.spinner("Checking real-time conditions and calculating your departure…"):
        try:
            response = requests.post(API_ENDPOINT, json=request_payload, timeout=10.0)

            if response.status_code == 200:
                prediction_data = response.json()
                render_decision_card(prediction_data, admin_mode=admin_mode)

            elif response.status_code == 500:
                st.error(
                    "🚨 **Service unavailable.** "
                    "The prediction engine hasn't been set up yet. "
                    "Please contact the administrator."
                )
            elif response.status_code == 404:
                st.error(
                    "🚨 **Route not found.** "
                    "The selected route could not be found in our database. "
                    "Try a different route or refresh the page."
                )
            elif response.status_code == 422:
                st.error("🚨 **Invalid request.** Please check your inputs and try again.")
                if admin_mode:
                    st.json(response.json())
            else:
                st.error(f"⚠️ Something went wrong (HTTP {response.status_code}). Please try again.")
                if admin_mode:
                    st.text(response.text)

        except requests.exceptions.ConnectionError:
            st.error(
                "🔌 **Can't reach the server.** "
                "Make sure the RouteTrust backend is running and try again.\n\n"
                "_If you're the developer: start it with `uvicorn src.api.main:app --reload`_"
            )
        except requests.exceptions.Timeout:
            st.error(
                "⏱️ **The server took too long to respond.** "
                "This can happen during heavy load. Please wait a moment and try again."
            )
        except Exception as e:
            st.error(f"❌ **Unexpected error:** {str(e)}")
            if admin_mode:
                st.exception(e)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    # Always render the commuter controls + admin toggle in sidebar
    admin_mode = render_sidebar_controls()

    # Commuter intelligence is always the primary view
    render_commuter_intelligence(admin_mode=admin_mode)

    # Admin diagnostics panel — only visible when unlocked
    if admin_mode:
        st.divider()
        render_model_diagnostics()


if __name__ == "__main__":
    main()
