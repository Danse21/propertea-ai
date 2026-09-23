import io
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.patches import Patch

import api_client
from eda_service import (
    CORR_LEGEND,
    HEATMAP,
    MISSINGNESS_COLUMNS,
    NA_IS_CATEGORY,
    PLOT_KINDS,
    TARGET_COLUMN,
    DataValidationError,
    build_plot,
    missingness_summary,
    top_mover_correlations,
    validate_data,
)
from styles import CSS
from theme import COLORS, HEATMAP_CMAP
from ui import badge, crumb, note, sidebar_brand, spacer

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
if "models" not in st.session_state:
    st.session_state.models = {}
if "page" not in st.session_state:
    st.session_state.page = "Datasets"
if "prep_df" not in st.session_state:
    st.session_state.prep_df = None
if "prep_source" not in st.session_state:
    st.session_state.prep_source = None

_cached_get_full_dataset = st.cache_data(api_client.get_full_dataset)
_cached_list_algorithms = st.cache_data(api_client.list_algorithms)
_cached_missingness_summary = st.cache_data(missingness_summary)
_cached_top_mover_correlations = st.cache_data(top_mover_correlations)


def sidebar():
    with st.sidebar:
        sidebar_brand()
        for group, pages in NAV.items():
            st.html(f"<div class='nav-group'>{group}</div>")
            for page in pages:
                active = st.session_state.page == page
                wrapper_class = "nav-active" if active else ""
                st.markdown(f"<div class='{wrapper_class}'>", unsafe_allow_html=True)
                if st.button(page, key=f"nav-{page}", use_container_width=True):
                    st.session_state.page = page
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            f"<div class='session-badge'><span class='lbl'>SIGNED IN</span>"
            f"{st.session_state.username}</div>",
            unsafe_allow_html=True,
        )
        if st.button("Log out", key="nav-logout", use_container_width=True):
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


def _select_dataset(ds: dict, models: list[dict]) -> None:
    try:
        preview = api_client.get_dataset(st.session_state.token, ds["id"], limit=1)
    except api_client.ApiError as e:
        st.error(f"Couldn't open that dataset: {e}")
        return

    st.session_state.dataset_id = ds["id"]
    st.session_state.dataset_name = ds["name"]
    st.session_state.dataset_summary = {
        "n_rows": ds["n_rows"],
        "n_columns": len(preview["columns"]),
    }
    st.session_state.models = {
        m["algo"]: {
            "model_id": m["id"],
            "metrics": m["metrics"],
            "best_params": m["best_params"],
            "importances": m["importances"],
        }
        for m in reversed(models)
    }
    st.session_state.page = "Explore"
    st.rerun()


def render_datasets():
    crumb("Datasets")
    st.title("Your datasets")
    st.html("<p class='subtitle'>Pick up where you left off, or start a new upload</p>")

    _left_pad, main_col, _right_pad = st.columns([1, 8, 1])
    with main_col:
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
            if st.button("Go to Upload \u2192", type="primary", use_container_width=True):
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
                header, action = st.columns([3, 1])

                with header:
                    st.subheader(ds["name"])
                    source = "fetched from URL" if ds["source_url"] else "uploaded"
                    st.caption(
                        f"{ds['n_rows']:,} rows \u00b7 target {ds['target_column']} \u00b7 "
                        f"{source} \u00b7 {_pretty_date(ds['created_at'])}"
                    )

                with action:
                    spacer(24)
                    label = "Reopen" if is_active else "Continue with this"
                    if st.button(label, key=f"pick-{ds['id']}", type="primary", use_container_width=True):
                        _select_dataset(ds, models)

                if is_active:
                    badge("Currently open")

                if models:
                    st.caption(f"{len(models)} trained model{'s' if len(models) > 1 else ''}")
                    st.dataframe(
                        [
                            {
                                "Algorithm": m["algo"],
                                "RMSE (log)": m["metrics"]["rmse_log"],
                                "R²": m["metrics"].get("r2", "—"),
                                "Trained": _pretty_date(m["created_at"]),
                            }
                            for m in models
                        ],
                        hide_index=True,
                    )
                else:
                    st.caption("No models trained on this dataset yet.")

        spacer(24)
        if st.button("Upload another dataset", use_container_width=True):
            st.session_state.page = "Upload"
            st.rerun()


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
                    st.session_state.token, uploaded, st.session_state.dataset_name, TARGET_COLUMN
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
                    st.session_state.token, url, st.session_state.dataset_name, TARGET_COLUMN
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
        preview = api_client.get_dataset(st.session_state.token, dataset_id, limit=1)
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
        return _cached_get_full_dataset(st.session_state.token, st.session_state.dataset_id)
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

    if algo in st.session_state.models:
        with st.container(border=True):
            st.subheader(f"Result — {algo}")
            metrics = st.session_state.models[algo]["metrics"]
            with st.container(border=True):
                st.html(
                    f"<div class='rmse-box-label'>RMSE: {metrics['rmse_log']} &nbsp;·&nbsp; "
                    f"R²: {metrics.get('r2', '—')}</div>"
                )
            spacer(36)
            badge("Model successfully trained and saved!", large=True)
            spacer(24)

    if st.session_state.models:
        spacer(24)
        with st.container(border=True):
            st.subheader("Model comparison")
            comparison = pd.DataFrame(
                [
                    {"Model": name, "RMSE (log price)": m["metrics"]["rmse_log"], "R²": m["metrics"].get("r2", "—")}
                    for name, m in st.session_state.models.items()
                ]
            )
            st.dataframe(comparison, hide_index=True, use_container_width=True)

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
                    st.session_state.token,
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
                    if not importances:
                        st.caption("This model was trained before importances were recorded. Retrain it to see them.")
                    else:
                        labels = list(importances.keys())[::-1]
                        values = list(importances.values())[::-1]
                        fig_imp, ax_imp = plt.subplots(figsize=(7, 4))
                        ax_imp.barh(labels, values, color=COLORS["accent"])
                        ax_imp.set_xlabel("Importance (increase in RMSE when shuffled)")
                        ax_imp.spines[["top", "right"]].set_visible(False)
                        st.pyplot(fig_imp)
                        plt.close(fig_imp)

                with st.container(border=True):
                    st.subheader("Where this prediction falls")
                    df_total_sf = df["TotalBsmtSF"] + df["1stFlrSF"] + df["2ndFlrSF"]
                    fig, ax = plt.subplots(figsize=(7, 5))
                    ax.scatter(df_total_sf, df["SalePrice"], alpha=0.35, color=COLORS["accent"], label="Historical sales")
                    ax.scatter([total_sf], [price], s=140, color=COLORS["highlight"], edgecolor=COLORS["white"], linewidth=1.5, zorder=5, label="Your estimate")
                    ax.axhline(price, color=COLORS["highlight"], linestyle="--", linewidth=1, alpha=0.6)
                    ax.axvline(total_sf, color=COLORS["highlight"], linestyle="--", linewidth=1, alpha=0.6)
                    ax.set_xlabel("Total Square Footage (sq ft)")
                    ax.set_ylabel("SalePrice")
                    ax.spines[["top", "right"]].set_visible(False)
                    ax.legend(loc="upper left", fontsize=9, frameon=False)
                    st.pyplot(fig)
                    plt.close(fig)

                with st.container(border=True):
                    st.metric("Estimated Price", f"${price:,.0f}", help=f"{model_name} on {total_sf:,} sq ft · {neighborhood}")
        else:
            note("Select specifications and click Predict Price.")


def _prep_frame() -> pd.DataFrame | None:
    df = _require_dataset()
    if df is None:
        return None
    if st.session_state.prep_df is None or st.session_state.prep_source != st.session_state.dataset_id:
        st.session_state.prep_df = df.copy()
        st.session_state.prep_source = st.session_state.dataset_id
        st.session_state.pop("prep_shown", None)
    return st.session_state.prep_df


def render_prepare():
    crumb("Prepare data")
    st.title("Prepare data")
    st.html("<p class='subtitle'>Trim columns, inspect the frame, plot it, then save it as a new dataset</p>")

    prep = _prep_frame()
    if prep is None:
        return

    all_columns = list(prep.columns)

    with st.container(border=True):
        st.subheader("Columns")
        st.caption("Unticking a column hides it here. Dropping removes it from the data you save.")
        shown = st.multiselect("Columns in view", all_columns, default=all_columns, key="prep_shown")
        hidden = [c for c in all_columns if c not in shown]

        drop_col, reset_col = st.columns(2)
        with drop_col:
            if st.button(
                f"Drop {len(hidden)} hidden column{'s' if len(hidden) != 1 else ''}",
                disabled=not hidden,
                use_container_width=True,
            ):
                st.session_state.prep_df = prep.drop(columns=hidden)
                st.session_state.pop("prep_shown", None)
                st.rerun()
        with reset_col:
            if st.button("Reset to uploaded data", use_container_width=True):
                st.session_state.prep_df = None
                st.session_state.pop("prep_shown", None)
                st.rerun()

        st.caption(f"{len(prep):,} rows \u00b7 {len(all_columns)} columns kept \u00b7 {len(shown)} shown")
        st.dataframe(prep[shown], use_container_width=True, height=360)

    if not shown:
        note("Tick at least one column to inspect or plot it.")
        return

    with st.container(border=True):
        st.subheader("Inspect")
        head_tab, info_tab, describe_tab, missing_tab = st.tabs(
            ["head()", "info()", "describe()", "Missing values"]
        )
        with head_tab:
            n = st.slider("Rows", 1, 50, 5, key="prep_head_n")
            st.dataframe(prep[shown].head(n), use_container_width=True)
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
            note("Pick an X or Y column to draw a plot.")

    with st.container(border=True):
        st.subheader("Save")
        target = TARGET_COLUMN if TARGET_COLUMN in prep.columns else all_columns[0]
        st.caption(f"Saved as a new dataset with target column {target}.")
        name_col, button_col = st.columns([3, 1])
        with name_col:
            new_name = st.text_input("Save as", value=f"{st.session_state.dataset_name}-prepared")
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
                    badge(
                        f"Saved as \u201c{new_name.strip()}\u201d \u2014 "
                        f"{saved['n_rows']:,} rows \u00d7 {len(prep.columns)} columns",
                        large=True,
                    )


ROUTES = {
    "Datasets": render_datasets,
    "Upload": render_upload,
    "Explore": render_eda,
    "Train": render_train,
    "Predict": render_predict,
    "Prepare": render_prepare,
}
NAV = {
    "v1 \u00b7 guided flow": ["Datasets", "Upload", "Explore", "Train", "Predict"],
    "Data lab": ["Prepare"],
}

if st.session_state.token is None:
    render_auth()
else:
    sidebar()
    ROUTES[st.session_state.page]()
