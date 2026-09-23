import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeRegressor

from app.services.realtor_preprocessing import (
    TARGET_COLUMN,
    prepare_data,
)


NUMERIC_FEATURES = [
    "bed",
    "bath",
    "acre_lot",
    "house_size",
    "prev_sold_year",
]

CATEGORICAL_FEATURES = [
    "status",
    "city",
    "state",
    "zip_code",
]



def build_pipeline(model=None) -> Pipeline:
    numeric_transformer = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )

    categorical_transformer = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        [
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ]
    )

    if model is None:
        model = LinearRegression()

    return Pipeline(
        [
            ("preprocess", preprocessor),
            ("model", model),
        ]
    )



from sklearn.metrics import root_mean_squared_error
from sklearn.model_selection import train_test_split


def train_model(
    raw_df: pd.DataFrame,
    model=None,
) -> dict:
    df = prepare_data(raw_df)

    X = df.drop(columns=[TARGET_COLUMN])
    y = np.log1p(df[TARGET_COLUMN])

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )

    pipeline = build_pipeline(model)

    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)

    rmse = root_mean_squared_error(
        y_test,
        predictions,
    )

    return {
        "model": pipeline,
        "rmse_log": float(rmse),
    }