import copy
from datetime import datetime

import pandas as pd
import streamlit as st

import api_client
from eda_service import TARGET_COLUMN, is_ames_shaped, missingness_summary, top_mover_correlations
from ui import context_bar, note, spacer

DEFAULTS = {
    "token": None,
    "username": None,
    "dataset_id": None,
    "dataset_name": "ames-house-prices",
    "dataset_summary": None,
    "target_column": TARGET_COLUMN,
    "ames_ready": True,
    "models": {},
    "page": "Datasets",
    "prediction": None,
    "prep_df": None,
    "prep_source": None,
    "prep_history": [],
    "prep_saved_at": 0,
    "prep_saved_as": None,
    "prep_confirm_reset": False,
    "last_uploaded_id": None,
    "_uploaded_file_id": None,
}

PREP_WIDGET_KEYS = (
    "prep_shown", "prep_order", "prep_rename_editor",
    "prep_plot_x", "prep_plot_y", "prep_plot_hue",
    "prep_impute_col", "prep_cast_col",
)


def init_session() -> None:
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = copy.deepcopy(value)


cached_get_full_dataset = st.cache_data(api_client.get_full_dataset)
cached_list_algorithms = st.cache_data(api_client.list_algorithms)
cached_missingness_summary = st.cache_data(missingness_summary)
cached_top_mover_correlations = st.cache_data(top_mover_correlations)


def sign_out():
    if st.session_state.token:
        try:
            api_client.logout(st.session_state.token)
        except api_client.ApiError:
            pass
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.dataset_id = None
    st.session_state.dataset_summary = None
    st.session_state._uploaded_file_id = None
    st.session_state.models = {}
    st.session_state.prep_df = None
    st.session_state.prep_source = None
    st.session_state.prep_history = []
    st.session_state.page = "Datasets"
    cached_get_full_dataset.clear()
    st.rerun()


def pretty_date(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%d %b %Y")


def select_dataset(ds: dict, models: list[dict], goto: str | None = None) -> None:
    try:
        preview = api_client.get_dataset(st.session_state.token, ds["id"], limit=1)
    except api_client.ApiError as e:
        st.error(f"Couldn't open that dataset: {e}")
        return

    st.session_state.dataset_id = ds["id"]
    st.session_state.dataset_name = ds["name"]
    st.session_state.target_column = ds["target_column"] or ""
    st.session_state.dataset_summary = {
        "n_rows": ds["n_rows"],
        "n_columns": len(preview["columns"]),
    }
    st.session_state.prep_df = None
    st.session_state.prep_source = None
    st.session_state.prep_history = []
    st.session_state.prep_saved_as = None
    st.session_state.prep_saved_at = 0
    st.session_state.last_uploaded_id = None
    st.session_state.prediction = None
    st.session_state.ames_ready = is_ames_shaped(
        pd.DataFrame(preview["rows"], columns=preview["columns"])
    )
    st.session_state.models = {
        m["algo"]: {
            "model_id": m["id"],
            "metrics": m["metrics"],
            "best_params": m["best_params"],
            "importances": m["importances"],
        }
        for m in reversed(models)
    }
    for key in PREP_WIDGET_KEYS:
        st.session_state.pop(key, None)
    st.session_state.page = goto or ("Explore" if st.session_state.ames_ready else "Prepare")
    st.rerun()


def dataset_meta() -> str:
    summary = st.session_state.dataset_summary or {}
    target = st.session_state.target_column
    parts = []
    if summary.get("n_rows") is not None:
        parts.append(f"{summary['n_rows']:,} rows")
    if summary.get("n_columns") is not None:
        parts.append(f"{summary['n_columns']} columns")
    parts.append(f"target {target}" if target else "no target set")
    return " \u00b7 ".join(parts)


def active_dataset_bar() -> None:
    if st.session_state.dataset_id is None:
        return
    context_bar(st.session_state.dataset_name, dataset_meta())


def missing_prerequisite(message: str, action_label: str, page: str, key: str) -> None:
    note(message)
    spacer(24)
    if st.button(action_label, key=key, type="primary"):
        st.session_state.page = page
        st.rerun()


def require_ames_dataset() -> pd.DataFrame | None:
    df = require_dataset()
    if df is None:
        return None
    if not is_ames_shaped(df):
        missing_prerequisite(
            f"\u201c{st.session_state.dataset_name}\u201d isn't Ames housing data, so this page can't run on "
            "it: it needs the full Ames column set. Prepare it first, or open a dataset that has those columns.",
            "Open Prepare \u2192",
            "Prepare",
            f"prereq-prepare-{st.session_state.page}",
        )
        return None
    return df


def require_dataset() -> pd.DataFrame | None:
    if st.session_state.dataset_id is None:
        missing_prerequisite(
            "No dataset is open yet. Upload a CSV or open one you saved earlier.",
            "Upload a dataset \u2192",
            "Upload",
            f"prereq-upload-{st.session_state.page}",
        )
        return None
    try:
        return cached_get_full_dataset(st.session_state.token, st.session_state.dataset_id)
    except api_client.ApiError as e:
        st.error(f"Couldn't load the dataset from the backend: {e}")
        return None
