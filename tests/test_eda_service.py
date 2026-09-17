import pandas as pd

from frontend.eda_service import missingness_summary, top_mover_correlations


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
