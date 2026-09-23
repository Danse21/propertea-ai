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


def page_header(label: str, title: str, subtitle: str = "") -> None:
    crumb(label)
    st.title(title)
    if subtitle:
        st.html(f"<p class='subtitle'>{subtitle}</p>")


def hint(text: str) -> None:
    st.html(f"<p class='section-hint'>{text}</p>")


def context_bar(name: str, meta: str, *, stale: bool = False) -> None:
    stale_class = " is-stale" if stale else ""
    st.html(
        f"<div class='context-bar{stale_class}'>"
        f"<span><span class='ctx-label'>Dataset</span>"
        f"<span class='ctx-value'>{name}</span></span>"
        f"<span class='ctx-meta'>{meta}</span>"
        f"</div>"
    )
