import pandas as pd

FILL_STRATEGIES = ("mean", "median", "mode", "constant", "drop rows")

CASTS = {
    "numeric": lambda s: pd.to_numeric(s),
    "integer": lambda s: pd.to_numeric(s).astype("Int64"),
    "string": lambda s: s.astype("string"),
    "category": lambda s: s.astype("category"),
    "datetime": lambda s: pd.to_datetime(s),
    "boolean": lambda s: s.astype("boolean"),
}


def _column(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        raise ValueError(f"No column named {column!r}")
    return df[column]


def impute(df: pd.DataFrame, column: str, strategy: str, constant: str | None = None) -> pd.DataFrame:
    series = _column(df, column)
    numeric = pd.api.types.is_numeric_dtype(series)

    if strategy == "drop rows":
        return df[series.notna()].reset_index(drop=True)

    if strategy in ("mean", "median"):
        if not numeric:
            raise ValueError(f"{strategy} needs a numeric column; {column!r} is {series.dtype}")
        value = series.mean() if strategy == "mean" else series.median()
    elif strategy == "mode":
        modes = series.mode(dropna=True)
        if modes.empty:
            raise ValueError(f"{column!r} has no values to take a mode from")
        value = modes.iloc[0]
    elif strategy == "constant":
        if constant is None or constant == "":
            raise ValueError("Give a fill value")
        value = pd.to_numeric(constant) if numeric else constant
    else:
        raise ValueError(f"Unknown fill strategy {strategy!r}")

    out = df.copy()
    out[column] = series.fillna(value)
    return out


def cast(df: pd.DataFrame, column: str, dtype: str) -> pd.DataFrame:
    series = _column(df, column)
    if dtype not in CASTS:
        raise ValueError(f"Unknown dtype {dtype!r}")
    try:
        converted = CASTS[dtype](series)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Can't cast {column!r} to {dtype}: {exc}") from exc
    out = df.copy()
    out[column] = converted
    return out


def filter_rows(df: pd.DataFrame, expression: str) -> pd.DataFrame:
    if not expression.strip():
        return df
    try:
        return df.query(expression).reset_index(drop=True)
    except Exception as exc:
        raise ValueError(f"Can't apply {expression!r}: {exc}") from exc


def drop_sparse_rows(df: pd.DataFrame, max_missing_pct: float) -> pd.DataFrame:
    if not df.columns.size:
        return df
    missing_pct = df.isna().sum(axis=1) / len(df.columns) * 100
    return df[missing_pct <= max_missing_pct].reset_index(drop=True)


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates().reset_index(drop=True)


def rename_columns(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    renamed = {old: new.strip() for old, new in mapping.items() if new.strip() != old}
    if not renamed:
        return df
    unknown = [c for c in renamed if c not in df.columns]
    if unknown:
        raise ValueError(f"No column named {unknown[0]!r}")
    if any(not new for new in renamed.values()):
        raise ValueError("Column names can't be empty")
    final = [renamed.get(c, c) for c in df.columns]
    duplicates = {c for c in final if final.count(c) > 1}
    if duplicates:
        raise ValueError(f"Duplicate column names: {sorted(duplicates)}")
    return df.rename(columns=renamed)


def reorder_columns(df: pd.DataFrame, order: list[str]) -> pd.DataFrame:
    if set(order) != set(df.columns):
        missing = sorted(set(df.columns) - set(order))
        raise ValueError(f"Order must list every column; missing {missing}")
    return df[order]
