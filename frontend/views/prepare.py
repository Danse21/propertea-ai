import io

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

import api_client
import prep_ops
import state
from eda_service import HEATMAP, PLOT_KINDS, DataValidationError, build_plot, missingness_summary
from state import PREP_WIDGET_KEYS
from ui import badge, context_bar, hint, note, page_header, spacer


def _prep_frame() -> pd.DataFrame | None:
    df = state.require_dataset()
    if df is None:
        return None
    if st.session_state.prep_df is None or st.session_state.prep_source != st.session_state.dataset_id:
        st.session_state.prep_df = df.copy()
        st.session_state.prep_source = st.session_state.dataset_id
        st.session_state.prep_history = []
        st.session_state.prep_saved_at = 0
        st.session_state.pop("prep_shown", None)
    return st.session_state.prep_df


def _resync_column_widgets(columns: list[str]) -> None:
    for key in PREP_WIDGET_KEYS:
        st.session_state.pop(key, None)
    st.session_state.prep_shown = columns
    st.session_state.prep_order = columns


PREP_HISTORY_LIMIT = 20


def _apply_op(op, frame: pd.DataFrame, *args, label: str) -> None:
    try:
        result = op(frame, *args)
    except ValueError as e:
        st.error(str(e))
        return
    st.session_state.prep_history = (
        st.session_state.prep_history + [(label, frame)]
    )[-PREP_HISTORY_LIMIT:]
    st.session_state.prep_df = result
    if list(result.columns) != list(frame.columns):
        _resync_column_widgets(list(result.columns))
    st.rerun()


def _undo_op() -> None:
    label, frame = st.session_state.prep_history[-1]
    st.session_state.prep_history = st.session_state.prep_history[:-1]
    current = st.session_state.prep_df
    st.session_state.prep_df = frame
    if current is None or list(current.columns) != list(frame.columns):
        _resync_column_widgets(list(frame.columns))
    st.rerun()


def _prep_unsaved() -> bool:
    return len(st.session_state.prep_history) != st.session_state.prep_saved_at


def _reset_prep_frame() -> None:
    st.session_state.prep_df = None
    st.session_state.prep_history = []
    st.session_state.prep_saved_at = 0
    for key in PREP_WIDGET_KEYS:
        st.session_state.pop(key, None)
    st.rerun()


def _column_selector(all_columns: list[str]) -> list[str]:
    if len(all_columns) > 15:
        st.caption("Removing a column here only hides it; the data is untouched until you delete it.")
    return list(
        st.pills(
            "Columns in view",
            all_columns,
            selection_mode="multi",
            default=all_columns,
            key="prep_shown",
        )
    )


def render_prepare():
    page_header(
        "Prepare data",
        "Prepare data",
        "Clean the open dataset, then save the result as a new one.",
    )

    prep = _prep_frame()
    if prep is None:
        return

    all_columns = list(prep.columns)
    unsaved = _prep_unsaved()
    bar_col, save_col = st.columns([5, 1])
    with bar_col:
        changes = len(st.session_state.prep_history)
        state = f"{changes} change{'s' if changes != 1 else ''} not saved yet" if unsaved else "no unsaved changes"
        context_bar(
            st.session_state.dataset_name,
            f"{len(prep):,} rows \u00b7 {len(all_columns)} columns \u00b7 {state}",
            stale=unsaved,
        )
    with save_col:
        spacer(24)
        st.html("<a class='jump-link' href='#save'>Go to save \u2193</a>")

    if st.session_state.prep_saved_as:
        saved = st.session_state.prep_saved_as
        badge(
            f"Saved \u201c{saved['name']}\u201d \u2014 {saved['n_rows']:,} rows \u00d7 {saved['n_columns']} columns. "
            f"\u201c{st.session_state.dataset_name}\u201d stays open here; find the new one on Datasets."
        )

    with st.container(border=True):
        st.subheader("Data")
        preview_tab, info_tab, describe_tab, missing_tab = st.tabs(
            ["Preview", "Column information", "Summary statistics", "Missing values"]
        )
        shown = st.session_state.get("prep_shown") or all_columns
        shown = [c for c in shown if c in all_columns] or all_columns
        with preview_tab:
            rows = st.slider("Rows to show", 5, 100, 25, key="prep_head_n")
            st.dataframe(prep[shown].head(rows), use_container_width=True, height=360)
            st.caption(f"{len(prep):,} rows total \u00b7 showing {min(rows, len(prep))} of them, {len(shown)} of {len(all_columns)} columns")
        with info_tab:
            buffer = io.StringIO()
            prep[shown].info(buf=buffer)
            st.code(buffer.getvalue(), language="text")
        with describe_tab:
            numeric_only = st.toggle("Numeric columns only", value=True, key="prep_desc_numeric")
            described = prep[shown].describe() if numeric_only else prep[shown].describe(include="all")
            st.dataframe(described.T, use_container_width=True)
        with missing_tab:
            miss = missingness_summary(prep[shown])
            if miss.empty:
                st.caption("No missing values.")
            else:
                st.dataframe(miss.rename("% missing"), use_container_width=True)

    with st.container(border=True):
        st.subheader("Columns")
        hint("Hiding a column only changes what you see here. Deleting removes it from the data you save.")
        shown = _column_selector(all_columns)
        hidden = [c for c in all_columns if c not in shown]

        drop_col, undo_col, reset_col = st.columns(3)
        with drop_col:
            if st.button(
                f"Delete {len(hidden)} hidden column{'s' if len(hidden) != 1 else ''} from the data",
                disabled=not hidden,
                use_container_width=True,
            ):
                _apply_op(
                    lambda frame, cols: frame.drop(columns=cols), prep, hidden,
                    label=f"deleted {len(hidden)} column{'s' if len(hidden) != 1 else ''}",
                )
        with undo_col:
            history = st.session_state.prep_history
            undo_label = f"Undo \u2014 {history[-1][0]}" if history else "Nothing to undo"
            if st.button(undo_label, disabled=not history, use_container_width=True):
                _undo_op()
        with reset_col:
            if st.session_state.get("prep_confirm_reset"):
                if st.button("Confirm reset \u2014 lose changes", key="prep-reset-yes", use_container_width=True):
                    st.session_state.prep_confirm_reset = False
                    _reset_prep_frame()
                if st.button("Cancel", key="prep-reset-no", type="tertiary", use_container_width=True):
                    st.session_state.prep_confirm_reset = False
                    st.rerun()
            elif st.button("Reset to uploaded data", use_container_width=True):
                if unsaved:
                    st.session_state.prep_confirm_reset = True
                    st.rerun()
                else:
                    _reset_prep_frame()

        if not shown:
            note("Show at least one column to inspect or plot it.")
            return

    with st.container(border=True):
        st.subheader("Transform")
        impute_tab, cast_tab, rows_tab, columns_tab = st.tabs(
            ["Fill missing", "Change type", "Rows", "Rename & order"]
        )

        with impute_tab:
            col, strategy, value = st.columns([2, 2, 2])
            with col:
                impute_column = st.selectbox("Column", all_columns, key="prep_impute_col")
            with strategy:
                impute_strategy = st.selectbox("Fill with", prep_ops.FILL_STRATEGIES, key="prep_impute_how")
            with value:
                impute_constant = st.text_input(
                    "Value", key="prep_impute_value", disabled=impute_strategy != "constant"
                )
            st.caption(f"{prep[impute_column].isna().sum():,} missing values in {impute_column}")
            if st.button("Apply fill", key="prep_impute_go"):
                _apply_op(prep_ops.impute, prep, impute_column, impute_strategy, impute_constant, label=f"filled {impute_column}")

        with cast_tab:
            col, dtype = st.columns(2)
            with col:
                cast_column = st.selectbox("Column", all_columns, key="prep_cast_col")
            with dtype:
                cast_dtype = st.selectbox("Cast to", list(prep_ops.CASTS), key="prep_cast_dtype")
            st.caption(f"{cast_column} is currently {prep[cast_column].dtype}")
            if st.button("Apply cast", key="prep_cast_go"):
                _apply_op(prep_ops.cast, prep, cast_column, cast_dtype, label=f"cast {cast_column} to {cast_dtype}")

        with rows_tab:
            expression = st.text_input(
                "Keep rows where",
                key="prep_filter_expr",
                placeholder="SalePrice > 100000 and OverallQual >= 5",
                help="A pandas query expression. Wrap odd column names in backticks.",
            )
            if st.button("Apply filter", key="prep_filter_go", disabled=not expression.strip()):
                _apply_op(prep_ops.filter_rows, prep, expression, label="filtered rows")

            threshold = st.slider("Drop rows missing more than (% of columns)", 0, 100, 50, key="prep_sparse_pct")
            sparse_col, dedupe_col = st.columns(2)
            with sparse_col:
                if st.button("Drop sparse rows", key="prep_sparse_go", use_container_width=True):
                    _apply_op(prep_ops.drop_sparse_rows, prep, float(threshold), label="dropped sparse rows")
            with dedupe_col:
                duplicates = int(prep.duplicated().sum())
                if st.button(
                    f"Drop {duplicates:,} duplicate rows",
                    key="prep_dedupe_go",
                    disabled=not duplicates,
                    use_container_width=True,
                ):
                    _apply_op(prep_ops.deduplicate, prep, label="dropped duplicate rows")

        with columns_tab:
            edited = st.data_editor(
                pd.DataFrame({"column": all_columns, "rename to": all_columns}),
                hide_index=True,
                disabled=["column"],
                use_container_width=True,
                key="prep_rename_editor",
            )
            if st.button("Apply renames", key="prep_rename_go"):
                _apply_op(prep_ops.rename_columns, prep, dict(zip(edited["column"], edited["rename to"])), label="renamed columns")

            order = list(
                st.multiselect(
                    "Column order",
                    all_columns,
                    default=all_columns,
                    key="prep_order",
                    help="Clear it and re-pick the columns in the order you want.",
                )
            )
            if set(order) != set(all_columns):
                st.caption("Re-pick every column to set an order \u2014 removing one here won't delete it. Use Columns above for that.")
            if st.button(
                "Apply order",
                key="prep_order_go",
                disabled=order == all_columns or set(order) != set(all_columns),
            ):
                _apply_op(prep_ops.reorder_columns, prep, order, label="reordered columns")

    with st.container(border=True):
        st.subheader("Plot")
        kind = st.selectbox("Plot type", PLOT_KINDS, key="prep_plot_kind")
        x = y = hue = None
        if kind != HEATMAP:
            none_label = "\u2014"
            options = [none_label, *shown]
            x_col, y_col, hue_col = st.columns(3)
            with x_col:
                x = st.selectbox("X", options, key="prep_plot_x")
            with y_col:
                y = st.selectbox("Y", options, key="prep_plot_y")
            with hue_col:
                hue = st.selectbox("Colour by", options, key="prep_plot_hue")
            x, y, hue = (None if v == none_label else v for v in (x, y, hue))

        if kind == HEATMAP or x or y:
            try:
                fig = build_plot(prep, kind, x, y, hue)
            except (DataValidationError, ValueError, TypeError) as e:
                st.error(f"Couldn't draw that plot: {e}")
            else:
                st.pyplot(fig)
                plt.close(fig)
        else:
            hint("Pick an X or Y column to draw a plot.")

    with st.container(border=True):
        st.subheader("Save")
        hint("Saving never overwrites the open dataset \u2014 it creates a new one.")
        no_target = "\u2014 none yet \u2014"
        target_options = [no_target, *all_columns]
        default_target = st.session_state.target_column if st.session_state.target_column in all_columns else no_target
        name_col, target_col, button_col = st.columns([2, 2, 1])
        with name_col:
            new_name = st.text_input("Save as", value=f"{st.session_state.dataset_name}-prepared")
        with target_col:
            target = st.selectbox(
                "Target column",
                target_options,
                index=target_options.index(default_target),
                help="The column you want to predict. Leave it unset if you haven't decided.",
            )
            target = None if target == no_target else target
        with button_col:
            spacer(35)
            save_clicked = st.button("Save dataset", type="primary", use_container_width=True)

        if save_clicked:
            if not new_name.strip():
                st.error("Give the dataset a name.")
            else:
                try:
                    saved = api_client.upload_dataset(
                        st.session_state.token,
                        prep.to_csv(index=False).encode(),
                        new_name.strip(),
                        target,
                    )
                except api_client.BackendUnreachableError as e:
                    st.error(f"Can't reach the backend: {e}")
                except api_client.ApiError as e:
                    st.error(f"Couldn't save that dataset: {e}")
                else:
                    st.session_state.prep_saved_at = len(st.session_state.prep_history)
                    st.session_state.prep_saved_as = {
                        "id": saved["id"],
                        "name": new_name.strip(),
                        "n_rows": saved["n_rows"],
                        "n_columns": len(prep.columns),
                    }
                    st.rerun()
