"""Optional shared-password gate for deployed instances.

Inactive by default: if no APP_PASSWORD is configured the app is open, so local
development is unaffected. Set APP_PASSWORD in .streamlit/secrets.toml (or as an
environment variable) on the deployed instance to require a password.

This is a single shared password suitable for a small internal team. For
per-user accounts, SSO, or an audit trail, put the app behind your identity
provider (see the deployment notes in README.md).
"""

import hmac
import os

import streamlit as st


def _expected_password() -> str | None:
    try:
        if "APP_PASSWORD" in st.secrets:
            return st.secrets["APP_PASSWORD"]
    except Exception:
        pass
    return os.environ.get("APP_PASSWORD")


def check_password() -> bool:
    """Return True if the visitor may see the app."""
    expected = _expected_password()
    if not expected:
        return True  # no password configured — open instance
    if st.session_state.get("authenticated"):
        return True

    st.markdown("### 📊 Wisdom Research Hub")
    st.caption("Internal research platform — please sign in.")

    with st.form("login"):
        entered = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")

    if submitted:
        if hmac.compare_digest(entered, expected):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False
