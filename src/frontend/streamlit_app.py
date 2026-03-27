from __future__ import annotations

from collections.abc import Sequence
from typing import cast

import streamlit as st

from pages import chat_page, sources_page, studio_page
from services.api_client import ApiError
from state.session_state import clear_auth, get_client, init_state, set_auth

st.set_page_config(page_title="NotebookLM Clone", layout="wide")
init_state()
client = get_client()


def _render_api_error(exc: ApiError, *, show_message: bool = True) -> None:
    if show_message:
        st.sidebar.error(str(exc))
    details = exc.details
    if isinstance(details, list):
        for item in details:
            field = item.get("field") if isinstance(item, dict) else None
            message = item.get("message") if isinstance(item, dict) else None
            if isinstance(field, str) and isinstance(message, str):
                st.sidebar.caption(f"{field}: {message}")
    elif isinstance(details, dict):
        for key, value in details.items():
            st.sidebar.caption(f"{key}: {value}")


def _validate_auth_fields(email: str, password: str) -> str | None:
    clean_email = email.strip()
    if not clean_email:
        return "Email is required."
    if "@" not in clean_email or "." not in clean_email.split("@")[-1]:
        return "Enter a valid email address."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    return None


def _render_dependency_panel() -> None:
    st.sidebar.markdown("### Dependencies")
    try:
        dependencies = client.dependency_health()
    except ApiError as exc:
        st.sidebar.error(f"Dependency check failed: {exc}")
        return
    for name in ("postgres", "redis", "milvus", "zep", "ollama", "provider_gate"):
        row = dependencies.get(name)
        if not isinstance(row, dict):
            continue
        status = str(row.get("status", "unknown"))
        detail = str(row.get("detail", ""))
        icon = _status_icon(status)
        st.sidebar.caption(f"{icon} {name}: {status}")
        if detail:
            st.sidebar.caption(f"{name} detail: {detail}")


def _status_icon(status: str) -> str:
    if status == "up":
        return "OK"
    if status == "degraded":
        return "WARN"
    if status == "skipped":
        return "SKIP"
    return "DOWN"


def _apply_query_token_auth() -> None:
    oauth_code = _query_param_value("oauth_code")
    if not isinstance(oauth_code, str) or not oauth_code:
        return
    try:
        result = client.google_exchange(oauth_code=oauth_code)
        set_auth(
            user_email=result["user"]["email"],
            user_id=result["user"]["id"],
            access_token=result["access_token"],
        )
    except ApiError as exc:
        st.sidebar.error(f"Google sign-in exchange failed: {exc}")
        if exc.details:
            _render_api_error(exc, show_message=False)
    finally:
        st.query_params.clear()


def _query_param_value(key: str) -> str | None:
    value = cast(object, st.query_params.get(key))
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        if not value:
            return None
        first = value[0]
        return first if isinstance(first, str) else None
    if isinstance(value, Sequence):
        first = next(iter(value), None)
        return first if isinstance(first, str) else None
    return None


def _render_auth_sidebar() -> bool:
    st.sidebar.title("Authentication")
    _render_dependency_panel()
    if st.session_state.get("access_token"):
        st.sidebar.success(f"Logged in as {st.session_state.get('user_email')}")
        if st.sidebar.button("Logout"):
            try:
                client.logout()
            except ApiError:
                pass
            clear_auth()
            st.rerun()
        return True

    with st.sidebar.form("login_form"):
        st.subheader("Login")
        login_email = st.text_input("Email")
        login_password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            validation_error = _validate_auth_fields(login_email, login_password)
            if validation_error is not None:
                st.sidebar.error(validation_error)
                return False
            try:
                result = client.login(email=login_email, password=login_password)
                set_auth(
                    user_email=result["user"]["email"],
                    user_id=result["user"]["id"],
                    access_token=result["access_token"],
                )
                st.rerun()
            except ApiError as exc:
                _render_api_error(exc)

    with st.sidebar.form("register_form"):
        st.subheader("Register")
        reg_email = st.text_input("New Email")
        reg_password = st.text_input("New Password", type="password")
        if st.form_submit_button("Register"):
            validation_error = _validate_auth_fields(reg_email, reg_password)
            if validation_error is not None:
                st.sidebar.error(validation_error)
                return False
            try:
                result = client.register(email=reg_email, password=reg_password)
                set_auth(
                    user_email=result["user"]["email"],
                    user_id=result["user"]["id"],
                    access_token=result["access_token"],
                )
                st.rerun()
            except ApiError as exc:
                _render_api_error(exc)

    if st.sidebar.button("Start Google OAuth"):
        try:
            oauth = client.google_start()
            st.sidebar.link_button("Continue with Google", url=oauth["auth_url"])
        except ApiError as exc:
            _render_api_error(exc)

    return False


_apply_query_token_auth()
st.title("NotebookLM Clone")
logged_in = _render_auth_sidebar()
if not logged_in:
    st.info("Login to start ingesting sources and chatting.")
    st.stop()

sources_tab, chat_tab, studio_tab = st.tabs(["Sources", "Chat", "Studio"])
with sources_tab:
    sources_page.render(client)
with chat_tab:
    chat_page.render(client)
with studio_tab:
    studio_page.render(client)
