import streamlit as st


def spacer(px: int) -> None:
    st.html(f"<div class='spacer-{px}'></div>")


def badge(text: str, *, large: bool = False) -> None:
    size_class = " status-badge-lg" if large else ""
    st.html(f"<div class='status-badge{size_class}'><span class='dot'></span>{text}</div>")


def note(text: str) -> None:
    st.html(f"<div class='note'>{text}</div>")


def crumb(label: str) -> None:
    st.html(f"<div class='crumb'>PROPERTEA-AI / {label.upper()}</div>")


def sidebar_brand() -> None:
    st.html("<div class='sidebar-brand'>\U0001F3E0 propertea-ai</div>")
