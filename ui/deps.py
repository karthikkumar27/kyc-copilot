"""Wiring: settings from the environment and the API client for the current session."""

import os
from dataclasses import dataclass

import streamlit as st

from api_client import ApiClient, Readiness
from identity import Identity, current_identity

CLIENT_OVERRIDE_KEY = "_api_client_override"  # tests put a fake client here
SUPPORTED_AUTH_MODES = ("dev",)


@dataclass(frozen=True)
class Settings:
    api_url: str
    auth_mode: str


def settings() -> Settings:
    auth_mode = os.environ.get("KYC_UI_AUTH_MODE", "dev")
    if auth_mode not in SUPPORTED_AUTH_MODES:
        raise RuntimeError(
            f"KYC_UI_AUTH_MODE={auth_mode!r} is not supported yet. Supported: "
            f"{', '.join(SUPPORTED_AUTH_MODES)}."
        )
    api_url = os.environ.get("KYC_API_URL", "http://api:8000").rstrip("/")
    return Settings(api_url=api_url, auth_mode=auth_mode)


def get_client():
    """The client pages use. Rebuilt on every run so it always carries the current identity."""
    override = st.session_state.get(CLIENT_OVERRIDE_KEY)
    if override is not None:
        return override
    return ApiClient(settings().api_url, current_identity())


@st.cache_data(ttl=15, show_spinner=False)
def _cached_readiness(api_url: str) -> Readiness:
    return ApiClient(api_url, Identity("ui-status", "agent")).readiness()


def readiness() -> Readiness:
    override = st.session_state.get(CLIENT_OVERRIDE_KEY)
    if override is not None:
        return override.readiness()
    return _cached_readiness(settings().api_url)
