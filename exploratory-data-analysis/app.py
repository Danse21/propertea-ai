import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st

MODELS_DIR = Path(__file__).parent / "models"

st.set_page_config(page_title="Estimate House Price", page_icon="🏠", layout="centered")


@st.cache_resource
def load_pipelines():
    return {
        "Linear Regression (Ridge)": joblib.load(MODELS_DIR / "ridge_pipeline.joblib"),
        "Decision Tree": joblib.load(MODELS_DIR / "decisiontree_pipeline.joblib"),
    }


@st.cache_data
def load_defaults():
    with open(MODELS_DIR / "defaults.json") as f:
        return json.load(f)


@st.cache_data
def load_categorical_options():
    with open(MODELS_DIR / "categorical_options.json") as f:
        return json.load(f)


pipelines = load_pipelines()
defaults = load_defaults()
options = load_categorical_options()

st.markdown(
    """
    <style>
    .block-container { max-width: 640px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏠 Estimate House Price")
st.caption(
    "Proof of concept — the model is trained on the Ames Housing dataset (USD, sales 2006–2010). "
    "The focus is showing the flow works, not exact price estimates."
)

with st.container(border=True):
    st.subheader("Find a home")

    neighborhood = st.selectbox("Neighborhood", options["Neighborhood"])
    bldg_type = st.selectbox("Building type", options["BldgType"])

    col1, col2 = st.columns(2)
    with col1:
        overall_qual = st.slider("Overall quality", 1, 10, int(defaults["OverallQual"]))
        gr_liv_area = st.number_input("Living area (sqft)", min_value=300, max_value=6000, value=int(defaults["GrLivArea"]))
        total_bsmt_sf = st.number_input("Basement area (sqft)", min_value=0, max_value=6000, value=int(defaults["TotalBsmtSF"]))
    with col2:
        year_built = st.slider("Year built", 1870, 2010, int(defaults["YearBuilt"]))
        garage_cars = st.slider("Garage car capacity", 0, 4, int(defaults["GarageCars"]))
        tot_rms = st.slider("Number of rooms", 2, 14, int(defaults["TotRmsAbvGrd"]))

    kitchen_qual = st.selectbox("Kitchen quality", options["KitchenQual"])

    model_name = st.selectbox("Model", list(pipelines.keys()))

    predict_clicked = st.button("Estimate price", type="primary", use_container_width=True)

if predict_clicked:
    row = dict(defaults)
    row.update(
        {
            "Neighborhood": neighborhood,
            "BldgType": bldg_type,
            "OverallQual": overall_qual,
            "GrLivArea": gr_liv_area,
            "TotalBsmtSF": total_bsmt_sf,
            "YearBuilt": year_built,
            "GarageCars": garage_cars,
            "TotRmsAbvGrd": tot_rms,
            "KitchenQual": kitchen_qual,
        }
    )
    # Recompute engineered features from the (possibly overridden) raw inputs.
    # GrLivArea already sums 1stFlrSF + 2ndFlrSF (+ LowQualFinSF, ~0 for 98% of rows),
    # so TotalSF = TotalBsmtSF + GrLivArea is a close approximation of the training-time formula.
    row["TotalSF"] = row["TotalBsmtSF"] + row["GrLivArea"]
    row["HouseAge"] = row["YrSold"] - row["YearBuilt"]

    X_pred = pd.DataFrame([row])
    pipeline = pipelines[model_name]
    log_price = pipeline.predict(X_pred)[0]
    price = np.expm1(log_price)

    st.metric("Estimated price", f"${price:,.0f}")
