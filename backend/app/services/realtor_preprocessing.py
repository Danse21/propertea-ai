"""Data cleaning and feature engineering for the Realtor real estate dataset."""

import pandas as pd


FEATURES_COLUMNS = [
    "status",
    "bed",
    "bath",
    "acre_lot",
    "city",
    "state",
    "zip_code",
    "house_size",
    "prev_sold_date",
]

TARGET_COLUMN = "price"


class DataValidationError(ValueError):
    """Raised when a DataFrame doesn't look like valid Realtor data."""


def validate_data(
    df: pd.DataFrame,
    *,
    require_target: bool = True,
) -> None:
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


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Rows without a target cannot be used for training.
    df = df.dropna(subset=[TARGET_COLUMN])

    # Price must be positive.
    df = df.loc[df[TARGET_COLUMN] > 0]

    # Remove clearly corrupted extreme values.
    df = df.loc[df["bed"].isna() | (df["bed"] <= 20)]
    df = df.loc[df["bath"].isna() | (df["bath"] <= 20)]
    df = df.loc[df["house_size"].isna() | (df["house_size"] <= 20_000)]
    df = df.loc[df["acre_lot"].isna() | (df["acre_lot"] <= 1_000)]

    # Convert previous sale date to datetime.
    df["prev_sold_date"] = pd.to_datetime(
        df["prev_sold_date"],
        errors="coerce",
    )

    # Remove clearly invalid future dates.
    df.loc[
        df["prev_sold_date"].dt.year > 2026,
        "prev_sold_date",
    ] = pd.NaT

    
    df = df.drop(
        columns=["street", "brokered_by"],
        errors="ignore",
    )

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "prev_sold_date" in df.columns:
        df["prev_sold_year"] = df["prev_sold_date"].dt.year

        
        df = df.drop(columns=["prev_sold_date"])

    return df


def prepare_data(
    df: pd.DataFrame,
    *,
    require_target: bool = True,
) -> pd.DataFrame:
    """Validate, clean and engineer features for the Realtor dataset."""

    validate_data(
        df,
        require_target=require_target,
    )

    df = clean_data(df)

    return engineer_features(df)