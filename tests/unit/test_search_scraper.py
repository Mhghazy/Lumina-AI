import pytest
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock

from lumina.search.scraper import (
    _make_soup,
    _normalize_onion_url,
    _extract_onion_urls,
    _is_onion_url,
    _decode_bing_url,
    _deduplicate,
    format_images_for_chat,
    format_videos_for_chat,
    perform_search,
    _tor_proxy_candidates,
)


class TestMakeSoup:
    def test_parses_html(self):
        soup = _make_soup("<html><body><p>hello</p></body></html>")
        assert soup.find("p").get_text() == "hello"

    def test_none_input(self):
        soup = _make_soup(None)
        assert soup is not None

    def test_malformed_html(self):
        soup = _make_soup("<div><p>unclosed")
        assert soup.find("p") is not None


class TestNormalizeOnionUrl:
    def test_full_url(self):
        assert _normalize_onion_url("http://darknet.onion/page") == "http://darknet.onion/page"

    def test_no_protocol(self):
        assert _normalize_onion_url("darknet.onion/page").startswith("http://darknet.onion/page")

    def test_with_brackets(self):
        result = _normalize_onion_url("<darknet.onion>")
        assert result.startswith("http://darknet.onion")

    def test_non_onion(self):
        assert _normalize_onion_url("http://example.com") == ""

    def test_empty(self):
        assert _normalize_onion_url("") == ""

    def test_none(self):
        assert _normalize_onion_url(None) == ""

    def test_with_trailing_slash(self):
        result = _normalize_onion_url("http://darknet.onion/")
        assert result == "http://darknet.onion/"

    def test_strips_curly_brackets(self):
        result = _normalize_onion_url("{http://darknet.onion}")
        assert "{" not in result
        assert "}" not in result

    def test_strips_single_quotes(self):
        result = _normalize_onion_url("'http://darknet.onion'")
        assert "'" not in result

    def test_case_insensitive_onion_check(self):
        result = _normalize_onion_url("http://DARKNET.ONION")
        assert "DARKNET.ONION" in result or "darknet.onion" in result


ONION_16 = "abcdefghijklmnop"

class TestExtractOnionUrls:
    def test_multiple_urls(self):
        text = f"Check http://{ONION_16}.onion and http://qrstuvwxyz234567.onion and {ONION_16}.onion/path"
        urls = _extract_onion_urls(text)
        assert len(urls) == 3

    def test_deduplicates(self):
        text = f"Same url http://{ONION_16}.onion and http://{ONION_16}.onion again"
        urls = _extract_onion_urls(text)
        assert len(urls) == 1

    def test_none_text(self):
        assert _extract_onion_urls("example.com stuff") == []

    def test_empty_string(self):
        assert _extract_onion_urls("") == []

    def test_none_input(self):
        assert _extract_onion_urls(None) == []

    def test_url_with_path(self):
        text = f"http://{ONION_16}.onion/hidden/service"
        urls = _extract_onion_urls(text)
        assert len(urls) == 1
        assert "/hidden/service" in urls[0]

    def test_url_with_query(self):
        text = f"http://{ONION_16}.onion/page?id=1"
        urls = _extract_onion_urls(text)
        assert len(urls) == 1


class TestIsOnionUrl:
    def test_valid_onion(self):
        assert _is_onion_url(f"http://{ONION_16}.onion") is True

    def test_invalid_onion(self):
        assert _is_onion_url("http://example.com") is False

    def test_empty(self):
        assert _is_onion_url("") is False


class TestDecodeBingUrl:
    def test_base64_encoded(self):
        import base64
        target = "https://example.com/page"
        encoded = base64.urlsafe_b64encode(target.encode()).decode()
        href = f"https://www.bing.com/url?u=a1{encoded}"
        result = _decode_bing_url(href)
        assert "example.com" in result

    def test_plain_url(self):
        result = _decode_bing_url("https://example.com")
        assert result == "https://example.com"

    def test_relative_path(self):
        result = _decode_bing_url("/search?q=test")
        assert "bing.com" in result

    def test_none(self):
        assert _decode_bing_url(None) == ""

    def test_empty(self):
        assert _decode_bing_url("") == ""

    def test_non_matching_returns_original(self):
        result = _decode_bing_url("https://other.com/page")
        assert result == "https://other.com/page"


class TestDeduplicate:
    def test_removes_duplicates(self):
        results = [
            {"title": "A", "url": "http://example.com/a"},
            {"title": "B", "url": "http://example.com/b"},
            {"title": "A again", "url": "http://example.com/a"},
        ]
        deduped = _deduplicate(results)
        assert len(deduped) == 2

    def test_keeps_no_url_entries(self):
        results = [
            {"title": "A", "url": ""},
            {"title": "B", "url": ""},
        ]
        deduped = _deduplicate(results)
        assert len(deduped) == 2

    def test_case_insensitive(self):
        results = [
            {"title": "A", "url": "HTTP://EXAMPLE.COM"},
            {"title": "B", "url": "http://example.com"},
        ]
        deduped = _deduplicate(results)
        assert len(deduped) == 1

    def test_trailing_slash(self):
        results = [
            {"title": "A", "url": "http://example.com/page/"},
            {"title": "B", "url": "http://example.com/page"},
        ]
        deduped = _deduplicate(results)
        assert len(deduped) == 1

    def test_empty_input(self):
        assert _deduplicate([]) == []


class TestFormatImagesForChat:
    def test_with_results(self):
        results = [
            {"title": "Cat", "thumbnail": "http://img.com/cat.jpg", "url": "http://page.com/cat"},
            {"title": "Dog", "thumbnail": "http://img.com/dog.jpg", "url": "http://page.com/dog"},
        ]
        md = format_images_for_chat(results)
        assert "![Cat](" in md
        assert "![Dog](" in md
        assert "http://img.com/cat.jpg" in md
        assert "http://img.com/dog.jpg" in md

    def test_empty(self):
        assert format_images_for_chat([]) == ""

    def test_no_display_url(self):
        results = [{"title": "No img", "url": "http://page.com"}]
        assert format_images_for_chat(results) == ""

    def test_max_show(self):
        results = [{"title": f"Img{i}", "thumbnail": f"http://img.com/{i}.jpg", "url": f"http://page.com/{i}"} for i in range(10)]
        md = format_images_for_chat(results, max_show=3)
        assert md.count("![") == 3

    def test_title_with_brackets(self):
        results = [{"title": "Image [1]", "thumbnail": "http://img.com/1.jpg", "url": "http://page.com/1"}]
        md = format_images_for_chat(results)
        assert "[" in md


class TestFormatVideosForChat:
    def test_with_results(self):
        results = [
            {"title": "Video 1", "content": "http://video.com/1", "publisher": "Channel A", "duration": "5:00"},
            {"title": "Video 2", "content": "http://video.com/2", "publisher": "Channel B"},
        ]
        md = format_videos_for_chat(results)
        assert "Video 1" in md
        assert "Video 2" in md
        assert "Channel A" in md
        assert "5:00" in md

    def test_empty(self):
        assert format_videos_for_chat([]) == ""

    def test_missing_keys(self):
        results = [{"title": "No URL"}]
        md = format_videos_for_chat(results)
        assert "No URL" not in md
        assert "Video Results" in md

    def test_max_show(self):
        results = [{"title": f"V{i}", "content": f"http://v.com/{i}"} for i in range(10)]
        md = format_videos_for_chat(results, max_show=3)
        assert md.count("[V") == 3

    def test_description_truncated(self):
        long_desc = "x" * 300
        results = [{"title": "V", "content": "http://v.com/1", "description": long_desc}]
        md = format_videos_for_chat(results)
        assert "x" * 200 in md
        assert "x" * 201 not in md


class TestPerformSearch:
    def test_engine_selection_google_only(self):
        with patch("lumina.search.scraper.search_google") as mock_google:
            mock_google.return_value = [{"title": "G1", "url": "http://g.com", "description": "d"}]
            text, media = perform_search("test", engines=["google"])
            assert "Google" in text
            assert "G1" in text
            assert mock_google.called

    def test_engine_selection_multiple(self):
        with patch("lumina.search.scraper.search_google") as mock_g:
            mock_g.return_value = [{"title": "G1", "url": "http://g.com", "description": "d"}]
            with patch("lumina.search.scraper.search_bing") as mock_b:
                mock_b.return_value = [{"title": "B1", "url": "http://b.com", "description": "d"}]
                text, media = perform_search("test", engines=["google", "bing"])
                assert "Google" in text
                assert "Bing" in text

    def test_no_engines(self):
        text, media = perform_search("test", engines=[])
        assert text is not None
        assert len(text) > 0

    def test_default_engines(self):
        with patch("lumina.search.scraper.search_google") as mock_g:
            mock_g.return_value = []
            with patch("lumina.search.scraper.search_duckduckgo") as mock_d:
                mock_d.return_value = []
                with patch("lumina.search.scraper.search_wikipedia") as mock_w:
                    mock_w.return_value = []
                    text, media = perform_search("test")
                    assert mock_g.called
                    assert mock_d.called
                    assert mock_w.called

    def test_all_engines_return_no_results(self):
        with patch("lumina.search.scraper.search_google", return_value=[]):
            with patch("lumina.search.scraper.search_duckduckgo", return_value=[]):
                text, media = perform_search("test", engines=["google", "duckduckgo"])
                assert "No results found" in text

    def test_search_type_media_returns_raw_media(self):
        with patch("lumina.search.scraper.search_duckduckgo") as mock_d:
            mock_d.return_value = [{"title": "Img1", "thumbnail": "http://img.com/1.jpg"}]
            text, media = perform_search("test", engines=["duckduckgo"], search_type="images")
            assert len(media) == 1

    def test_tor_proxy_candidates_defaults(self):
        with patch.dict("os.environ", {}, clear=True):
            candidates = _tor_proxy_candidates()
            assert len(candidates) == 2
            assert "9150" in candidates[0]
            assert "9050" in candidates[1]

    def test_tor_proxy_candidates_env_override(self):
        with patch.dict("os.environ", {"TOR_SOCKS_PROXY": "socks5://custom:1080"}, clear=True):
            candidates = _tor_proxy_candidates()
            assert candidates == ["socks5://custom:1080"]

    def test_tor_proxy_candidates_multiple_env(self):
        with patch.dict("os.environ", {"TOR_PROXY": "socks5://a:1,socks5://b:2"}, clear=True):
            candidates = _tor_proxy_candidates()
            assert len(candidates) == 2
