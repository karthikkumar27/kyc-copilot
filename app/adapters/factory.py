"""Builds the configured adapter instances (one per process)."""

from functools import lru_cache

from app.adapters.registry import resolve
from app.config import get_settings


@lru_cache
def get_ocr():
    s = get_settings()
    return resolve("ocr", s.ocr_provider)(s)


@lru_cache
def get_pii():
    s = get_settings()
    return resolve("pii", s.pii_provider)(s)


@lru_cache
def get_storage():
    s = get_settings()
    return resolve("storage", s.storage_provider)(s)


@lru_cache
def get_queue():
    s = get_settings()
    return resolve("queue", s.queue_provider)(s)


def validate_adapters() -> None:
    """Called at startup: a misconfigured or placeholder adapter fails the deploy, not a user."""
    get_ocr()
    get_pii()
    get_storage()
    get_queue()
