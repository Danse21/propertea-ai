
import uuid

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.patches import Patch

import api_client
from eda_service import (
    CORR_LEGEND,
    MISSINGNESS_COLUMNS,
    NA_IS_CATEGORY,
    TARGET_COLUMN,
    DataValidationError,
    missingness_summary,
    top_mover_correlations,
    validate_data,
)
from styles import CSS
from theme import COLORS
from ui import badge, crumb, sidebar_brand, spacer

st.set_page_config(page_title="propertea-ai", page_icon="\U0001F3E0", layout="wide")
st.html(CSS)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "dataset_id" not in st.session_state:
    st.session_state.dataset_id = None
if "dataset_summary" not in st.session_state:
    st.session_state.dataset_summary = None
if "_uploaded_file_id" not in st.session_state:
    st.session_state._uploaded_file_id = None
if "dataset_name" not in st.session_state:
    st.session_state.dataset_name = "ames-house-prices"
if "models" not in st.session_state:
    st.session_state.models = {}
if "page" not in st.session_state:
    st.session_state.page = "Upload"

_cached_get_full_dataset = st.cache_data(api_client.get_full_dataset)
_cached_list_algorithms = st.cache_data(api_client.list_algorithms)
_cached_missingness_summary = st.cache_data(missingness_summary)
_cached_top_mover_correlations = st.cache_data(top_mover_correlations)


def sidebar():
    with st.sidebar:
        sidebar_brand()
        for page in PAGES:
            active = st.session_state.page == page
            wrapper_class = "nav-active" if active else ""
            st.markdown(f"<div class='{wrapper_class}'>", unsafe_allow_html=True)
            if st.button(page, key=f"nav-{page}", use_container_width=True):
                st.session_state.page = page
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            f"<div class='session-badge'><span class='lbl'>SESSION</span>"
            f"{st.session_state.session_id[:8]}&hellip;</div>",
            unsafe_allow_html=True,
        )


def render_upload():
    crumb("Upload")
    st.title("Upload Dataset")
    st.html("<p class='subtitle'>Fetch a housing CSV from a URL, or drag one in directly</p>")

    _left_pad, main_col, _right_pad = st.columns([1, 8, 1])
    with main_col:
        with st.container(border=True):
            uploaded = st.file_uploader(
                "Drag and drop a CSV file here, or browse", type="csv"
            )
            if uploaded is not None and uploaded.file_id != st.session_state._uploaded_file_id:
                st.session_state._uploaded_file_id = uploaded.file_id
                _try_load(lambda: api_client.upload_dataset(
                    st.session_state.session_id, uploaded, st.session_state.dataset_name, TARGET_COLUMN
                ))

            st.html("<strong><div class='divider'>OR PASTE A URL</div></strong>")

            col_url, col_btn = st.columns([3, 1])
            with col_url:
                url = st.text_input(
                    "CSV URL",
                    placeholder="https://raw.githubusercontent.com/propertea-ai/data/main/train.csv",
                )
            with col_btn:
                spacer(35)
                fetch_clicked = st.button("Fetch dataset", use_container_width=True)
            if fetch_clicked and url:
                _try_load(lambda: api_client.fetch_dataset_from_url(
                    st.session_state.session_id, url, st.session_state.dataset_name, TARGET_COLUMN
                ))

            name_col, target_col = st.columns(2)
            with name_col:
                st.session_state.dataset_name = st.text_input("DATASET NAME", value=st.session_state.dataset_name)
            with target_col:
                st.text_input("TARGET COLUMN", value=TARGET_COLUMN, disabled=True)

        summary = st.session_state.dataset_summary
        if summary is not None:
            badge(f"Dataset successfully uploaded: {summary['n_rows']:,} rows × {summary['n_columns']} columns", large=True)

        if st.button("Continue to Explore data →", type="primary", use_container_width=True):
            if st.session_state.dataset_id is None:
                st.error("Dataset not added.")
            else:
                st.session_state.page = "Explore"
                st.rerun()


def _try_load(persist):
    """`persist` calls the backend (upload or from-url) and returns its DatasetOut dict."""
    try:
        response = persist()
    except api_client.BackendUnreachableError as e:
        st.error(f"Can't reach the backend: {e}")
        return
    except api_client.ApiError as e:
        st.error(f"Couldn't save that dataset: {e}")
        return

    dataset_id = response["id"]
    try:
        preview = api_client.get_dataset(st.session_state.session_id, dataset_id, limit=1)
        validate_data(pd.DataFrame(preview["rows"], columns=preview["columns"]), require_target=True)
    except DataValidationError as e:
        st.error(f"This doesn't look like valid Ames housing data: {e}")
        return
    except api_client.ApiError as e:
        st.error(f"Uploaded, but couldn't verify the dataset: {e}")
        return

    st.session_state.dataset_id = dataset_id
    st.session_state.dataset_summary = {"n_rows": response["n_rows"], "n_columns": len(preview["columns"])}
    st.session_state.models = {}


def _require_dataset() -> pd.DataFrame | None:
    if st.session_state.dataset_id is None:
        st.warning("Upload a dataset first — see the Upload page.")
        return None
    try:
        return _cached_get_full_dataset(st.session_state.session_id, st.session_state.dataset_id)
    except api_client.ApiError as e:
        st.error(f"Couldn't load the dataset from the backend: {e}")
        return None


def render_eda():
    crumb("Explore data")
    st.title("Exploratory data analysis (EDA)")
    st.caption("A quick look at the target distribution, missing data, and which features move price the most — before training.")

    df = _require_dataset()
    if df is None:
        return

    with st.container(border=True):
        st.subheader("Target distribution")
        log_price = np.log1p(df["SalePrice"])
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.2))
        axes[0].hist(df["SalePrice"] / 1000, bins=40, color=COLORS["teal-600"])
        axes[0].set_title(f"SalePrice (skew {df['SalePrice'].skew():.2f})", fontsize=10)
        axes[0].set_xlabel("SalePrice ($1000x)")
        axes[0].set_ylabel("Count")
        axes[1].hist(log_price, bins=40, color=COLORS["teal-600"])
        axes[1].set_title(f"log1p(SalePrice) (skew {log_price.skew():.2f})", fontsize=10)
        axes[1].set_xlabel("log1p(SalePrice)")
        axes[1].set_ylabel("Count")
        for ax in axes:
            ax.spines[["top", "right"]].set_visible(False)
        st.pyplot(fig)

    with st.container(border=True):
        st.subheader("Missingness per column")
        st.caption("Red = genuinely missing · Blue = NA means \"none\" (not a gap to fill)")
        miss = _cached_missingness_summary(df)
        cols_to_show = [c for c in MISSINGNESS_COLUMNS if c in miss.index] or miss.index[:10]
        miss_subset = miss.loc[cols_to_show].sort_values()
        if len(miss_subset):
            bar_colors = [
                COLORS["teal-600"] if col in NA_IS_CATEGORY else COLORS["red-600"]
                for col in miss_subset.index
            ]
            fig2, ax2 = plt.subplots(figsize=(9, 3.2))
            ax2.barh(miss_subset.index, miss_subset.values, color=bar_colors)
            ax2.set_xlabel("% missing")
            ax2.spines[["top", "right"]].set_visible(False)
            legend_handles = [
                Patch(facecolor=COLORS["red-600"], label="Genuinely missing"),
                Patch(facecolor=COLORS["teal-600"], label="NA means \"none\""),
            ]
            ax2.legend(handles=legend_handles, loc="lower right", fontsize=8, frameon=False)
            st.pyplot(fig2)
        else:
            st.caption("No missing values in this dataset.")

    with st.container(border=True):
        st.subheader("Correlation heatmap — top SalePrice movers")
        corr = _cached_top_mover_correlations(df)
        fig3, ax3 = plt.subplots(figsize=(5, 4))
        im = ax3.imshow(corr, cmap="BuGn", vmin=0, vmax=1)
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
                    color=COLORS["white"] if corr.iloc[i, j] > 0.6 else COLORS["gray-900"],
                )
        fig3.colorbar(im, ax=ax3, fraction=0.046, pad=0.04)
        st.pyplot(fig3, width="content")

        legend_cols = st.columns(2)
        for idx, (abbr, raw, desc) in enumerate(CORR_LEGEND):
            with legend_cols[idx % 2]:
                st.markdown(
                    f"<div class='legend-item'><b>{abbr}</b> "
                    f"<span class='legend-raw'>({raw})</span> = {desc}</div>",
                    unsafe_allow_html=True,
                )

    _left_pad, main_col, _right_pad = st.columns([1, 8, 1])
    with main_col:
        if st.button("Continue to Train model →", type="primary", use_container_width=True):
            st.session_state.page = "Train"
            st.rerun()


def render_train():
    crumb("Train Model")
    st.title("Train machine learning models")
    st.caption("Pick an algorithm and fit it on the cleaned dataset.")

    df = _require_dataset()
    if df is None:
        return

    try:
        names = _cached_list_algorithms()
    except api_client.ApiError as e:
        st.error(f"Couldn't load available algorithms: {e}")
        return

    algo = st.radio("Algorithm", names, horizontal=True, label_visibility="collapsed")

    train_clicked = st.button("Train Model", type="primary")

    if train_clicked:
        with st.spinner("Training..."):
            try:
                result = api_client.train(st.session_state.session_id, st.session_state.dataset_id, algo)
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

    if algo in st.session_state.models:
        with st.container(border=True):
            st.subheader(f"Result — {algo}")
            metrics = st.session_state.models[algo]["metrics"]
            with st.container(border=True):
                st.html(f"<div class='rmse-box-label'>RMSE: {metrics['rmse_log']}</div>")
            spacer(36)
            badge("Model successfully trained and saved!", large=True)
            spacer(24)

    spacer(32)
    _left_pad, main_col, _right_pad = st.columns([1, 8, 1])
    with main_col:
        if st.button("Continue to Predict →", type="primary", use_container_width=True):
            if not st.session_state.models:
                st.error("No model trained, choose a model and train.")
            else:
                st.session_state.page = "Predict"
                st.rerun()


def render_predict():
    crumb("Predict")
    st.title("Predict a house price")
    st.caption("Select specifications and Predict price.")

    df = _require_dataset()
    if df is None:
        return
    if not st.session_state.models:
        st.warning("Train at least one model first; see the Train model page.")
        return

    left, right = st.columns([2, 3])
    with left:
        with st.container(border=True):
            model_name = st.selectbox(
                "Model",
                list(st.session_state.models.keys()),
                format_func=lambda a: f"{a} — RMSE {st.session_state.models[a]['metrics']['rmse_log']}",
            )
            neighborhood = st.selectbox("Neighborhood", sorted(df["Neighborhood"].dropna().unique()))
            overall_qual = st.slider("Overall Quality", 1, 10, 8)
            first_flr_sf = st.number_input("First Floor SF", min_value=300, max_value=4000, value=1200)
            second_flr_sf = st.number_input("Second Floor SF", min_value=0, max_value=2000, value=1000)
            gr_liv_area = first_flr_sf + second_flr_sf
            total_bsmt_sf = st.number_input("Total Basement SF", min_value=0, max_value=6000, value=1100)
            total_sf = total_bsmt_sf + first_flr_sf + second_flr_sf
            full_bath = st.slider("Full Bathrooms", 0, 4, 2)
            year_built = st.number_input("Year Built", min_value=1870, max_value=2026, value=2005)
            year_remod = st.number_input("Year Last Renovated", min_value=1870, max_value=2026, value=2005)
            garage_cars = st.slider("Garage Cars", 0, 4, 2)
            kitchen_qual = st.selectbox("Kitchen Quality", sorted(df["KitchenQual"].dropna().unique()))
            predict_clicked = st.button("Predict Price", type="primary", use_container_width=True)

    with right:
        if predict_clicked:
            try:
                model_id = st.session_state.models[model_name]["model_id"]
                result = api_client.predict(
                    st.session_state.session_id,
                    model_id,
                    {
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
                    },
                )
                price = result["prediction"]
            except api_client.ApiError as e:
                st.error(f"Couldn't generate a prediction: {e}")
            else:
                with st.container(border=True):
                    st.subheader("Feature importance")
                    importances = st.session_state.models[model_name]["importances"]
                    labels = list(importances.keys())[::-1]
                    values = list(importances.values())[::-1]
                    fig_imp, ax_imp = plt.subplots(figsize=(7, 4))
                    ax_imp.barh(labels, values, color=COLORS["teal-600"])
                    ax_imp.set_xlabel("Importance (increase in RMSE when shuffled)")
                    ax_imp.spines[["top", "right"]].set_visible(False)
                    st.pyplot(fig_imp)

                with st.container(border=True):
                    st.subheader("Where this prediction falls")
                    df_total_sf = df["TotalBsmtSF"] + df["1stFlrSF"] + df["2ndFlrSF"]
                    fig, ax = plt.subplots(figsize=(7, 5))
                    ax.scatter(df_total_sf, df["SalePrice"], alpha=0.35, color=COLORS["teal-600"], label="Historical sales")
                    ax.scatter([total_sf], [price], s=140, color=COLORS["orange-500"], edgecolor=COLORS["white"], linewidth=1.5, zorder=5, label="Your estimate")
                    ax.axhline(price, color=COLORS["orange-500"], linestyle="--", linewidth=1, alpha=0.6)
                    ax.axvline(total_sf, color=COLORS["orange-500"], linestyle="--", linewidth=1, alpha=0.6)
                    ax.set_xlabel("Total Square Footage (sq ft)")
                    ax.set_ylabel("SalePrice")
                    ax.spines[["top", "right"]].set_visible(False)
                    ax.legend(loc="upper left", fontsize=9, frameon=False)
                    st.pyplot(fig)

                with st.container(border=True):
                    st.metric("Estimated Price", f"${price:,.0f}", help=f"{model_name} on {total_sf:,} sq ft · {neighborhood}")
        else:
            st.info("Select specifications and click Predict Price.")


ROUTES = {
    "Upload": render_upload,
    "Explore": render_eda,
    "Train": render_train,
    "Predict": render_predict,
}
PAGES = list(ROUTES)

sidebar()
ROUTES[st.session_state.page]()
