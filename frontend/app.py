import streamlit as st

import state
from styles import CSS
from ui import sidebar_brand
from views import auth, datasets, eda, predict, prepare, train, upload

st.set_page_config(page_title="propertea-ai", page_icon="\U0001F3E0", layout="wide")
st.html(CSS)
state.init_session()

ROUTES = {
    "Datasets": datasets.render_datasets,
    "Upload": upload.render_upload,
    "Explore": eda.render_eda,
    "Train": train.render_train,
    "Predict": predict.render_predict,
    "Prepare": prepare.render_prepare,
}
NAV = ["Datasets", "Explore", "Train", "Predict"]
SUBPAGES = {"Upload": "Datasets", "Prepare": "Datasets"}


def sidebar():
    with st.sidebar:
        sidebar_brand()
        current = st.session_state.page
        for page in NAV:
            active = current == page or SUBPAGES.get(current) == page
            if st.button(
                page,
                key=f"nav-{page}",
                type="primary" if active else "tertiary",
                use_container_width=True,
            ):
                st.session_state.page = page
                st.rerun()
            if SUBPAGES.get(current) == page:
                st.html(f"<div class='nav-sub'>\u21b3 {current}</div>")

        st.html(
            f"<div class='session-badge'><span class='lbl'>SIGNED IN</span>"
            f"{st.session_state.username}</div>"
        )
        if st.button("Log out", key="nav-logout", type="tertiary", use_container_width=True):
            state.sign_out()


if st.session_state.token is None:
    auth.render_auth()
else:
    sidebar()
    ROUTES[st.session_state.page]()
