import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.services.modeling import (
    MODELS,
    build_predict_row,
    compute_defaults,
    get_feature_importances,
    train_model,
)
from app.services.preprocessing import (
    FEATURES_COLUMNS,
    TARGET_COLUMN,
    engineer_features,
    prepare_data,
)


def make_valid_df(n_rows: int = 5) -> pd.DataFrame:
    rows = []
    for i in range(n_rows):
        row = {col: 0 for col in FEATURES_COLUMNS}
        row.update(
            {
                "MSSubClass": 60,
                "Neighborhood": "CollgCr",
                "TotalBsmtSF": 800,
                "1stFlrSF": 900,
                "2ndFlrSF": 200,
                "GrLivArea": 1100,
                "YearBuilt": 2000,
                "YearRemodAdd": 2000,
                "YrSold": 2008,
                "OverallQual": 5,
                "FullBath": 2,
                "GarageCars": 1,
                "KitchenQual": "TA",
            }
        )
        row["Id"] = i + 1
        row[TARGET_COLUMN] = 150_000 + i * 10_000
        rows.append(row)
    return pd.DataFrame(rows)


def make_training_df(n_rows: int = 40) -> pd.DataFrame:
    """Enough rows, with real numeric variation, for GridSearchCV's cv folds to be non-degenerate."""
    rng = np.random.default_rng(0)
    rows = []
    for i in range(n_rows):
        row = {col: 0 for col in FEATURES_COLUMNS}
        overall_qual = int(rng.integers(1, 10))
        gr_liv_area = int(rng.integers(800, 3000))
        row.update(
            {
                "MSSubClass": 60,
                "Neighborhood": "CollgCr",
                "OverallQual": overall_qual,
                "TotalBsmtSF": int(rng.integers(0, 2000)),
                "1stFlrSF": int(rng.integers(500, 2000)),
                "2ndFlrSF": int(rng.integers(0, 1500)),
                "GrLivArea": gr_liv_area,
                "YearBuilt": int(rng.integers(1950, 2010)),
                "YearRemodAdd": 2000,
                "YrSold": 2008,
                "FullBath": int(rng.integers(1, 4)),
                "GarageCars": int(rng.integers(0, 4)),
                "KitchenQual": "TA",
            }
        )
        row["Id"] = i + 1
        row[TARGET_COLUMN] = 80_000 + overall_qual * 15_000 + gr_liv_area * 40 + rng.normal(scale=5000)
        rows.append(row)
    return pd.DataFrame(rows)


class TestTrainModel:
    @pytest.mark.parametrize("algo", list(MODELS.keys()))
    def test_trains_without_error_and_reports_a_plausible_rmse(self, algo):
        df = make_training_df()
        result = train_model(df, algo)
        rmse = result["metrics"]["rmse_log"]
        assert 0 < rmse < 1.0

    @pytest.mark.parametrize("algo", list(MODELS.keys()))
    def test_trains_without_error_and_reports_a_plausible_r2(self, algo):
        df = make_training_df()
        result = train_model(df, algo)
        r2 = result["metrics"]["r2"]
        assert -1.0 < r2 <= 1.0

    @pytest.mark.parametrize("algo", list(MODELS.keys()))
    def test_returned_pipeline_can_predict_a_single_row(self, algo):
        df = make_training_df()
        result = train_model(df, algo)
        row = build_predict_row(result["defaults"], {"OverallQual": 8})
        prediction = result["pipeline"].predict(row)
        assert len(prediction) == 1

    def test_linear_regression_has_no_tuned_params(self):
        result = train_model(make_training_df(), "Linear Regression")
        assert result["best_params"] is None

    @pytest.mark.parametrize("algo", ["Ridge", "Lasso", "Elastic Net", "Random Forest"])
    def test_tuned_models_report_best_params_from_their_grid(self, algo):
        result = train_model(make_training_df(), algo)
        assert result["best_params"] is not None
        for param_name, value in result["best_params"].items():
            assert value in MODELS[algo]["param_grid"][param_name]


class TestGetFeatureImportances:
    def _fit_toy_pipeline(self):
        rng = np.random.default_rng(0)
        X = pd.DataFrame(
            {
                "important": rng.normal(size=200),
                "noise": rng.normal(size=200),
            }
        )
        y = X["important"] * 5 + rng.normal(scale=0.1, size=200)
        pipeline = Pipeline([("scale", StandardScaler()), ("model", LinearRegression())])
        pipeline.fit(X, y)
        return pipeline, X, y

    def test_ranks_the_informative_feature_first(self):
        pipeline, X, y = self._fit_toy_pipeline()
        result = get_feature_importances(pipeline, X, y, top_n=2)
        assert result.index[0] == "important"

    def test_respects_top_n(self):
        pipeline, X, y = self._fit_toy_pipeline()
        result = get_feature_importances(pipeline, X, y, top_n=1)
        assert len(result) == 1

    def test_sorted_descending(self):
        pipeline, X, y = self._fit_toy_pipeline()
        result = get_feature_importances(pipeline, X, y)
        assert list(result) == sorted(result, reverse=True)


class TestBuildPredictRow:
    def test_overrides_win_over_defaults(self):
        df = make_valid_df()
        row = build_predict_row(compute_defaults(prepare_data(df)), {"OverallQual": 9})
        assert row["OverallQual"].iloc[0] == 9

    def test_total_sf_and_house_age_match_engineer_features_exactly(self):
        df = make_valid_df()
        overrides = {"1stFlrSF": 1200, "2ndFlrSF": 1000, "TotalBsmtSF": 1100, "YearBuilt": 2005}
        row = build_predict_row(compute_defaults(prepare_data(df)), overrides)

        expected = engineer_features(row.drop(columns=["TotalSF", "HouseAge"]))
        assert row["TotalSF"].iloc[0] == expected["TotalSF"].iloc[0]
        assert row["HouseAge"].iloc[0] == expected["HouseAge"].iloc[0]
        assert row["TotalSF"].iloc[0] == 1100 + 1200 + 1000

    def test_returns_single_row(self):
        df = make_valid_df()
        row = build_predict_row(compute_defaults(prepare_data(df)), {})
        assert len(row) == 1

