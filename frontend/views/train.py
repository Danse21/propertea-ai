import pandas as pd
import streamlit as st

import api_client
import state
from ui import badge, page_header, spacer


def render_train():
    page_header(
        "Train model",
        "Train a model",
        "Pick an algorithm and fit it on the cleaned dataset. Lower RMSE is better.",
    )
    state.active_dataset_bar()

    df = state.require_ames_dataset()
    if df is None:
        return

    try:
        names = state.cached_list_algorithms()
    except api_client.ApiError as e:
        st.error(f"Couldn't load available algorithms: {e}")
        return

    algo = st.radio("Algorithm", names, horizontal=True, label_visibility="collapsed")

    if st.button("Train model", type="primary"):
        with st.spinner(f"Training {algo}\u2026"):
            try:
                result = api_client.train(st.session_state.token, st.session_state.dataset_id, algo)
            except api_client.BackendUnreachableError as e:
                st.error(f"Can't reach the backend: {e}")
            except api_client.ApiError as e:
                st.error(f"Training failed: {e}")
            else:
                st.session_state.models[algo] = {
                    "model_id": result["model_id"],
                    "metrics": result["metrics"],
                    "best_params": result["best_params"],
                    "importances": result["importances"],
                }
                st.session_state.prediction = None

    if algo in st.session_state.models:
        metrics = st.session_state.models[algo]["metrics"]
        r2 = metrics.get("r2")
        st.html(
            f"<div class='rmse-box-label'>{algo} \u2014 RMSE (log price) {metrics['rmse_log']:.4f}"
            f"{f' &nbsp;\u00b7&nbsp; R\u00b2 {r2:.4f}' if r2 is not None else ''}</div>"
        )
        badge("Trained and saved")

    if st.session_state.models:
        spacer(24)
        with st.container(border=True):
            st.subheader("Model comparison")
            st.caption("RMSE (log price) \u2014 lower is better.")
            comparison = pd.DataFrame(
                [
                    {
                        "Model": name,
                        "RMSE (log price)": round(m["metrics"]["rmse_log"], 4),
                        "R\u00b2": round(m["metrics"]["r2"], 4) if m["metrics"].get("r2") is not None else "\u2014",
                    }
                    for name, m in st.session_state.models.items()
                ]
            )
            st.dataframe(comparison, hide_index=True, use_container_width=True)

    spacer(24)
    trained = bool(st.session_state.models)
    if st.button(
        "Continue to Predict \u2192",
        type="primary",
        disabled=not trained,
        help=None if trained else "Train at least one model first.",
    ):
        st.session_state.page = "Predict"
        st.rerun()
