"""Small reusable HTML-emitting helpers for the Streamlit UI."""

import streamlit as st


def spacer(px: int) -> None:
    """A vertical gap of a fixed size. `px` must match a `.spacer-N` class in styles.py."""
    st.html(f"<div class='spacer-{px}'></div>")


def badge(text: str, *, large: bool = False) -> None:
    """A pill-shaped status badge with a leading dot (e.g. a success message)."""
    size_class = " status-badge-lg" if large else ""
    st.html(f"<div class='status-badge{size_class}'><span class='dot'></span>{text}</div>")


def crumb(label: str) -> None:
    """The small breadcrumb line under the top nav on each page."""
    st.html(f"<div class='crumb'>PROPERTEA-AI / {label.upper()}</div>")


def sidebar_brand() -> None:
    """The "house" wordmark at the top of the sidebar."""
    st.html("<div class='sidebar-brand'>\U0001F3E0 propertea-ai</div>")
