import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.preprocessing import (  # noqa: E402
    NA_IS_CATEGORY,
    TARGET_COLUMN,
    DataValidationError,
    validate_data,
)

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


def missingness_summary(df: pd.DataFrame) -> pd.Series:
    pct = (df.isna().sum() / len(df) * 100).round(1)
    return pct[pct > 0].sort_values(ascending=False)


def top_mover_correlations(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in CORR_MOVERS if c in df.columns]
    return df[cols].corr()


SEABORN_PLOTS = {
    "Histogram": sns.histplot,
    "Box plot": sns.boxplot,
    "Violin plot": sns.violinplot,
    "Scatter plot": sns.scatterplot,
    "Line plot": sns.lineplot,
    "Bar plot": sns.barplot,
    "Count plot": sns.countplot,
}

HEATMAP = "Correlation heatmap"
PLOT_KINDS = [HEATMAP, *SEABORN_PLOTS]


def build_plot(
    df: pd.DataFrame,
    kind: str,
    x: str | None = None,
    y: str | None = None,
    hue: str | None = None,
):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    if kind == HEATMAP:
        numeric = df.select_dtypes("number")
        if numeric.shape[1] < 2:
            plt.close(fig)
            raise DataValidationError("need at least two numeric columns")
        sns.heatmap(numeric.corr(), ax=ax, cmap="crest")
    elif kind in SEABORN_PLOTS:
        if kind == "Count plot" and x is not None:
            y = None
        SEABORN_PLOTS[kind](data=df, x=x, y=y, hue=hue, ax=ax)
        ax.spines[["top", "right"]].set_visible(False)
        if x and df[x].nunique() > 8 and not pd.api.types.is_numeric_dtype(df[x]):
            ax.tick_params(axis="x", rotation=45)
    else:
        plt.close(fig)
        raise DataValidationError(f"unknown plot type {kind!r}")
    fig.tight_layout()
    return fig
