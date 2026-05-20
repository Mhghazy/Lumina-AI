import random
import string
import pytest
import urllib.parse

from lumina.search.scraper import _normalize_onion_url, _extract_onion_urls, _is_onion_url


@pytest.mark.fuzz
class TestFuzzOnionUrls:
    def test_random_onion_candidates(self):
        for _ in range(100):
            length = random.choice([16, 56])
            host = "".join(random.choices("abcdefghijklmnopqrstuvwxyz234567", k=length))
            url = f"http://{host}.onion"
            result = _normalize_onion_url(url)
            assert isinstance(result, str)

    def test_random_malformed_urls(self):
        for _ in range(100):
            bits = random.choices(
                ["http://", "https://", "ftp://", "", " ", "abc", "://", "///"],
                k=random.randint(1, 5),
            )
            raw = "".join(bits)
            result = _normalize_onion_url(raw)
            assert isinstance(result, str)

    def test_random_unicode_in_urls(self):
        for _ in range(50):
            junk = "".join(random.choices(string.printable + "áéíóúñüøÆØßÞ", k=random.randint(1, 20)))
            try:
                result = _normalize_onion_url(junk)
                assert isinstance(result, str)
            except ValueError:
                pass

    def test_extract_from_random_text(self):
        for _ in range(50):
            text = "".join(random.choices(string.printable, k=random.randint(10, 200)))
            result = _extract_onion_urls(text)
            assert isinstance(result, list)

    def test_onion_url_in_long_text(self):
        for _ in range(50):
            prefix = "A" * random.randint(0, 1000)
            host = "".join(random.choices("abcdefghijklmnopqrstuvwxyz234567", k=16))
            suffix = "B" * random.randint(0, 1000)
            text = f"{prefix}http://{host}.onion{suffix}"
            result = _extract_onion_urls(text)
            assert isinstance(result, list)
