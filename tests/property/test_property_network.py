import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck

from lumina.utils.network import safe_error


@given(text=st.text(min_size=0, max_size=200))
@pytest.mark.property
def test_safe_error_idempotent(text):
    first = safe_error(Exception(text))
    second = safe_error(Exception(first))
    assert first == second


@given(text=st.text(min_size=1, max_size=100))
@settings(suppress_health_check=[HealthCheck.filter_too_much])
@pytest.mark.property
def test_safe_error_no_api_key_leak(text):
    assume("?" in text)
    result = safe_error(Exception(text))
    assert isinstance(result, str)


@given(
    key_name=st.sampled_from(["key", "api_key", "token", "secret"]),
    key_value=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=["L", "N", "P"])),
)
@pytest.mark.property
def test_safe_error_redacts_known_keys(key_name, key_value):
    text = f"?{key_name}={key_value}"
    result = safe_error(Exception(text))
    if key_name in ("key", "api_key"):
        assert f"{key_name}=<redacted>" in result
    else:
        assert isinstance(result, str)
