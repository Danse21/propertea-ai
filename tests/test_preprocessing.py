import numpy as np
import pandas as pd
import pytest

from backend.app.services.preprocessing import (
    FEATURES_COLUMNS,
    NA_IS_CATEGORY,
    OUTLIER_IDS,
    TARGET_COLUMN,
    DataValidationError,
    clean_data,
    engineer_features,
    prepare_data,
    validate_data,
)

def make_valid_df(n_rows: int = 2) -> pd.DataFrame:
    
    rows = []
    for i in range(n_rows):
        row = {col: 0 for col in FEATURES_COLUMNS}
        row.update(
            {
                "MSSubClass": 60,
                "TotalBsmtSF": 800,
                "1stFlrSF": 900,
                "2ndFlrSF": 200,
                "YearBuilt": 2000,
                "YrSold": 2008,
            }
        )
        row["Id"] = i + 1
        row[TARGET_COLUMN] = 200_000
        rows.append(row)
    return pd.DataFrame(rows)


class TestValidateData:
    def test_valid_data_passes(self):
        validate_data(make_valid_df())

    def test_empty_dataframe_raises(self):
        df = make_valid_df().iloc[0:0]
        with pytest.raises(DataValidationError, match="empty"):
            validate_data(df)

    def test_missing_feature_column_raises(self):
        df = make_valid_df().drop(columns=["Neighborhood"])
        with pytest.raises(DataValidationError, match="Neighborhood"):
            validate_data(df)

    def test_missing_target_raises_when_required(self):
        df = make_valid_df().drop(columns=[TARGET_COLUMN])
        with pytest.raises(DataValidationError, match=TARGET_COLUMN):
            validate_data(df, require_target=True)

    def test_missing_target_ok_when_not_required(self):
        df = make_valid_df().drop(columns=[TARGET_COLUMN])
        validate_data(df, require_target=False)

    def test_reports_all_problems_at_once(self):
        df = make_valid_df().drop(columns=["Neighborhood", TARGET_COLUMN]).iloc[0:0]
        with pytest.raises(DataValidationError) as exc_info:
            validate_data(df, require_target=True)
        message = str(exc_info.value)
        assert "empty" in message
        assert "Neighborhood" in message
        assert TARGET_COLUMN in message


class TestCleanData:
    def test_drops_known_outlier_ids(self):
        df = pd.DataFrame({"Id": [1, OUTLIER_IDS[0], OUTLIER_IDS[1], 2]})
        result = clean_data(df)
        assert sorted(result["Id"]) == [1, 2]

    def test_keeps_outliers_when_disabled(self):
        df = pd.DataFrame({"Id": [1, OUTLIER_IDS[0]]})
        result = clean_data(df, drop_outliers=False)
        assert OUTLIER_IDS[0] in result["Id"].values

    def test_no_id_column_does_not_crash(self):
        df = pd.DataFrame({"MSSubClass": [60]})
        result = clean_data(df)
        assert len(result) == 1

    @pytest.mark.parametrize("col", NA_IS_CATEGORY)
    def test_na_is_category_columns_filled_with_none_string(self, col):
        df = pd.DataFrame({col: [np.nan, "Gd"]})
        result = clean_data(df)
        assert result[col].tolist() == ["None", "Gd"]

    def test_mssubclass_cast_to_string(self):
        df = pd.DataFrame({"MSSubClass": [60, 20]})
        result = clean_data(df)
        assert result["MSSubClass"].tolist() == ["60", "20"]
        assert pd.api.types.is_string_dtype(result["MSSubClass"])

    def test_does_not_mutate_caller_dataframe(self):
        original = pd.DataFrame({"MSSubClass": [60]})
        clean_data(original)
        assert original["MSSubClass"].tolist() == [60]


class TestEngineerFeatures:
    def test_computes_total_sf_and_house_age(self):
        df = pd.DataFrame(
            {
                "TotalBsmtSF": [800],
                "1stFlrSF": [900],
                "2ndFlrSF": [200],
                "YearBuilt": [2000],
                "YrSold": [2008],
            }
        )
        result = engineer_features(df)
        assert result["TotalSF"].iloc[0] == 1900
        assert result["HouseAge"].iloc[0] == 8

    def test_skips_total_sf_when_source_columns_missing(self):
        df = pd.DataFrame({"YearBuilt": [2000], "YrSold": [2008]})
        result = engineer_features(df)
        assert "TotalSF" not in result.columns
        assert "HouseAge" in result.columns

    def test_skips_house_age_when_source_columns_missing(self):
        df = pd.DataFrame({"TotalBsmtSF": [800], "1stFlrSF": [900], "2ndFlrSF": [200]})
        result = engineer_features(df)
        assert "HouseAge" not in result.columns
        assert "TotalSF" in result.columns


class TestPrepareData:
    def test_train_time_succeeds_with_target(self):
        df = make_valid_df(n_rows=2)
        result = prepare_data(df)
        assert len(result) == 2
        assert result["TotalSF"].iloc[0] == 800 + 900 + 200
        assert result["HouseAge"].iloc[0] == 2008 - 2000
        assert pd.api.types.is_string_dtype(result["MSSubClass"])

    def test_predict_time_succeeds_without_target(self):
        df = make_valid_df(n_rows=1).drop(columns=[TARGET_COLUMN])
        result = prepare_data(df, drop_outliers=False, require_target=False)
        assert len(result) == 1

    def test_prepare_data_raises_on_missing_column_before_cleaning(self):
        df = make_valid_df().drop(columns=["Neighborhood"])
        with pytest.raises(DataValidationError):
            prepare_data(df)

    def test_prepare_data_drops_known_outlier_row(self):
        df = make_valid_df(n_rows=1)
        df.loc[0, "Id"] = OUTLIER_IDS[0]
        result = prepare_data(df)
        assert len(result) == 0
