import pytest
from unittest.mock import patch, MagicMock

from lumina.image.engine import (
    _has_google_key,
    generate_image_async,
    edit_image_async,
)


class TestProviderFailures:
    def test_try_imagen_missing_api_key(self):
        with patch("lumina.image.engine.GOOGLE_API_KEY", None):
            with patch("lumina.image.engine._try_imagen") as mock:
                mock.return_value = False
                assert mock() is False

    def test_try_gemini_flash_missing_api_key(self):
        with patch("lumina.image.engine.GOOGLE_API_KEY", None):
            with patch("lumina.image.engine._try_gemini_flash_image") as mock:
                mock.return_value = False
                assert mock() is False

    def test_try_together_missing_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            from lumina.image.engine import _try_together
            result = _try_together("test", "/tmp/test.png")
            assert result is False

    def test_try_craiyon_empty_response(self):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"images": []}
        mock_response.status_code = 200
        mock_session.post.return_value = mock_response

        with patch("lumina.image.engine.make_session", return_value=mock_session):
            from lumina.image.engine import _try_craiyon
            result = _try_craiyon("test", "/tmp/test.png")
            assert result is False

    def test_try_aihorde_missing_job_id(self):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.status_code = 200
        mock_session.post.return_value = mock_response

        with patch("lumina.image.engine.make_session", return_value=mock_session):
            from lumina.image.engine import _try_aihorde
            result = _try_aihorde("test", "/tmp/test.png")
            assert result is False

    def test_try_edit_gemini_input_not_an_image(self):
        with patch("builtins.open", side_effect=Exception("File not found")):
            from lumina.image.engine import _try_edit_gemini
            result = _try_edit_gemini("edit", "/tmp/nonexistent.png", "/tmp/out.png")
            assert result is False


class TestFallbackChain:
    @pytest.mark.asyncio
    async def test_all_6_providers_raise_exceptions(self):
        def make_provider(exc_msg):
            fn = MagicMock()
            fn.side_effect = Exception(exc_msg)
            return fn

        mock_providers = [make_provider(f"fail {i}") for i in range(6)]

        with patch("lumina.image.engine.PROVIDERS", mock_providers):
            with patch("os.makedirs"):
                with patch("lumina.image.engine.IMAGE_CACHE_DIR", "/tmp"):
                    with patch("os.path.join", return_value="/tmp/fallback.png"):
                        with patch("os.path.abspath", return_value="/tmp/fallback.png"):
                            with patch("asyncio.to_thread") as mock_thread:
                                mock_thread.side_effect = lambda f, *a, **kw: f()
                                with patch("PIL.Image.new") as mock_new:
                                    mock_img = MagicMock()
                                    mock_new.return_value = mock_img
                                    result = await generate_image_async("test failover")
                                    assert result is not None

    @pytest.mark.asyncio
    async def test_provider_exception_stops_at_next_working(self):
        failing = MagicMock(side_effect=Exception("fail"))
        failing.__name__ = "_try_mock_fail"
        succeeding = MagicMock(return_value=True)
        succeeding.__name__ = "_try_mock_success"
        mock_providers = [failing, succeeding]

        with patch("lumina.image.engine.PROVIDERS", mock_providers):
            with patch("lumina.image.engine.IMAGE_CACHE_DIR", "/tmp"):
                with patch("os.makedirs"):
                    with patch("asyncio.to_thread") as mock_thread:
                        mock_thread.side_effect = lambda f, *a, **kw: f()
                        result = await generate_image_async("test")
                        assert result is not None
                        assert failing.called
                        assert succeeding.called

    @pytest.mark.asyncio
    async def test_edit_input_not_found_returns_none(self):
        result = await edit_image_async("edit", "/tmp/nonexistent.png")
        assert result is None

    @pytest.mark.asyncio
    async def test_edit_all_providers_fail_then_pil_fallback(self):
        with patch("os.path.exists", return_value=True):
            edit_providers = [MagicMock(return_value=False), MagicMock(return_value=False)]

            with patch("lumina.image.engine.EDIT_PROVIDERS", edit_providers):
                with patch("asyncio.to_thread") as mock_thread:
                    mock_thread.side_effect = lambda f, *a, **kw: f()
                    with patch("lumina.image.engine._try_edit_pil_overlay", return_value=True) as mock_pil:
                        with patch("lumina.image.engine.IMAGE_CACHE_DIR", "/tmp"):
                            result = await edit_image_async("edit", "/tmp/src.png")
                            assert result is not None
                            mock_pil.assert_called_once()

    def test_has_google_key_false_when_not_set(self):
        with patch("lumina.image.engine.GOOGLE_API_KEY", None):
            assert _has_google_key() is False

    def test_has_google_key_true_when_set(self):
        with patch("lumina.image.engine.GOOGLE_API_KEY", "fake-key"):
            assert _has_google_key() is True
