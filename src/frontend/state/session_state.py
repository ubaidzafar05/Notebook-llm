from __future__ import annotations

from typing import cast

import streamlit as st

from services.api_client import ApiClient


STATE_KEYS = {
    "api_client": "api_client",
    "user_email": "user_email",
    "user_id": "user_id",
    "access_token": "access_token",
    "selected_session_id": "selected_session_id",
    "latest_job_id": "latest_job_id",
    "latest_podcast_id": "latest_podcast_id",
}


def init_state() -> None:
    if STATE_KEYS["api_client"] not in st.session_state:
        st.session_state[STATE_KEYS["api_client"]] = ApiClient()
    for key in ["user_email", "user_id", "access_token", "selected_session_id", "latest_job_id", "latest_podcast_id"]:
        st.session_state.setdefault(STATE_KEYS[key], None)


def get_client() -> ApiClient:
    return cast(ApiClient, st.session_state[STATE_KEYS["api_client"]])


def set_auth(user_email: str, user_id: str, access_token: str) -> None:
    st.session_state[STATE_KEYS["user_email"]] = user_email
    st.session_state[STATE_KEYS["user_id"]] = user_id
    st.session_state[STATE_KEYS["access_token"]] = access_token
    get_client().set_access_token(access_token)


def clear_auth() -> None:
    set_auth(user_email="", user_id="", access_token="")
