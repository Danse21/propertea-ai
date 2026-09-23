from datetime import datetime

import streamlit as st

import api_client
import state
from ui import badge, note, page_header, spacer


def _dataset_stamp(ds: dict) -> str:
    return datetime.fromisoformat(ds["created_at"]).strftime("%d %b %Y, %H:%M")


def render_datasets():
    head_col, action_col = st.columns([4, 1])
    with head_col:
        page_header("Datasets", "Your datasets", "Open one to explore, prepare, train or predict")
    with action_col:
        spacer(32)
        if st.button("Upload dataset", key="datasets-upload", type="primary", use_container_width=True):
            st.session_state.page = "Upload"
            st.rerun()

    try:
        datasets = api_client.list_datasets(st.session_state.token)
    except api_client.BackendUnreachableError as e:
        st.error(f"Can't reach the backend: {e}")
        return
    except api_client.ApiError as e:
        st.error(f"Couldn't load your datasets: {e}")
        return

    if not datasets:
        note("Nothing here yet. Upload a CSV to get started.")
        spacer(24)
        if st.button("Upload your first dataset", key="datasets-first-upload", type="primary"):
            st.session_state.page = "Upload"
            st.rerun()
        return

    for ds in datasets:
        try:
            models = api_client.list_models(st.session_state.token, ds["id"])
        except api_client.ApiError:
            models = []

        with st.container(border=True):
            is_active = ds["id"] == st.session_state.dataset_id
            header, action = st.columns([4, 1])

            with header:
                st.subheader(ds["name"])
                source = "fetched from URL" if ds["source_url"] else "uploaded"
                target = ds["target_column"] or "no target"
                st.caption(
                    f"{ds['n_rows']:,} rows \u00b7 {target} \u00b7 {source} \u00b7 "
                    f"{_dataset_stamp(ds)} \u00b7 #{ds['id']}"
                )
                if is_active:
                    badge("Currently open")

            with action:
                spacer(24)
                explore_col, prepare_col = st.columns(2)
                with explore_col:
                    if st.button("Explore", key=f"pick-{ds['id']}", use_container_width=True):
                        state.select_dataset(ds, models, goto="Explore")
                with prepare_col:
                    if st.button("Prepare", key=f"prep-{ds['id']}", use_container_width=True):
                        state.select_dataset(ds, models, goto="Prepare")

            if models:
                with st.expander(f"{len(models)} trained model{'s' if len(models) > 1 else ''}"):
                    st.dataframe(
                        [
                            {
                                "Algorithm": m["algo"],
                                "RMSE (log price)": round(m["metrics"]["rmse_log"], 4),
                                "R\u00b2": round(m["metrics"]["r2"], 4) if m["metrics"].get("r2") is not None else "\u2014",
                                "Trained": state.pretty_date(m["created_at"]),
                            }
                            for m in models
                        ],
                        hide_index=True,
                        use_container_width=True,
                    )
