import io
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.patches import Patch

import api_client
import prep_ops
from eda_service import (
    CORR_LEGEND,
    HEATMAP,
    MISSINGNESS_COLUMNS,
    NA_IS_CATEGORY,
    PLOT_KINDS,
    TARGET_COLUMN,
    DataValidationError,
    build_plot,
    is_ames_shaped,
    missingness_summary,
    top_mover_correlations,
)
from styles import CSS
from theme import COLORS, HEATMAP_CMAP
from ui import badge, context_bar, crumb, hint, note, page_header, sidebar_brand, spacer

st.set_page_config(page_title="propertea-ai", page_icon="\U0001F3E0", layout="wide")
st.html(CSS)

if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "dataset_id" not in st.session_state:
    st.session_state.dataset_id = None
if "dataset_summary" not in st.session_state:
    st.session_state.dataset_summary = None
if "_uploaded_file_id" not in st.session_state:
    st.session_state._uploaded_file_id = None
if "dataset_name" not in st.session_state:
    st.session_state.dataset_name = "ames-house-prices"
if "target_column" not in st.session_state:
    st.session_state.target_column = TARGET_COLUMN
if "ames_ready" not in st.session_state:
    st.session_state.ames_ready = True
if "models" not in st.session_state:
    st.session_state.models = {}
if "page" not in st.session_state:
    st.session_state.page = "Datasets"
if "prep_df" not in st.session_state:
    st.session_state.prep_df = None
if "prep_source" not in st.session_state:
    st.session_state.prep_source = None
if "prep_history" not in st.session_state:
    st.session_state.prep_history = []
if "last_uploaded_id" not in st.session_state:
    st.session_state.last_uploaded_id = None
if "prep_saved_as" not in st.session_state:
    st.session_state.prep_saved_as = None
if "prediction" not in st.session_state:
    st.session_state.prediction = None
if "prep_saved_at" not in st.session_state:
    st.session_state.prep_saved_at = 0
if "prep_confirm_reset" not in st.session_state:
    st.session_state.prep_confirm_reset = False

_cached_get_full_dataset = st.cache_data(api_client.get_full_dataset)
_cached_list_algorithms = st.cache_data(api_client.list_algorithms)
_cached_missingness_summary = st.cache_data(missingness_summary)
_cached_top_mover_correlations = st.cache_data(top_mover_correlations)


def sidebar():
    with st.sidebar:
        sidebar_brand()
        current = st.session_state.page
        for page in NAV:
            active = current == page or SUBPAGES.get(current) == page
            if st.button(
                page,
                key=f"nav-{page}",
                type="primary" if active else "tertiary",
                use_container_width=True,
            ):
                st.session_state.page = page
                st.rerun()
            if SUBPAGES.get(current) == page:
                st.html(f"<div class='nav-sub'>\u21b3 {current}</div>")

        st.html(
            f"<div class='session-badge'><span class='lbl'>SIGNED IN</span>"
            f"{st.session_state.username}</div>"
        )
        if st.button("Log out", key="nav-logout", type="tertiary", use_container_width=True):
            _sign_out()


def _sign_out():
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
    _cached_get_full_dataset.clear()
    st.rerun()


def _sign_in(call):
    try:
        result = call()
    except api_client.BackendUnreachableError as e:
        st.error(f"Can't reach the backend: {e}")
    except api_client.AuthError as e:
        st.error(str(e))
    except api_client.ApiError as e:
        st.error(f"Couldn't sign you in: {e}")
    else:
        st.session_state.token = result["token"]
        st.session_state.username = result["username"]
        st.rerun()


def render_auth():
    _left_pad, main_col, _right_pad = st.columns([1, 2, 1])
    with main_col:
        st.html("<div class='auth-brand'>\U0001F3E0 propertea-ai</div>")
        st.html("<p class='subtitle'>Sign in to reach your datasets and trained models</p>")

        login_tab, register_tab = st.tabs(["Log in", "Create account"])

        with login_tab:
            with st.form("login"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Log in", type="primary", use_container_width=True):
                    if not username or not password:
                        st.error("Enter a username and a password.")
                    else:
                        _sign_in(lambda: api_client.login(username, password))

        with register_tab:
            with st.form("register"):
                new_username = st.text_input("Username", help="At least 3 characters")
                new_password = st.text_input("Password", type="password", help="At least 8 characters")
                if st.form_submit_button("Create account", type="primary", use_container_width=True):
                    if len(new_username) < 3:
                        st.error("Username must be at least 3 characters.")
                    elif len(new_password) < 8:
                        st.error("Password must be at least 8 characters.")
                    else:
                        _sign_in(lambda: api_client.register(new_username, new_password))


def _pretty_date(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%d %b %Y")


def _select_dataset(ds: dict, models: list[dict], goto: str | None = None) -> None:
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


def _dataset_meta() -> str:
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
    context_bar(st.session_state.dataset_name, _dataset_meta())


def _missing_prerequisite(message: str, action_label: str, page: str, key: str) -> None:
    note(message)
    spacer(24)
    if st.button(action_label, key=key, type="primary"):
        st.session_state.page = page
        st.rerun()


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
                        _select_dataset(ds, models, goto="Explore")
                with prepare_col:
                    if st.button("Prepare", key=f"prep-{ds['id']}", use_container_width=True):
                        _select_dataset(ds, models, goto="Prepare")

            if models:
                with st.expander(f"{len(models)} trained model{'s' if len(models) > 1 else ''}"):
                    st.dataframe(
                        [
                            {
                                "Algorithm": m["algo"],
                                "RMSE (log price)": round(m["metrics"]["rmse_log"], 4),
                                "R\u00b2": round(m["metrics"]["r2"], 4) if m["metrics"].get("r2") is not None else "\u2014",
                                "Trained": _pretty_date(m["created_at"]),
                            }
                            for m in models
                        ],
                        hide_index=True,
                        use_container_width=True,
                    )


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
                _try_load(lambda: api_client.upload_dataset(
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
            _try_load(lambda: api_client.fetch_dataset_from_url(
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


def _try_load(persist):
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


def _require_ames_dataset() -> pd.DataFrame | None:
    df = _require_dataset()
    if df is None:
        return None
    if not is_ames_shaped(df):
        _missing_prerequisite(
            f"\u201c{st.session_state.dataset_name}\u201d isn't Ames housing data, so this page can't run on "
            "it: it needs the full Ames column set. Prepare it first, or open a dataset that has those columns.",
            "Open Prepare \u2192",
            "Prepare",
            f"prereq-prepare-{st.session_state.page}",
        )
        return None
    return df


def _require_dataset() -> pd.DataFrame | None:
    if st.session_state.dataset_id is None:
        _missing_prerequisite(
            "No dataset is open yet. Upload a CSV or open one you saved earlier.",
            "Upload a dataset \u2192",
            "Upload",
            f"prereq-upload-{st.session_state.page}",
        )
        return None
    try:
        return _cached_get_full_dataset(st.session_state.token, st.session_state.dataset_id)
    except api_client.ApiError as e:
        st.error(f"Couldn't load the dataset from the backend: {e}")
        return None


def render_eda():
    page_header(
        "Explore data",
        "Exploratory data analysis",
        "The target distribution, missing data, and which features move price the most \u2014 before training.",
    )
    active_dataset_bar()

    df = _require_ames_dataset()
    if df is None:
        return

    with st.container(border=True):
        st.subheader("Target distribution")
        log_price = np.log1p(df["SalePrice"])
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.2))
        axes[0].hist(df["SalePrice"] / 1000, bins=40, color=COLORS["accent"])
        axes[0].set_title(f"SalePrice (skew {df['SalePrice'].skew():.2f})", fontsize=10)
        axes[0].set_xlabel("SalePrice ($1000x)")
        axes[0].set_ylabel("Count")
        axes[1].hist(log_price, bins=40, color=COLORS["accent"])
        axes[1].set_title(f"log1p(SalePrice) (skew {log_price.skew():.2f})", fontsize=10)
        axes[1].set_xlabel("log1p(SalePrice)")
        axes[1].set_ylabel("Count")
        for ax in axes:
            ax.spines[["top", "right"]].set_visible(False)
        st.pyplot(fig)
        plt.close(fig)

    with st.container(border=True):
        st.subheader("Missingness per column")
        st.caption("Red = genuinely missing · Blue = NA means \"none\" (not a gap to fill)")
        miss = _cached_missingness_summary(df)
        cols_to_show = [c for c in MISSINGNESS_COLUMNS if c in miss.index] or miss.index[:10]
        miss_subset = miss.loc[cols_to_show].sort_values()
        if len(miss_subset):
            bar_colors = [
                COLORS["accent"] if col in NA_IS_CATEGORY else COLORS["danger"]
                for col in miss_subset.index
            ]
            fig2, ax2 = plt.subplots(figsize=(9, 3.2))
            ax2.barh(miss_subset.index, miss_subset.values, color=bar_colors)
            ax2.set_xlabel("% missing")
            ax2.spines[["top", "right"]].set_visible(False)
            legend_handles = [
                Patch(facecolor=COLORS["danger"], label="Genuinely missing"),
                Patch(facecolor=COLORS["accent"], label="NA means \"none\""),
            ]
            ax2.legend(handles=legend_handles, loc="lower right", fontsize=8, frameon=False)
            st.pyplot(fig2)
            plt.close(fig2)
        else:
            st.caption("No missing values in this dataset.")

    with st.container(border=True):
        st.subheader("Correlation heatmap — top SalePrice movers")
        corr = _cached_top_mover_correlations(df)
        fig3, ax3 = plt.subplots(figsize=(5, 4))
        im = ax3.imshow(corr, cmap=HEATMAP_CMAP, vmin=0, vmax=1)
        ax3.set_xticks(range(len(corr.columns)))
        ax3.set_xticklabels(
            [abbr for abbr, raw, _ in CORR_LEGEND if raw in corr.columns], rotation=45, ha="right", fontsize=8
        )
        ax3.set_yticks(range(len(corr.columns)))
        ax3.set_yticklabels([abbr for abbr, raw, _ in CORR_LEGEND if raw in corr.columns], fontsize=8)
        for i in range(len(corr.columns)):
            for j in range(len(corr.columns)):
                ax3.text(
                    j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7,
                    color=COLORS["white"] if corr.iloc[i, j] > 0.6 else COLORS["ink"],
                )
        fig3.colorbar(im, ax=ax3, fraction=0.046, pad=0.04)
        st.pyplot(fig3, width="content")
        plt.close(fig3)

        legend_cols = st.columns(2)
        for idx, (abbr, raw, desc) in enumerate(CORR_LEGEND):
            with legend_cols[idx % 2]:
                st.markdown(
                    f"<div class='legend-item'><b>{abbr}</b> "
                    f"<span class='legend-raw'>({raw})</span> = {desc}</div>",
                    unsafe_allow_html=True,
                )

    spacer(24)
    if st.button("Continue to Train model \u2192", type="primary"):
        st.session_state.page = "Train"
        st.rerun()


def render_train():
    page_header(
        "Train model",
        "Train a model",
        "Pick an algorithm and fit it on the cleaned dataset. Lower RMSE is better.",
    )
    active_dataset_bar()

    df = _require_ames_dataset()
    if df is None:
        return

    try:
        names = _cached_list_algorithms()
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


NEIGHBORHOODS = {
    "Blmngtn": "Bloomington Heights", "Blueste": "Bluestem", "BrDale": "Briardale",
    "BrkSide": "Brookside", "ClearCr": "Clear Creek", "CollgCr": "College Creek",
    "Crawfor": "Crawford", "Edwards": "Edwards", "Gilbert": "Gilbert",
    "IDOTRR": "Iowa DOT and Rail Road", "MeadowV": "Meadow Village", "Mitchel": "Mitchell",
    "NAmes": "North Ames", "NoRidge": "Northridge", "NPkVill": "Northpark Villa",
    "NridgHt": "Northridge Heights", "NWAmes": "Northwest Ames", "OldTown": "Old Town",
    "SWISU": "South & West of Iowa State", "Sawyer": "Sawyer", "SawyerW": "Sawyer West",
    "Somerst": "Somerset", "StoneBr": "Stone Brook", "Timber": "Timberland",
    "Veenker": "Veenker",
}

QUALITY_LABELS = {
    "Ex": "Excellent", "Gd": "Good", "TA": "Typical / average", "Fa": "Fair", "Po": "Poor",
}


def _labelled(mapping: dict[str, str]):
    return lambda code: f"{mapping.get(code, code)} ({code})" if code in mapping else code


def render_predict():
    page_header("Predict", "Predict a house price", "Describe the house, then run the model on it.")
    active_dataset_bar()

    df = _require_ames_dataset()
    if df is None:
        return
    if not st.session_state.models:
        _missing_prerequisite(
            "No model has been trained on this dataset yet, so there is nothing to predict with.",
            "Go to Train \u2192",
            "Train",
            "prereq-train-predict",
        )
        return

    left, right = st.columns([2, 3])
    with left:
        with st.container(border=True):
            model_name = st.selectbox(
                "Model",
                list(st.session_state.models.keys()),
                format_func=lambda a: f"{a} \u2014 RMSE {st.session_state.models[a]['metrics']['rmse_log']:.4f}",
            )

            st.markdown("**Location and quality**")
            neighborhood = st.selectbox(
                "Neighborhood",
                sorted(df["Neighborhood"].dropna().unique()),
                format_func=_labelled(NEIGHBORHOODS),
            )
            overall_qual = st.slider(
                "Overall quality (1 very poor \u2013 10 excellent)", 1, 10, 8
            )
            kitchen_qual = st.selectbox(
                "Kitchen quality",
                sorted(df["KitchenQual"].dropna().unique()),
                format_func=_labelled(QUALITY_LABELS),
            )

            st.markdown("**Size**")
            first_flr_sf = st.number_input("First-floor area (sq ft)", min_value=300, max_value=4000, value=1200)
            second_flr_sf = st.number_input("Second-floor area (sq ft)", min_value=0, max_value=2000, value=1000)
            total_bsmt_sf = st.number_input("Basement area (sq ft)", min_value=0, max_value=6000, value=1100)
            gr_liv_area = first_flr_sf + second_flr_sf
            total_sf = total_bsmt_sf + gr_liv_area
            st.caption(f"Living area {gr_liv_area:,} sq ft \u00b7 total with basement {total_sf:,} sq ft")

            st.markdown("**Rooms, age and parking**")
            full_bath = st.slider("Full bathrooms", 0, 4, 2)
            garage_cars = st.slider("Garage capacity (cars)", 0, 4, 2)
            year_built = st.number_input("Year built", min_value=1870, max_value=2026, value=2005)
            year_remod = st.number_input("Year last renovated", min_value=1870, max_value=2026, value=2005)

            predict_clicked = st.button("Predict price", type="primary", use_container_width=True)

    overrides = {
        "Neighborhood": neighborhood,
        "OverallQual": overall_qual,
        "1stFlrSF": first_flr_sf,
        "2ndFlrSF": second_flr_sf,
        "GrLivArea": gr_liv_area,
        "TotalBsmtSF": total_bsmt_sf,
        "FullBath": full_bath,
        "YearBuilt": year_built,
        "YearRemodAdd": year_remod,
        "GarageCars": garage_cars,
        "KitchenQual": kitchen_qual,
    }

    if predict_clicked:
        try:
            result = api_client.predict(
                st.session_state.token,
                st.session_state.models[model_name]["model_id"],
                overrides,
            )
        except api_client.ApiError as e:
            st.error(f"Couldn't generate a prediction: {e}")
        else:
            st.session_state.prediction = {
                "price": result["prediction"],
                "overrides": overrides,
                "model": model_name,
                "total_sf": total_sf,
            }

    with right:
        prediction = st.session_state.prediction
        if prediction is None:
            note("Describe the house on the left, then press Predict price.")
            return

        stale = prediction["overrides"] != overrides or prediction["model"] != model_name
        price = prediction["price"]
        shown_sf = prediction["total_sf"]

        with st.container(border=True):
            st.metric(
                "Estimated price",
                f"${price:,.0f}",
                help=f"{prediction['model']} on {shown_sf:,} sq ft \u00b7 "
                f"{NEIGHBORHOODS.get(prediction['overrides']['Neighborhood'], prediction['overrides']['Neighborhood'])}",
            )
            if stale:
                st.warning("Inputs changed since this estimate. Press Predict price to recalculate.")
            else:
                st.caption(
                    f"{prediction['model']} \u00b7 "
                    f"{NEIGHBORHOODS.get(prediction['overrides']['Neighborhood'], prediction['overrides']['Neighborhood'])}"
                    f" \u00b7 {shown_sf:,} sq ft total"
                )

        with st.container(border=True):
            st.subheader("Where this estimate falls")
            st.caption("Historical Ames sales by total square footage, with this estimate marked.")
            df_total_sf = df["TotalBsmtSF"] + df["1stFlrSF"] + df["2ndFlrSF"]
            fig, ax = plt.subplots(figsize=(7, 4.2))
            ax.scatter(df_total_sf, df["SalePrice"], alpha=0.35, color=COLORS["accent"], label="Historical sales")
            ax.scatter([shown_sf], [price], s=140, color=COLORS["highlight"], edgecolor=COLORS["white"], linewidth=1.5, zorder=5, label="This estimate")
            ax.axhline(price, color=COLORS["highlight"], linestyle="--", linewidth=1, alpha=0.6)
            ax.axvline(shown_sf, color=COLORS["highlight"], linestyle="--", linewidth=1, alpha=0.6)
            ax.set_xlabel("Total square footage (sq ft)")
            ax.set_ylabel("Sale price")
            ax.spines[["top", "right"]].set_visible(False)
            ax.legend(loc="upper left", fontsize=9, frameon=False)
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

        with st.container(border=True):
            st.subheader("What this model relies on")
            st.caption(
                "Model-wide feature importance measured across the whole training set \u2014 "
                "it is not an explanation of this particular house."
            )
            importances = st.session_state.models[prediction["model"]]["importances"]
            if not importances:
                st.caption("This model was trained before importances were recorded. Retrain it to see them.")
            else:
                labels = list(importances.keys())[::-1]
                values = list(importances.values())[::-1]
                fig_imp, ax_imp = plt.subplots(figsize=(7, 3.6))
                ax_imp.barh(labels, values, color=COLORS["accent"])
                ax_imp.set_xlabel("Increase in RMSE when the feature is shuffled")
                ax_imp.spines[["top", "right"]].set_visible(False)
                fig_imp.tight_layout()
                st.pyplot(fig_imp)
                plt.close(fig_imp)


def _prep_frame() -> pd.DataFrame | None:
    df = _require_dataset()
    if df is None:
        return None
    if st.session_state.prep_df is None or st.session_state.prep_source != st.session_state.dataset_id:
        st.session_state.prep_df = df.copy()
        st.session_state.prep_source = st.session_state.dataset_id
        st.session_state.prep_history = []
        st.session_state.prep_saved_at = 0
        st.session_state.pop("prep_shown", None)
    return st.session_state.prep_df


PREP_WIDGET_KEYS = (
    "prep_shown", "prep_order", "prep_rename_editor",
    "prep_plot_x", "prep_plot_y", "prep_plot_hue",
    "prep_impute_col", "prep_cast_col",
)


def _resync_column_widgets(columns: list[str]) -> None:
    for key in PREP_WIDGET_KEYS:
        st.session_state.pop(key, None)
    st.session_state.prep_shown = columns
    st.session_state.prep_order = columns


PREP_HISTORY_LIMIT = 20


def _apply_op(op, frame: pd.DataFrame, *args, label: str) -> None:
    try:
        result = op(frame, *args)
    except ValueError as e:
        st.error(str(e))
        return
    st.session_state.prep_history = (
        st.session_state.prep_history + [(label, frame)]
    )[-PREP_HISTORY_LIMIT:]
    st.session_state.prep_df = result
    if list(result.columns) != list(frame.columns):
        _resync_column_widgets(list(result.columns))
    st.rerun()


def _undo_op() -> None:
    label, frame = st.session_state.prep_history[-1]
    st.session_state.prep_history = st.session_state.prep_history[:-1]
    current = st.session_state.prep_df
    st.session_state.prep_df = frame
    if current is None or list(current.columns) != list(frame.columns):
        _resync_column_widgets(list(frame.columns))
    st.rerun()


def _prep_unsaved() -> bool:
    return len(st.session_state.prep_history) != st.session_state.prep_saved_at


def _reset_prep_frame() -> None:
    st.session_state.prep_df = None
    st.session_state.prep_history = []
    st.session_state.prep_saved_at = 0
    for key in PREP_WIDGET_KEYS:
        st.session_state.pop(key, None)
    st.rerun()


def _column_selector(all_columns: list[str]) -> list[str]:
    if len(all_columns) <= 15:
        return list(
            st.pills(
                "Columns in view",
                all_columns,
                selection_mode="multi",
                default=all_columns,
                key="prep_shown",
            )
        )
    with st.expander(f"Columns in view \u2014 {len(st.session_state.get('prep_shown', all_columns))} of {len(all_columns)}"):
        st.caption("Type to search. Removing a column here only hides it; the data is untouched until you delete it.")
        return list(
            st.multiselect(
                "Columns in view",
                all_columns,
                default=all_columns,
                key="prep_shown",
                label_visibility="collapsed",
            )
        )


def render_prepare():
    page_header(
        "Prepare data",
        "Prepare data",
        "Clean the open dataset, then save the result as a new one.",
    )

    prep = _prep_frame()
    if prep is None:
        return

    all_columns = list(prep.columns)
    unsaved = _prep_unsaved()
    bar_col, save_col = st.columns([5, 1])
    with bar_col:
        changes = len(st.session_state.prep_history)
        state = f"{changes} change{'s' if changes != 1 else ''} not saved yet" if unsaved else "no unsaved changes"
        context_bar(
            st.session_state.dataset_name,
            f"{len(prep):,} rows \u00b7 {len(all_columns)} columns \u00b7 {state}",
            stale=unsaved,
        )
    with save_col:
        spacer(24)
        st.html("<a class='jump-link' href='#save'>Go to save \u2193</a>")

    if st.session_state.prep_saved_as:
        saved = st.session_state.prep_saved_as
        badge(
            f"Saved \u201c{saved['name']}\u201d \u2014 {saved['n_rows']:,} rows \u00d7 {saved['n_columns']} columns. "
            f"\u201c{st.session_state.dataset_name}\u201d stays open here; find the new one on Datasets."
        )

    with st.container(border=True):
        st.subheader("Data")
        preview_tab, info_tab, describe_tab, missing_tab = st.tabs(
            ["Preview", "Column information", "Summary statistics", "Missing values"]
        )
        shown = st.session_state.get("prep_shown") or all_columns
        shown = [c for c in shown if c in all_columns] or all_columns
        with preview_tab:
            rows = st.slider("Rows to show", 5, 100, 25, key="prep_head_n")
            st.dataframe(prep[shown].head(rows), use_container_width=True, height=360)
            st.caption(f"{len(prep):,} rows total \u00b7 showing {min(rows, len(prep))} of them, {len(shown)} of {len(all_columns)} columns")
        with info_tab:
            buffer = io.StringIO()
            prep[shown].info(buf=buffer)
            st.code(buffer.getvalue(), language="text")
        with describe_tab:
            numeric_only = st.toggle("Numeric columns only", value=True, key="prep_desc_numeric")
            described = prep[shown].describe() if numeric_only else prep[shown].describe(include="all")
            st.dataframe(described.T, use_container_width=True)
        with missing_tab:
            miss = missingness_summary(prep[shown])
            if miss.empty:
                st.caption("No missing values.")
            else:
                st.dataframe(miss.rename("% missing"), use_container_width=True)

    with st.container(border=True):
        st.subheader("Columns")
        hint("Hiding a column only changes what you see here. Deleting removes it from the data you save.")
        shown = _column_selector(all_columns)
        hidden = [c for c in all_columns if c not in shown]

        drop_col, undo_col, reset_col = st.columns(3)
        with drop_col:
            if st.button(
                f"Delete {len(hidden)} hidden column{'s' if len(hidden) != 1 else ''} from the data",
                disabled=not hidden,
                use_container_width=True,
            ):
                _apply_op(
                    lambda frame, cols: frame.drop(columns=cols), prep, hidden,
                    label=f"deleted {len(hidden)} column{'s' if len(hidden) != 1 else ''}",
                )
        with undo_col:
            history = st.session_state.prep_history
            undo_label = f"Undo \u2014 {history[-1][0]}" if history else "Nothing to undo"
            if st.button(undo_label, disabled=not history, use_container_width=True):
                _undo_op()
        with reset_col:
            if st.session_state.get("prep_confirm_reset"):
                if st.button("Confirm reset \u2014 lose changes", key="prep-reset-yes", use_container_width=True):
                    st.session_state.prep_confirm_reset = False
                    _reset_prep_frame()
                if st.button("Cancel", key="prep-reset-no", type="tertiary", use_container_width=True):
                    st.session_state.prep_confirm_reset = False
                    st.rerun()
            elif st.button("Reset to uploaded data", use_container_width=True):
                if unsaved:
                    st.session_state.prep_confirm_reset = True
                    st.rerun()
                else:
                    _reset_prep_frame()

        if not shown:
            note("Show at least one column to inspect or plot it.")
            return

    with st.container(border=True):
        st.subheader("Transform")
        impute_tab, cast_tab, rows_tab, columns_tab = st.tabs(
            ["Fill missing", "Change type", "Rows", "Rename & order"]
        )

        with impute_tab:
            col, strategy, value = st.columns([2, 2, 2])
            with col:
                impute_column = st.selectbox("Column", all_columns, key="prep_impute_col")
            with strategy:
                impute_strategy = st.selectbox("Fill with", prep_ops.FILL_STRATEGIES, key="prep_impute_how")
            with value:
                impute_constant = st.text_input(
                    "Value", key="prep_impute_value", disabled=impute_strategy != "constant"
                )
            st.caption(f"{prep[impute_column].isna().sum():,} missing values in {impute_column}")
            if st.button("Apply fill", key="prep_impute_go"):
                _apply_op(prep_ops.impute, prep, impute_column, impute_strategy, impute_constant, label=f"filled {impute_column}")

        with cast_tab:
            col, dtype = st.columns(2)
            with col:
                cast_column = st.selectbox("Column", all_columns, key="prep_cast_col")
            with dtype:
                cast_dtype = st.selectbox("Cast to", list(prep_ops.CASTS), key="prep_cast_dtype")
            st.caption(f"{cast_column} is currently {prep[cast_column].dtype}")
            if st.button("Apply cast", key="prep_cast_go"):
                _apply_op(prep_ops.cast, prep, cast_column, cast_dtype, label=f"cast {cast_column} to {cast_dtype}")

        with rows_tab:
            expression = st.text_input(
                "Keep rows where",
                key="prep_filter_expr",
                placeholder="SalePrice > 100000 and OverallQual >= 5",
                help="A pandas query expression. Wrap odd column names in backticks.",
            )
            if st.button("Apply filter", key="prep_filter_go", disabled=not expression.strip()):
                _apply_op(prep_ops.filter_rows, prep, expression, label="filtered rows")

            threshold = st.slider("Drop rows missing more than (% of columns)", 0, 100, 50, key="prep_sparse_pct")
            sparse_col, dedupe_col = st.columns(2)
            with sparse_col:
                if st.button("Drop sparse rows", key="prep_sparse_go", use_container_width=True):
                    _apply_op(prep_ops.drop_sparse_rows, prep, float(threshold), label="dropped sparse rows")
            with dedupe_col:
                duplicates = int(prep.duplicated().sum())
                if st.button(
                    f"Drop {duplicates:,} duplicate rows",
                    key="prep_dedupe_go",
                    disabled=not duplicates,
                    use_container_width=True,
                ):
                    _apply_op(prep_ops.deduplicate, prep, label="dropped duplicate rows")

        with columns_tab:
            edited = st.data_editor(
                pd.DataFrame({"column": all_columns, "rename to": all_columns}),
                hide_index=True,
                disabled=["column"],
                use_container_width=True,
                key="prep_rename_editor",
            )
            if st.button("Apply renames", key="prep_rename_go"):
                _apply_op(prep_ops.rename_columns, prep, dict(zip(edited["column"], edited["rename to"])), label="renamed columns")

            order = list(
                st.multiselect(
                    "Column order",
                    all_columns,
                    default=all_columns,
                    key="prep_order",
                    help="Clear it and re-pick the columns in the order you want.",
                )
            )
            if st.button("Apply order", key="prep_order_go", disabled=order == all_columns):
                _apply_op(prep_ops.reorder_columns, prep, order, label="reordered columns")

    with st.container(border=True):
        st.subheader("Plot")
        kind = st.selectbox("Plot type", PLOT_KINDS, key="prep_plot_kind")
        x = y = hue = None
        if kind != HEATMAP:
            none_label = "\u2014"
            options = [none_label, *shown]
            x_col, y_col, hue_col = st.columns(3)
            with x_col:
                x = st.selectbox("X", options, key="prep_plot_x")
            with y_col:
                y = st.selectbox("Y", options, key="prep_plot_y")
            with hue_col:
                hue = st.selectbox("Colour by", options, key="prep_plot_hue")
            x, y, hue = (None if v == none_label else v for v in (x, y, hue))

        if kind == HEATMAP or x or y:
            try:
                fig = build_plot(prep, kind, x, y, hue)
            except (DataValidationError, ValueError, TypeError) as e:
                st.error(f"Couldn't draw that plot: {e}")
            else:
                st.pyplot(fig)
                plt.close(fig)
        else:
            hint("Pick an X or Y column to draw a plot.")

    with st.container(border=True):
        st.subheader("Save")
        hint("Saving never overwrites the open dataset \u2014 it creates a new one.")
        no_target = "\u2014 none yet \u2014"
        target_options = [no_target, *all_columns]
        default_target = st.session_state.target_column if st.session_state.target_column in all_columns else no_target
        name_col, target_col, button_col = st.columns([2, 2, 1])
        with name_col:
            new_name = st.text_input("Save as", value=f"{st.session_state.dataset_name}-prepared")
        with target_col:
            target = st.selectbox(
                "Target column",
                target_options,
                index=target_options.index(default_target),
                help="The column you want to predict. Leave it unset if you haven't decided.",
            )
            target = None if target == no_target else target
        with button_col:
            spacer(35)
            save_clicked = st.button("Save dataset", type="primary", use_container_width=True)

        if save_clicked:
            if not new_name.strip():
                st.error("Give the dataset a name.")
            else:
                try:
                    saved = api_client.upload_dataset(
                        st.session_state.token,
                        prep.to_csv(index=False).encode(),
                        new_name.strip(),
                        target,
                    )
                except api_client.BackendUnreachableError as e:
                    st.error(f"Can't reach the backend: {e}")
                except api_client.ApiError as e:
                    st.error(f"Couldn't save that dataset: {e}")
                else:
                    st.session_state.prep_saved_at = len(st.session_state.prep_history)
                    st.session_state.prep_saved_as = {
                        "id": saved["id"],
                        "name": new_name.strip(),
                        "n_rows": saved["n_rows"],
                        "n_columns": len(prep.columns),
                    }
                    st.rerun()


ROUTES = {
    "Datasets": render_datasets,
    "Upload": render_upload,
    "Explore": render_eda,
    "Train": render_train,
    "Predict": render_predict,
    "Prepare": render_prepare,
}
NAV = ["Datasets", "Explore", "Train", "Predict"]
SUBPAGES = {"Upload": "Datasets", "Prepare": "Datasets"}

if st.session_state.token is None:
    render_auth()
else:
    sidebar()
    ROUTES[st.session_state.page]()
