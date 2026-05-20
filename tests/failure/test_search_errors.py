import json
import pytest
from unittest.mock import patch, MagicMock

from lumina.search.scraper import (
    search_google,
    search_bing,
    search_duckduckgo,
    search_wikipedia,
    search_ahmia,
    search_onion_direct,
    perform_search,
)
from lumina.routing.classifier import classify_search_need
from tests.mock_providers.mock_llm import MockAsyncLLMClient


class TestSearchEngineErrors:
    def test_search_google_network_failure(self):
        with patch("lumina.search.scraper.google_search_api", side_effect=Exception("Network error")):
            results = search_google("test query")
            assert results == []

    def test_search_bing_parse_failure(self):
        with patch("lumina.search.scraper._fetch_soup", return_value=(MagicMock(), MagicMock())):
            soup = MagicMock()
            soup.select.return_value = []
            with patch("lumina.search.scraper._fetch_soup", return_value=(soup, MagicMock())):
                results = search_bing("test query")
                assert results == []

    def test_search_duckduckgo_unrecognized_type(self):
        with patch("lumina.search.scraper.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            mock_ddgs.__enter__.return_value = mock_instance
            results = search_duckduckgo("test", search_type="unknown_type")
            assert results == []

    def test_search_wikipedia_disambiguation(self):
        import wikipedia.exceptions

        mock_page = MagicMock()
        mock_page.title = "opt1"
        mock_page.url = "http://wiki.com/opt1"

        with patch("lumina.search.scraper.wikipedia.search", return_value=["ambiguous"]):
            with patch("lumina.search.scraper.wikipedia.page", side_effect=[
                wikipedia.exceptions.DisambiguationError("test", ["opt1", "opt2"]),
                mock_page,
            ]):
                with patch("lumina.search.scraper.wikipedia.summary", return_value="Summary text"):
                    results = search_wikipedia("ambiguous term")
                    assert len(results) == 1
                    assert results[0]["title"] == "opt1"

    def test_search_wikipedia_disambiguation_option_fails(self):
        import wikipedia.exceptions

        with patch("lumina.search.scraper.wikipedia.search", return_value=["ambiguous"]):
            page_mock = MagicMock()
            page_mock.url = "http://wiki.com/opt1"

            with patch("lumina.search.scraper.wikipedia.page", side_effect=[
                wikipedia.exceptions.DisambiguationError("test", ["opt1", "opt2"]),
                page_mock,
            ]):
                with patch("lumina.search.scraper.wikipedia.summary", side_effect=Exception("Summary failed")):
                    results = search_wikipedia("ambiguous term")
                    assert results == []

    def test_search_wikipedia_no_results(self):
        with patch("lumina.search.scraper.wikipedia.search", return_value=[]):
            results = search_wikipedia("nonexistent")
            assert results == []

    def test_search_ahmia_timeout(self):
        with patch("lumina.search.scraper._fetch_soup", side_effect=Exception("timeout")):
            results = search_ahmia("test")
            assert results == []

    def test_search_onion_direct_no_onions(self):
        results = search_onion_direct("normal query without onion urls")
        assert results == []

    def test_search_onion_direct_proxy_failure(self):
        with patch("lumina.search.scraper._extract_onion_urls", return_value=["http://dark.onion"]):
            with patch("lumina.search.scraper._fetch_onion_soup", side_effect=Exception("SOCKS5 connection failed")):
                results = search_onion_direct("http://dark.onion")
                assert len(results) == 1
                assert "failed" in results[0]["title"].lower()


class TestClassificationErrors:
    @pytest.mark.asyncio
    async def test_classify_search_need_timeout(self):
        client = MockAsyncLLMClient("", raise_on_create=True)
        with patch("lumina.routing.classifier.groq_client", client):
            with patch("lumina.routing.classifier.gemma_client", client):
                result = await classify_search_need("test", [], "Conscious")
                assert result == {"needs_search": False}

    @pytest.mark.asyncio
    async def test_classify_search_need_empty_message(self):
        client = MockAsyncLLMClient(json.dumps({"needs_search": False}))
        with patch("lumina.routing.classifier.groq_client", client):
            with patch("lumina.routing.classifier.gemma_client", client):
                result = await classify_search_need("", [], "Conscious")
                assert result == {"needs_search": False}

    @pytest.mark.asyncio
    async def test_classify_search_need_api_error(self):
        client = MockAsyncLLMClient("", raise_on_create=True)
        with patch("lumina.routing.classifier.groq_client", client):
            with patch("lumina.routing.classifier.gemma_client", client):
                result = await classify_search_need("test", [], "Conscious")
                assert result == {"needs_search": False}


class TestAggregatorErrors:
    def test_perform_search_empty_results_all_engines(self):
        with patch("lumina.search.scraper.search_google", return_value=[]):
            with patch("lumina.search.scraper.search_duckduckgo", return_value=[]):
                text, media = perform_search("test", engines=["google", "duckduckgo"])
                assert "No results found" in text

    def test_perform_search_some_engines_fail_some_succeed(self):
        with patch("lumina.search.scraper.search_google", return_value=[]):
            with patch("lumina.search.scraper.search_duckduckgo", return_value=[{"title": "R1", "url": "http://r.com", "description": "d"}]):
                text, media = perform_search("test", engines=["google", "duckduckgo"])
                assert "R1" in text
                assert "No results found" in text
