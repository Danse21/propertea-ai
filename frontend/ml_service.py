"""Data loading, training, and prediction helpers for the Streamlit frontend."""

import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import root_mean_squared_error
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeRegressor

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.preprocessing import (  # noqa: E402
    NA_IS_CATEGORY,
    TARGET_COLUMN,
    DataValidationError,
    engineer_features,
    prepare_data,
    validate_data,
)

DEFAULT_DATA_PATH = REPO_ROOT / "exploratory-data-analysis" / "data" / "train.csv"

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

MODELS = {
    "Linear Regression": {
        "build": lambda: LinearRegression(),
        "param_grid": {},
    },
    "Decision Tree": {
        "build": lambda: DecisionTreeRegressor(random_state=42),
        "param_grid": {"model__max_depth": [4, 6, 8], "model__min_samples_leaf": [5, 10]},
    },
    "Random Forest": {
        "build": lambda: RandomForestRegressor(n_estimators=50, random_state=42),
        "param_grid": {"model__max_depth": [6, 10]},
    },
}


MAX_URL_DOWNLOAD_BYTES = 200 * 1024 * 1024
URL_FETCH_TIMEOUT_SECONDS = 60


def load_dataset_from_url(url: str) -> pd.DataFrame:
    """Fetch a CSV from a user-supplied URL with a timeout and a size cap."""
    with requests.get(url, timeout=URL_FETCH_TIMEOUT_SECONDS, stream=True) as response:
        response.raise_for_status()

        content_length = response.headers.get("Content-Length")
        if content_length is not None and int(content_length) > MAX_URL_DOWNLOAD_BYTES:
            raise ValueError(f"File is too large ({int(content_length):,} bytes) — max is {MAX_URL_DOWNLOAD_BYTES:,}.")

        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            total += len(chunk)
            if total > MAX_URL_DOWNLOAD_BYTES:
                raise ValueError(f"File exceeded the {MAX_URL_DOWNLOAD_BYTES:,}-byte limit while downloading.")
            chunks.append(chunk)

    content = io.BytesIO(b"".join(chunks))
    return pd.read_csv(content, na_values=["NA"], keep_default_na=False)


def load_dataset_from_upload(file) -> pd.DataFrame:
    return pd.read_csv(file, na_values=["NA"], keep_default_na=False)


def missingness_summary(df: pd.DataFrame) -> pd.Series:
    pct = (df.isna().sum() / len(df) * 100).round(1)
    return pct[pct > 0].sort_values(ascending=False)


def top_mover_correlations(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in CORR_MOVERS if c in df.columns]
    return df[cols].corr()


def _build_pipeline(X: pd.DataFrame, algo: str) -> Pipeline:
    numeric_features = X.select_dtypes(include="number").columns.tolist()
    categorical_features = X.select_dtypes(exclude="number").columns.tolist()

    numeric_transformer = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])
    categorical_transformer = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    preprocessor = ColumnTransformer([
        ("num", numeric_transformer, numeric_features),
        ("cat", categorical_transformer, categorical_features),
    ])
    return Pipeline([("preprocess", preprocessor), ("model", MODELS[algo]["build"]())])


def train_model(raw_df: pd.DataFrame, algo: str) -> dict:
    """Clean, engineer features, tune (if the model has anything to tune), fit, and evaluate."""
    df = prepare_data(raw_df, drop_outliers=True, require_target=True)
    y = np.log1p(df[TARGET_COLUMN])
    X = df.drop(columns=["Id", TARGET_COLUMN], errors="ignore")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    pipeline = _build_pipeline(X, algo)
    param_grid = MODELS[algo]["param_grid"]
    best_params = None

    if param_grid:
        search = GridSearchCV(pipeline, param_grid, cv=3, scoring="neg_root_mean_squared_error", n_jobs=2)
        search.fit(X_train, y_train)
        pipeline = search.best_estimator_
        best_params = search.best_params_
    else:
        pipeline.fit(X_train, y_train)

    pred = pipeline.predict(X_test)
    rmse = root_mean_squared_error(y_test, pred)

    importances = get_feature_importances(pipeline, X_test, y_test)

    pipeline.fit(X, y)

    return {
        "algo": algo,
        "pipeline": pipeline,
        "metrics": {"rmse_log": round(float(rmse), 3)},
        "importances": importances,
        "best_params": best_params,
    }


def get_feature_importances(pipeline: Pipeline, X: pd.DataFrame, y: pd.Series, top_n: int = 10) -> pd.Series:
    """Permutation importance, one value per original column (not per one-hot dummy)."""
    result = permutation_importance(
        pipeline, X, y, n_repeats=5, random_state=42, scoring="neg_root_mean_squared_error", n_jobs=2
    )
    importances = pd.Series(result.importances_mean, index=X.columns)
    return importances.sort_values(ascending=False).head(top_n)


def build_predict_row(raw_df: pd.DataFrame, overrides: dict) -> pd.DataFrame:
    """One input row: dataset medians/modes filled in, overrides layered on top."""
    df = prepare_data(raw_df, drop_outliers=True, require_target=True)

    defaults = {}
    for col in df.columns:
        if col in ("Id", TARGET_COLUMN):
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            defaults[col] = df[col].median()
        else:
            defaults[col] = df[col].mode().iloc[0]

    row = dict(defaults)
    row.update(overrides)

    return engineer_features(pd.DataFrame([row]))
