import pandas as pd
import streamlit as st

import api_client
from eda_service import is_ames_shaped
from ui import badge, hint, page_header, spacer


def upload_panel(key_prefix: str) -> None:
    with st.container(border=True):
        name_col, target_col = st.columns(2)
        with name_col:
            st.session_state.dataset_name = st.text_input(
                "Dataset name", value=st.session_state.dataset_name, key=f"{key_prefix}-name"
            )
        with target_col:
            st.session_state.target_column = st.text_input(
                "Target column (optional)",
                value=st.session_state.target_column,
                key=f"{key_prefix}-target",
                help="The column you want to predict. Leave it empty and pick one later when you save.",
            )

        uploaded = st.file_uploader(
            "Drag and drop a CSV file here, or browse", type="csv", key=f"{key_prefix}-file"
        )
        if uploaded is not None:
            file_col, send_col = st.columns([3, 1])
            with file_col:
                size = (
                    f"{uploaded.size:,} B" if uploaded.size < 1024
                    else f"{uploaded.size / 1024:,.0f} KB"
                )
                st.caption(f"{uploaded.name} \u00b7 {size} \u2014 not uploaded yet")
            with send_col:
                send_clicked = st.button(
                    "Upload file", key=f"{key_prefix}-send", type="primary", use_container_width=True
                )
            if send_clicked:
                uploaded.seek(0)
                try_load(lambda: api_client.upload_dataset(
                    st.session_state.token,
                    uploaded,
                    st.session_state.dataset_name,
                    st.session_state.target_column or None,
                ))
        else:
            hint("Pick a CSV, then press Upload file. Nothing is sent until you do.")

        st.html("<div class='divider'>OR PASTE A URL</div>")

        col_url, col_btn = st.columns([3, 1])
        with col_url:
            url = st.text_input(
                "CSV URL",
                placeholder="https://raw.githubusercontent.com/propertea-ai/data/main/train.csv",
                key=f"{key_prefix}-url",
            )
        with col_btn:
            spacer(35)
            fetch_clicked = st.button(
                "Fetch dataset", key=f"{key_prefix}-fetch", disabled=not url.strip(), use_container_width=True
            )
        if fetch_clicked and url:
            try_load(lambda: api_client.fetch_dataset_from_url(
                st.session_state.token,
                url,
                st.session_state.dataset_name,
                st.session_state.target_column or None,
            ))


def render_upload():
    page_header("Upload", "Upload a dataset", "Send a CSV from your machine, or fetch one from a URL")

    upload_panel("upload")

    just_uploaded = (
        st.session_state.dataset_id is not None
        and st.session_state.dataset_id == st.session_state.last_uploaded_id
    )
    summary = st.session_state.dataset_summary
    if just_uploaded and summary is not None:
        badge(
            f"Uploaded \u201c{st.session_state.dataset_name}\u201d \u2014 "
            f"{summary['n_rows']:,} rows \u00d7 {summary['n_columns']} columns"
        )
    elif st.session_state.dataset_id is not None:
        st.caption(f"Currently open: {st.session_state.dataset_name}. A new upload replaces it.")

    spacer(24)
    goes_to = "Explore" if st.session_state.ames_ready else "Prepare"
    ready = st.session_state.dataset_id is not None
    go_col, other_col, _rest = st.columns([1, 1, 2])
    with go_col:
        if st.button(
            f"Continue to {goes_to} \u2192",
            type="primary",
            disabled=not ready,
            help=None if ready else "Upload or fetch a dataset first.",
            use_container_width=True,
        ):
            st.session_state.page = goes_to
            st.rerun()
    with other_col:
        other = "Prepare" if goes_to == "Explore" else "Datasets"
        if st.button(
            f"Go to {other}",
            disabled=not ready,
            use_container_width=True,
        ):
            st.session_state.page = other
            st.rerun()


def try_load(persist):
    try:
        response = persist()
    except api_client.BackendUnreachableError as e:
        st.error(f"Can't reach the backend: {e} \u2014 press Upload file again to retry.")
        return
    except api_client.ApiError as e:
        st.error(f"Couldn't save that dataset: {e} \u2014 fix it and try again.")
        return

    dataset_id = response["id"]
    try:
        preview = api_client.get_dataset(st.session_state.token, dataset_id, limit=1)
    except api_client.ApiError as e:
        st.error(f"Uploaded, but couldn't verify the dataset: {e}")
        return

    st.session_state.dataset_id = dataset_id
    st.session_state.last_uploaded_id = dataset_id
    st.session_state.dataset_summary = {"n_rows": response["n_rows"], "n_columns": len(preview["columns"])}
    st.session_state.models = {}
    st.session_state.prep_df = None
    st.session_state.prep_source = None
    st.session_state.prep_history = []
    st.session_state.prep_saved_at = 0
    st.session_state.prep_saved_as = None
    st.session_state.ames_ready = is_ames_shaped(
        pd.DataFrame(preview["rows"], columns=preview["columns"])
    )
    if not st.session_state.ames_ready:
        st.warning(
            "This isn't Ames housing data, so Explore, Train and Predict stay locked. "
            "Use Prepare to inspect and clean it."
        )
