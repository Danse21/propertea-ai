import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from matplotlib.patches import Patch

import state
from eda_service import CORR_LEGEND, MISSINGNESS_COLUMNS, NA_IS_CATEGORY
from theme import COLORS, HEATMAP_CMAP
from ui import page_header, spacer


def render_eda():
    page_header(
        "Explore data",
        "Exploratory data analysis",
        "The target distribution, missing data, and which features move price the most \u2014 before training.",
    )
    state.active_dataset_bar()

    df = state.require_ames_dataset()
    if df is None:
        return

    with st.container(border=True):
        st.subheader("Target distribution")
        log_price = np.log1p(df["SalePrice"])
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.2))
        axes[0].hist(df["SalePrice"] / 1000, bins=40, color=COLORS["accent"])
        axes[0].set_title(f"SalePrice (skew {df['SalePrice'].skew():.2f})", fontsize=10)
        axes[0].set_xlabel("SalePrice ($1000x)")
        axes[0].set_ylabel("Count")
        axes[1].hist(log_price, bins=40, color=COLORS["accent"])
        axes[1].set_title(f"log1p(SalePrice) (skew {log_price.skew():.2f})", fontsize=10)
        axes[1].set_xlabel("log1p(SalePrice)")
        axes[1].set_ylabel("Count")
        for ax in axes:
            ax.spines[["top", "right"]].set_visible(False)
        st.pyplot(fig)
        plt.close(fig)

    with st.container(border=True):
        st.subheader("Missingness per column")
        st.caption("Red = genuinely missing · Blue = NA means \"none\" (not a gap to fill)")
        miss = state.cached_missingness_summary(df)
        cols_to_show = [c for c in MISSINGNESS_COLUMNS if c in miss.index] or miss.index[:10]
        miss_subset = miss.loc[cols_to_show].sort_values()
        if len(miss_subset):
            bar_colors = [
                COLORS["accent"] if col in NA_IS_CATEGORY else COLORS["danger"]
                for col in miss_subset.index
            ]
            fig2, ax2 = plt.subplots(figsize=(9, 3.2))
            ax2.barh(miss_subset.index, miss_subset.values, color=bar_colors)
            ax2.set_xlabel("% missing")
            ax2.spines[["top", "right"]].set_visible(False)
            legend_handles = [
                Patch(facecolor=COLORS["danger"], label="Genuinely missing"),
                Patch(facecolor=COLORS["accent"], label="NA means \"none\""),
            ]
            ax2.legend(handles=legend_handles, loc="lower right", fontsize=8, frameon=False)
            st.pyplot(fig2)
            plt.close(fig2)
        else:
            st.caption("No missing values in this dataset.")

    with st.container(border=True):
        st.subheader("Correlation heatmap — top SalePrice movers")
        corr = state.cached_top_mover_correlations(df)
        fig3, ax3 = plt.subplots(figsize=(5, 4))
        im = ax3.imshow(corr, cmap=HEATMAP_CMAP, vmin=0, vmax=1)
        ax3.set_xticks(range(len(corr.columns)))
        ax3.set_xticklabels(
            [abbr for abbr, raw, _ in CORR_LEGEND if raw in corr.columns], rotation=45, ha="right", fontsize=8
        )
        ax3.set_yticks(range(len(corr.columns)))
        ax3.set_yticklabels([abbr for abbr, raw, _ in CORR_LEGEND if raw in corr.columns], fontsize=8)
        for i in range(len(corr.columns)):
            for j in range(len(corr.columns)):
                ax3.text(
                    j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7,
                    color=COLORS["white"] if corr.iloc[i, j] > 0.6 else COLORS["ink"],
                )
        fig3.colorbar(im, ax=ax3, fraction=0.046, pad=0.04)
        st.pyplot(fig3, width="content")
        plt.close(fig3)

        legend_cols = st.columns(2)
        for idx, (abbr, raw, desc) in enumerate(CORR_LEGEND):
            with legend_cols[idx % 2]:
                st.markdown(
                    f"<div class='legend-item'><b>{abbr}</b> "
                    f"<span class='legend-raw'>({raw})</span> = {desc}</div>",
                    unsafe_allow_html=True,
                )

    spacer(24)
    if st.button("Continue to Train model \u2192", type="primary"):
        st.session_state.page = "Train"
        st.rerun()
