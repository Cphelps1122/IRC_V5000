import hmac
import streamlit as st
import config


def _configured_password() -> str:
    try:
        secret_pw = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        secret_pw = ""
    return secret_pw or getattr(config, "APP_PASSWORD", "")


def require_auth():
    """Stop the page unless the user has entered the dashboard password."""
    password = _configured_password()
    if not password:
        st.error("Dashboard password is not configured. Set APP_PASSWORD in config.py or Streamlit Secrets.")
        st.stop()

    if st.session_state.get("authenticated") is True:
        return

    st.markdown(
        """
        <style>
        .stApp {background: radial-gradient(circle at top, rgba(56,189,248,.18), transparent 35rem), #07111F; color: #EAF2FF;}
        .block-container {max-width: 480px; padding-top: 14vh;}
        [data-testid="stSidebar"] {display:none;}
        h1, p, label {color:#EAF2FF !important;}
        .login-card {background:#0F1F35; border:1px solid rgba(148,163,184,.22); padding:28px; border-radius:22px; box-shadow:0 18px 42px rgba(0,0,0,.30);}
        .muted {color:#9FB4CF;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.title("Utility Operations Dashboard")
    st.caption("Enter the dashboard password to continue.")
    entered = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Password")
    submitted = st.button("Enter dashboard", use_container_width=True)
    if submitted:
        if hmac.compare_digest(entered, password):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


def logout_button():
    if st.sidebar.button("Log out"):
        st.session_state.authenticated = False
        st.rerun()
