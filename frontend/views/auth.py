import streamlit as st

import api_client


def _sign_in(call):
    try:
        result = call()
    except api_client.BackendUnreachableError as e:
        st.error(f"Can't reach the backend: {e}")
    except api_client.AuthError as e:
        st.error(str(e))
    except api_client.ApiError as e:
        st.error(f"Couldn't sign you in: {e}")
    else:
        st.session_state.token = result["token"]
        st.session_state.username = result["username"]
        st.rerun()


def render_auth():
    _left_pad, main_col, _right_pad = st.columns([1, 2, 1])
    with main_col:
        st.html("<div class='auth-brand'>\U0001F3E0 propertea-ai</div>")
        st.html("<p class='subtitle'>Sign in to reach your datasets and trained models</p>")

        login_tab, register_tab = st.tabs(["Log in", "Create account"])

        with login_tab:
            with st.form("login"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Log in", type="primary", use_container_width=True):
                    if not username or not password:
                        st.error("Enter a username and a password.")
                    else:
                        _sign_in(lambda: api_client.login(username, password))

        with register_tab:
            with st.form("register"):
                new_username = st.text_input("Username", help="At least 3 characters")
                new_password = st.text_input("Password", type="password", help="At least 8 characters")
                if st.form_submit_button("Create account", type="primary", use_container_width=True):
                    if len(new_username) < 3:
                        st.error("Username must be at least 3 characters.")
                    elif len(new_password) < 8:
                        st.error("Password must be at least 8 characters.")
                    else:
                        _sign_in(lambda: api_client.register(new_username, new_password))
