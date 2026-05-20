import pytest
from hypothesis import given, strategies as st

from lumina.search.scraper import _normalize_onion_url, _extract_onion_urls


@given(url=st.text(min_size=0, max_size=100))
@pytest.mark.property
def test_normalize_onion_url_idempotent(url):
    try:
        first = _normalize_onion_url(url)
        second = _normalize_onion_url(first)
        assert first == second
    except (ValueError, UnicodeEncodeError):
        pass


@given(text=st.text(min_size=0, max_size=200))
@pytest.mark.property
def test_extract_onion_urls_returns_list(text):
    result = _extract_onion_urls(text)
    assert isinstance(result, list)
    for url in result:
        assert ".onion" in url


@given(
    prefix=st.text(min_size=0, max_size=10),
    suffix=st.text(min_size=0, max_size=10),
)
@pytest.mark.property
def test_extract_known_onion(prefix, suffix):
    text = f"{prefix}http://abcdefghijklmnop.onion{suffix}"
    result = _extract_onion_urls(text)
    assert len(result) >= 1
