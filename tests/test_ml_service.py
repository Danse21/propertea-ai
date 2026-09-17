from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from backend.app.services.preprocessing import FEATURES_COLUMNS, TARGET_COLUMN, engineer_features
from frontend.ml_service import (
    MAX_URL_DOWNLOAD_BYTES,
    MODELS,
    build_predict_row,
    get_feature_importances,
    load_dataset_from_url,
    missingness_summary,
    top_mover_correlations,
    train_model,
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
    """Bigger than make_valid_df() and with real numeric variation.

    train_model()'s GridSearchCV/cv folds need non-degenerate data to fit
    and score meaningfully — make_valid_df()'s single repeated row works
    for pure unit tests but would give every cv fold identical data here.
    """
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
        # Regression guard for the exact bug this class was added for: an
        # accidental extra sqrt() inflates a small RMSE (e.g. sqrt(0.141) =
        # 0.375), so bounding it well below 1.0 on the log-price scale
        # would have caught it immediately.
        assert 0 < rmse < 1.0

    @pytest.mark.parametrize("algo", list(MODELS.keys()))
    def test_returned_pipeline_can_predict_a_single_row(self, algo):
        df = make_training_df()
        result = train_model(df, algo)
        row = build_predict_row(df, {"OverallQual": 8})
        prediction = result["pipeline"].predict(row)
        assert len(prediction) == 1

    def test_linear_regression_has_no_tuned_params(self):
        result = train_model(make_training_df(), "Linear Regression")
        assert result["best_params"] is None

    @pytest.mark.parametrize("algo", ["Decision Tree", "Random Forest"])
    def test_tuned_models_report_best_params_from_their_grid(self, algo):
        result = train_model(make_training_df(), algo)
        assert result["best_params"] is not None
        for param_name, value in result["best_params"].items():
            assert value in MODELS[algo]["param_grid"][param_name]


class TestMissingnessSummary:
    def test_reports_percent_missing_sorted_descending(self):
        df = pd.DataFrame(
            {
                "A": [1, None, None, None],
                "B": [1, 2, None, 4],
                "C": [1, 2, 3, 4],
            }
        )
        result = missingness_summary(df)
        assert list(result.index) == ["A", "B"]
        assert result["A"] == 75.0
        assert result["B"] == 25.0

    def test_excludes_fully_present_columns(self):
        df = pd.DataFrame({"A": [1, 2, 3]})
        result = missingness_summary(df)
        assert result.empty


class TestTopMoverCorrelations:
    def test_returns_square_matrix_of_present_columns(self):
        df = pd.DataFrame(
            {
                "OverallQual": [1, 3, 5, 7, 9],
                "GrLivArea": [1000, 1200, 1400, 1600, 1800],
            }
        )
        result = top_mover_correlations(df)
        assert set(result.columns) == {"OverallQual", "GrLivArea"}
        assert result.shape[0] == result.shape[1]

    def test_ignores_movers_not_present_in_df(self):
        df = pd.DataFrame({"OverallQual": [1, 2, 3], "SomeOtherColumn": [1, 2, 3]})
        result = top_mover_correlations(df)
        assert list(result.columns) == ["OverallQual"]


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
        row = build_predict_row(df, {"OverallQual": 9})
        assert row["OverallQual"].iloc[0] == 9

    def test_total_sf_and_house_age_match_engineer_features_exactly(self):
        df = make_valid_df()
        overrides = {"1stFlrSF": 1200, "2ndFlrSF": 1000, "TotalBsmtSF": 1100, "YearBuilt": 2005}
        row = build_predict_row(df, overrides)

        expected = engineer_features(row.drop(columns=["TotalSF", "HouseAge"]))
        assert row["TotalSF"].iloc[0] == expected["TotalSF"].iloc[0]
        assert row["HouseAge"].iloc[0] == expected["HouseAge"].iloc[0]
        assert row["TotalSF"].iloc[0] == 1100 + 1200 + 1000

    def test_returns_single_row(self):
        df = make_valid_df()
        row = build_predict_row(df, {})
        assert len(row) == 1


class TestLoadDatasetFromUrl:
    def _mock_response(self, headers=None, chunks=None):
        response = MagicMock()
        response.headers = headers or {}
        response.raise_for_status.return_value = None
        response.iter_content.return_value = chunks or []
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        return response

    def test_rejects_when_content_length_header_exceeds_cap(self):
        response = self._mock_response(headers={"Content-Length": str(MAX_URL_DOWNLOAD_BYTES + 1)})
        with patch("frontend.ml_service.requests.get", return_value=response):
            with pytest.raises(ValueError, match="too large"):
                load_dataset_from_url("http://example.com/big.csv")

    def test_rejects_when_streamed_bytes_exceed_cap_without_content_length(self):
        big_chunk = b"x" * (MAX_URL_DOWNLOAD_BYTES // 2 + 1)
        response = self._mock_response(chunks=[big_chunk, big_chunk])
        with patch("frontend.ml_service.requests.get", return_value=response):
            with pytest.raises(ValueError, match="exceeded"):
                load_dataset_from_url("http://example.com/big.csv")

    def test_successfully_parses_a_small_csv(self):
        csv_bytes = b"Id,SalePrice\n1,200000\n2,150000\n"
        response = self._mock_response(chunks=[csv_bytes])
        with patch("frontend.ml_service.requests.get", return_value=response):
            df = load_dataset_from_url("http://example.com/small.csv")
        assert list(df.columns) == ["Id", "SalePrice"]
        assert len(df) == 2
