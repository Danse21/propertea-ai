"""EDA helpers and validation for the Streamlit frontend."""

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.preprocessing import (  # noqa: E402
    NA_IS_CATEGORY,
    TARGET_COLUMN,
    DataValidationError,
    validate_data,
)

MISSINGNESS_COLUMNS = [
    "PoolQC", "MiscFeature", "Alley", "Fence", "FireplaceQu",
    "LotFrontage", "GarageYrBlt", "BsmtExposure", "MasVnrType", "Electrical",
]

CORR_MOVERS = [
    "OverallQual", "GrLivArea", "GarageCars", "GarageArea", "TotalBsmtSF",
    "1stFlrSF", "FullBath", "TotRmsAbvGrd", "YearBuilt", "YearRemodAdd",
]

CORR_LEGEND = [
    ("Qual", "OverallQual", "Overall quality"),
    ("GrLiv", "GrLivArea", "Above-grade living area"),
    ("GarCars", "GarageCars", "Garage capacity, in cars"),
    ("GarArea", "GarageArea", "Garage size, sq ft"),
    ("Bsmt", "TotalBsmtSF", "Total basement area, sq ft"),
    ("1stFlr", "1stFlrSF", "First floor area, sq ft"),
    ("Bath", "FullBath", "Full bathrooms"),
    ("Rooms", "TotRmsAbvGrd", "Total rooms above ground"),
    ("YrBlt", "YearBuilt", "Year built"),
    ("YrRemod", "YearRemodAdd", "Year last renovated"),
]


def missingness_summary(df: pd.DataFrame) -> pd.Series:
    pct = (df.isna().sum() / len(df) * 100).round(1)
    return pct[pct > 0].sort_values(ascending=False)


def top_mover_correlations(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in CORR_MOVERS if c in df.columns]
    return df[cols].corr()
