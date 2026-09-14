"""Data cleaning and feature engineering for the Ames Housing price dataset."""

import pandas as pd


NA_IS_CATEGORY = [
    "Alley", "BsmtQual", "BsmtCond", "BsmtExposure", "BsmtFinType1", "BsmtFinType2",
    "FireplaceQu", "GarageType", "GarageFinish", "GarageQual", "GarageCond",
    "PoolQC", "Fence", "MiscFeature",
]

OUTLIER_IDS = [524, 1299]

FEATURES_COLUMNS = [
    "MSSubClass", "MSZoning", "LotFrontage", "LotArea", "Street", "Alley", "LotShape",
    "LandContour", "Utilities", "LotConfig", "LandSlope", "Neighborhood", "Condition1",
    "Condition2", "BldgType", "HouseStyle", "OverallQual", "OverallCond", "YearBuilt",
    "YearRemodAdd", "RoofStyle", "RoofMatl", "Exterior1st", "Exterior2nd", "MasVnrType",
    "MasVnrArea", "ExterQual", "ExterCond", "Foundation", "BsmtQual", "BsmtCond",
    "BsmtExposure", "BsmtFinType1", "BsmtFinSF1", "BsmtFinType2", "BsmtFinSF2",
    "BsmtUnfSF", "TotalBsmtSF", "Heating", "HeatingQC", "CentralAir", "Electrical",
    "1stFlrSF", "2ndFlrSF", "LowQualFinSF", "GrLivArea", "BsmtFullBath", "BsmtHalfBath",
    "FullBath", "HalfBath", "BedroomAbvGr", "KitchenAbvGr", "KitchenQual", "TotRmsAbvGrd",
    "Functional", "Fireplaces", "FireplaceQu", "GarageType", "GarageYrBlt",
    "GarageFinish", "GarageCars", "GarageArea", "GarageQual", "GarageCond", "PavedDrive",
    "WoodDeckSF", "OpenPorchSF", "EnclosedPorch", "3SsnPorch", "ScreenPorch", "PoolArea",
    "PoolQC", "Fence", "MiscFeature", "MiscVal", "MoSold", "YrSold", "SaleType",
    "SaleCondition",
]

TARGET_COLUMN = "SalePrice"

class DataValidationError(ValueError):
    """Raised when a DataFrame doesn't look like valid Ames Housing data."""

def validate_data(df: pd.DataFrame, *, require_target: bool = True) -> None:
   
    errors = []

    if df.empty:
        errors.append("Dataset is empty.")

    missing_cols = [c for c in FEATURES_COLUMNS if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing expected columns: {missing_cols}")

    if require_target and TARGET_COLUMN not in df.columns:
        errors.append(f"Missing target column: {TARGET_COLUMN}")

    if errors:
        raise DataValidationError("; ".join(errors))


def clean_data(df: pd.DataFrame, *, drop_outliers: bool = True) -> pd.DataFrame:

    df = df.copy()

    if drop_outliers and "Id" in df.columns:
        df = df[~df["Id"].isin(OUTLIER_IDS)]

    na_category_cols = [c for c in NA_IS_CATEGORY if c in df.columns]
    if na_category_cols:
        df[na_category_cols] = df[na_category_cols].fillna("None")

    if "MSSubClass" in df.columns:
        df["MSSubClass"] = df["MSSubClass"].astype(str)

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    
    df = df.copy()

    if {"TotalBsmtSF", "1stFlrSF", "2ndFlrSF"}.issubset(df.columns):
        df["TotalSF"] = df["TotalBsmtSF"] + df["1stFlrSF"] + df["2ndFlrSF"]

    if {"YrSold", "YearBuilt"}.issubset(df.columns):
        df["HouseAge"] = df["YrSold"] - df["YearBuilt"]

    return df


def prepare_data(df: pd.DataFrame, *, drop_outliers: bool = True, require_target: bool = True) -> pd.DataFrame:
    """Single entry point: validate_data(), then clean_data(), then engineer_features()."""
    validate_data(df, require_target=require_target)
    return engineer_features(clean_data(df, drop_outliers=drop_outliers))
