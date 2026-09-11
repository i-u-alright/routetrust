"""
src/ui/components/diagnostics.py

Admin-only diagnostics panel.
Displays technical ML model performance metrics from artifacts/metadata.json.
Intended for developers and data scientists — labels retain technical terminology.
"""

import os
import json
import pandas as pd
import streamlit as st

METADATA_PATH = "artifacts/metadata.json"


def render_model_diagnostics():
    """
    Renders the full ML diagnostics dashboard.
    Only visible when the admin sidebar toggle is active.
    """
    st.title("📊 Model Diagnostics")
    st.markdown(
        "Internal model performance metrics for developer review. "
        "All values are computed on a chronologically held-out test set."
    )
    st.divider()

    if not os.path.exists(METADATA_PATH):
        st.warning(
            "⚠️ `artifacts/metadata.json` not found. "
            "Run `python -m src.ml.train` to generate the training artifacts."
        )
        return

    try:
        with open(METADATA_PATH, "r") as f:
            metadata = json.load(f)

        metrics = metadata.get("metrics", {})
        coverage = metrics.get("coverage", {})
        feature_importances = metadata.get("feature_importances_q50", {})
        prov = metadata.get("provenance", {})

        # ── 1. Quantile Calibration ──────────────────────────────────────────
        st.subheader("1. Quantile Calibration")
        st.markdown(
            "Empirical holdout coverage vs target quantile level. "
            "Ideally, Q10 coverage ≈ 10%, Q50 ≈ 50%, Q90 ≈ 90%."
        )

        q10_cov = coverage.get("q10", 0.0)
        q50_cov = coverage.get("q50", 0.0)
        q90_cov = coverage.get("q90", 0.0)

        cal_df = pd.DataFrame({
            "Quantile": ["Q10 (10th Pct)", "Q50 (Median)", "Q90 (90th Pct)"],
            "Target Coverage": ["10.0%", "50.0%", "90.0%"],
            "Empirical Coverage": [
                f"{q10_cov * 100:.1f}%",
                f"{q50_cov * 100:.1f}%",
                f"{q90_cov * 100:.1f}%",
            ],
            "Status": [
                "✅" if abs(q10_cov - 0.10) < 0.05 else "⚠️ Off-target",
                "✅" if abs(q50_cov - 0.50) < 0.10 else "⚠️ Off-target",
                "✅" if abs(q90_cov - 0.90) < 0.05 else "⚠️ Off-target",
            ],
        })
        st.table(cal_df)
        st.divider()

        # ── 2. Pinball Loss ──────────────────────────────────────────────────
        st.subheader("2. Pinball Loss (LGBM vs. Baseline)")
        st.markdown(
            "Pinball loss measures directional forecast accuracy per quantile. "
            "Lower is better. The baseline is a Groupby-Median model."
        )

        lgbm_loss = metrics.get("average_pinball_loss_lgbm", 0.0)
        base_loss = metrics.get("average_pinball_loss_baseline", 0.0)
        improvement = metrics.get("improvement_pct", 0.0)
        q10_lgbm = metrics.get("pinball_loss_lgbm", {}).get("q10", 0.0)
        q50_lgbm = metrics.get("pinball_loss_lgbm", {}).get("q50", 0.0)
        q90_lgbm = metrics.get("pinball_loss_lgbm", {}).get("q90", 0.0)
        q10_base = metrics.get("pinball_loss_baseline", {}).get("q10", 0.0)
        q50_base = metrics.get("pinball_loss_baseline", {}).get("q50", 0.0)
        q90_base = metrics.get("pinball_loss_baseline", {}).get("q90", 0.0)

        loss_df = pd.DataFrame({
            "Quantile": ["Q10", "Q50", "Q90", "Average"],
            "LightGBM Loss": [
                f"{q10_lgbm:.4f}", f"{q50_lgbm:.4f}", f"{q90_lgbm:.4f}", f"{lgbm_loss:.4f}"
            ],
            "Baseline Loss": [
                f"{q10_base:.4f}", f"{q50_base:.4f}", f"{q90_base:.4f}", f"{base_loss:.4f}"
            ],
        })
        st.table(loss_df)

        col_imp, col_blank = st.columns([1, 2])
        col_imp.metric("Overall Improvement vs. Baseline", f"{improvement:.1f}%")
        st.divider()

        # ── 3. Feature Importances (Q50 model) ──────────────────────────────
        st.subheader("3. Feature Importances — Q50 Model (Information Gain)")
        if feature_importances:
            fi_df = pd.DataFrame(
                {"Feature": list(feature_importances.keys()), "Gain": list(feature_importances.values())}
            ).sort_values("Gain", ascending=True)

            st.bar_chart(fi_df.set_index("Feature")["Gain"])

            with st.expander("View exact gain scores"):
                st.dataframe(fi_df.sort_values("Gain", ascending=False).reset_index(drop=True))
        st.divider()

        # ── 4. Provenance ────────────────────────────────────────────────────
        st.subheader("4. Training Provenance")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Trained At", metadata.get("timestamp", "N/A")[:16])
        col_b.metric("Training Set Size", f"{prov.get('train_size', 0):,}")
        col_c.metric("Holdout Set Size", f"{prov.get('holdout_size', 0):,}")

        with st.expander("Full metadata.json"):
            st.json(metadata)

    except Exception as e:
        st.error(f"❌ Failed to load diagnostics: {e}")
