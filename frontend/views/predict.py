import matplotlib.pyplot as plt
import streamlit as st

import api_client
import state
from theme import COLORS
from ui import note, page_header


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
    state.active_dataset_bar()

    df = state.require_ames_dataset()
    if df is None:
        return
    if not st.session_state.models:
        state.missing_prerequisite(
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
