import os
import pytest
from unittest.mock import patch

from lumina.core.config import (
    CHATS_DIR,
    IMAGE_CACHE_DIR,
    GOOGLE_API_KEY,
    GEMMA_MODEL,
    SEARCH_TIMEOUT_SECONDS,
    CHAT_IMAGE_TIMEOUT_SECONDS,
    PREFLIGHT_TIMEOUT_SECONDS,
)

from lumina.utils.network import safe_error


def test_chats_dir_configured():
    assert CHATS_DIR == "chats"


def test_image_cache_dir_configured():
    assert IMAGE_CACHE_DIR == "image_cache"


def test_gemma_model_default():
    assert GEMMA_MODEL == "gemma-4-31b-it"


def test_search_timeout_default():
    assert SEARCH_TIMEOUT_SECONDS == 25


def test_preflight_timeout_default():
    assert PREFLIGHT_TIMEOUT_SECONDS == 12


def test_chat_image_timeout_default():
    assert CHAT_IMAGE_TIMEOUT_SECONDS == 75


def test_config_no_crash():
    assert isinstance(CHATS_DIR, str)
    assert isinstance(IMAGE_CACHE_DIR, str)
    assert isinstance(GEMMA_MODEL, str)
    assert isinstance(SEARCH_TIMEOUT_SECONDS, int)
