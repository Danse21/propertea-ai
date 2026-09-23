import pandas as pd
import pytest

from frontend.prep_ops import (
    cast,
    deduplicate,
    drop_sparse_rows,
    filter_rows,
    impute,
    rename_columns,
    reorder_columns,
)


@pytest.fixture
def frame():
    return pd.DataFrame(
        {
            "price": [100.0, None, 300.0, 300.0],
            "kind": ["a", "b", None, "b"],
            "year": ["1990", "1991", "1992", "1993"],
        }
    )


class TestImpute:
    def test_mean_fills_missing_numbers(self, frame):
        result = impute(frame, "price", "mean")
        assert result["price"].tolist() == [100.0, 233.0 + 1 / 3, 300.0, 300.0]

    def test_median_fills_missing_numbers(self, frame):
        assert impute(frame, "price", "median")["price"][1] == 300.0

    def test_mode_fills_categories(self, frame):
        assert impute(frame, "kind", "mode")["kind"][2] == "b"

    def test_constant_is_coerced_for_numeric_columns(self, frame):
        assert impute(frame, "price", "constant", "0")["price"][1] == 0.0

    def test_drop_rows_removes_missing(self, frame):
        assert len(impute(frame, "price", "drop rows")) == 3

    def test_mean_rejects_non_numeric_column(self, frame):
        with pytest.raises(ValueError, match="numeric"):
            impute(frame, "kind", "mean")

    def test_constant_requires_a_value(self, frame):
        with pytest.raises(ValueError, match="fill value"):
            impute(frame, "kind", "constant", "")

    def test_unknown_column_is_rejected(self, frame):
        with pytest.raises(ValueError, match="No column"):
            impute(frame, "nope", "mean")

    def test_original_frame_is_untouched(self, frame):
        impute(frame, "price", "mean")
        assert frame["price"].isna().sum() == 1


class TestCast:
    def test_numeric_cast(self, frame):
        assert pd.api.types.is_numeric_dtype(cast(frame, "year", "numeric")["year"])

    def test_integer_cast_keeps_missing_values(self, frame):
        result = cast(frame, "price", "integer")
        assert str(result["price"].dtype) == "Int64"
        assert result["price"].isna().sum() == 1

    def test_category_cast(self, frame):
        assert str(cast(frame, "kind", "category")["kind"].dtype) == "category"

    def test_datetime_cast(self):
        df = pd.DataFrame({"d": ["2024-01-01", "2024-02-01"]})
        assert pd.api.types.is_datetime64_any_dtype(cast(df, "d", "datetime")["d"])

    def test_bad_cast_reports_the_column(self, frame):
        with pytest.raises(ValueError, match="kind"):
            cast(frame, "kind", "numeric")

    def test_unknown_dtype_is_rejected(self, frame):
        with pytest.raises(ValueError, match="Unknown dtype"):
            cast(frame, "year", "complex")


class TestRowOps:
    def test_filter_rows_applies_query(self, frame):
        assert filter_rows(frame, "price > 150")["price"].tolist() == [300.0, 300.0]

    def test_empty_expression_is_a_no_op(self, frame):
        assert len(filter_rows(frame, "   ")) == len(frame)

    def test_bad_expression_is_rejected(self, frame):
        with pytest.raises(ValueError, match="Can't apply"):
            filter_rows(frame, "price >")

    def test_drop_sparse_rows_uses_a_percentage(self, frame):
        assert len(drop_sparse_rows(frame, 0)) == 2
        assert len(drop_sparse_rows(frame, 100)) == 4

    def test_deduplicate(self):
        df = pd.DataFrame({"a": [1, 1, 2]})
        assert deduplicate(df)["a"].tolist() == [1, 2]


class TestColumnOps:
    def test_rename(self, frame):
        assert list(rename_columns(frame, {"price": "SalePrice"}).columns)[0] == "SalePrice"

    def test_rename_rejects_duplicates(self, frame):
        with pytest.raises(ValueError, match="Duplicate"):
            rename_columns(frame, {"price": "kind"})

    def test_rename_rejects_empty_names(self, frame):
        with pytest.raises(ValueError, match="empty"):
            rename_columns(frame, {"price": "  "})

    def test_reorder(self, frame):
        assert list(reorder_columns(frame, ["year", "kind", "price"]).columns) == [
            "year", "kind", "price",
        ]

    def test_reorder_requires_every_column(self, frame):
        with pytest.raises(ValueError, match="missing"):
            reorder_columns(frame, ["year"])
