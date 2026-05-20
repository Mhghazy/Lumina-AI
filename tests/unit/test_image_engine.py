import os
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from io import BytesIO
from PIL import Image as PILImage

from lumina.image.engine import (
    _has_google_key,
    PROVIDERS,
    EDIT_PROVIDERS,
    _try_edit_pil_overlay,
    generate_image_async,
    edit_image_async,
)


class TestHasGoogleKey:
    def test_google_key_set(self):
        with patch("lumina.image.engine.GOOGLE_API_KEY", "fake-key"):
            assert _has_google_key() is True

    def test_google_key_not_set(self):
        with patch("lumina.image.engine.GOOGLE_API_KEY", None):
            assert _has_google_key() is False

    def test_google_key_empty(self):
        with patch("lumina.image.engine.GOOGLE_API_KEY", ""):
            assert _has_google_key() is False


class TestProviderOrder:
    def test_providers_order(self):
        names = [fn.__name__ for fn in PROVIDERS]
        assert names == [
            "_try_pollinations",
            "_try_together",
            "_try_craiyon",
            "_try_imagen",
            "_try_gemini_flash_image",
            "_try_aihorde",
        ]

    def test_edit_providers_order(self):
        names = [fn.__name__ for fn in EDIT_PROVIDERS]
        assert names == [
            "_try_edit_gemini",
            "_try_edit_aihorde",
        ]


class TestEditPilOverlay:
    @pytest.fixture
    def temp_dir(self, tmp_path):
        return tmp_path

    def test_creates_image(self, temp_dir):
        src_path = os.path.join(temp_dir, "src.jpg")
        out_path = os.path.join(temp_dir, "out.png")
        img = PILImage.new("RGB", (500, 300), color=(100, 100, 100))
        img.save(src_path)

        result = _try_edit_pil_overlay("make it blue", src_path, out_path)
        assert result is True
        assert os.path.exists(out_path)

    def test_resizes_to_1024(self, temp_dir):
        src_path = os.path.join(temp_dir, "src.jpg")
        out_path = os.path.join(temp_dir, "out.png")
        img = PILImage.new("RGB", (200, 200), color=(100, 100, 100))
        img.save(src_path)

        _try_edit_pil_overlay("test", src_path, out_path)
        result_img = PILImage.open(out_path)
        assert result_img.size == (1024, 1024)

    def test_banner_contains_prompt(self, temp_dir):
        src_path = os.path.join(temp_dir, "src.jpg")
        out_path = os.path.join(temp_dir, "out.png")
        PILImage.new("RGB", (100, 100), color=(0, 0, 0)).save(src_path)

        _try_edit_pil_overlay("make it blue", src_path, out_path)
        result_img = PILImage.open(out_path)
        assert result_img.size == (1024, 1024)

    def test_input_not_found(self, temp_dir):
        out_path = os.path.join(temp_dir, "out.png")
        result = _try_edit_pil_overlay("edit", "/nonexistent/path.jpg", out_path)
        assert result is False


class TestGenerateImageAsync:
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_chain_stops_on_first_success(self):
        mock_providers = [
            MagicMock(return_value=True),
            MagicMock(return_value=False),
        ]
        with patch("lumina.image.engine.PROVIDERS", mock_providers):
            with patch("lumina.image.engine.IMAGE_CACHE_DIR", str(__file__)):
                with patch("asyncio.to_thread", new_callable=MagicMock) as mock_thread:
                    mock_thread.side_effect = lambda f, *a, **kw: f()

                    mock_providers[0].assert_not_called() is None

    @pytest.mark.asyncio
    async def test_chain_cascades_on_failure(self):
        success_fn = MagicMock(return_value=True)

        def side_effect(*a, **kw):
            return False

        mock_providers = [
            MagicMock(side_effect=lambda *a, **kw: False),
            MagicMock(side_effect=lambda *a, **kw: False),
            success_fn,
        ]
        with patch("lumina.image.engine.PROVIDERS", mock_providers):
            with patch("lumina.image.engine.IMAGE_CACHE_DIR", str(__file__)):
                with patch("asyncio.to_thread") as mock_thread:
                    mock_thread.side_effect = lambda f, *a, **kw: f()
                    result = await generate_image_async("test prompt")
                    assert result is not None
                    assert success_fn.called

    @pytest.mark.asyncio
    async def test_all_providers_fail_uses_pil_fallback(self):
        mock_providers = [MagicMock(return_value=False) for _ in range(6)]
        with patch("lumina.image.engine.PROVIDERS", mock_providers):
            with patch("os.makedirs"):
                with patch("os.path.join", return_value="/tmp/test.png"):
                    with patch("asyncio.to_thread") as mock_thread:
                        mock_thread.side_effect = lambda f, *a, **kw: f()
                        with patch("PIL.Image.new") as mock_img_new:
                            mock_img = MagicMock()
                            mock_img_new.return_value = mock_img
                            result = await generate_image_async("test")
                            assert result is not None

    @pytest.mark.asyncio
    async def test_all_providers_and_pil_fail(self):
        mock_providers = [MagicMock(return_value=False) for _ in range(6)]
        with patch("lumina.image.engine.PROVIDERS", mock_providers):
            with patch("os.makedirs"):
                with patch("os.path.join", return_value="/tmp/test.png"):
                    with patch("asyncio.to_thread") as mock_thread:
                        mock_thread.side_effect = lambda f, *a, **kw: f()
                        with patch("PIL.Image.new", side_effect=Exception("PIL fail")):
                            result = await generate_image_async("test")
                            assert result is None

    @pytest.mark.asyncio
    async def test_empty_prompt_still_processed(self):
        mock_providers = [MagicMock(return_value=True)]
        with patch("lumina.image.engine.PROVIDERS", mock_providers):
            with patch("os.makedirs"):
                with patch("lumina.image.engine.IMAGE_CACHE_DIR", "/tmp"):
                    with patch("asyncio.to_thread") as mock_thread:
                        mock_thread.side_effect = lambda f, *a, **kw: f()
                        result = await generate_image_async("")
                        assert result is not None


class TestEditImageAsync:
    @pytest.mark.asyncio
    async def test_missing_input_returns_none(self):
        result = await edit_image_async("edit prompt", "/nonexistent/path.png")
        assert result is None

    @pytest.mark.asyncio
    async def test_edit_chain_gemini_success(self):
        with patch("os.path.exists", return_value=True):
            with patch("lumina.image.engine.EDIT_PROVIDERS", [MagicMock(return_value=True)]):
                with patch("asyncio.to_thread") as mock_thread:
                    mock_thread.side_effect = lambda f, *a, **kw: f()
                    with patch("lumina.image.engine.IMAGE_CACHE_DIR", "/tmp"):
                        result = await edit_image_async("edit", "/tmp/src.png")
                        assert result is not None

    @pytest.mark.asyncio
    async def test_edit_falls_back_to_pil(self):
        with patch("os.path.exists", return_value=True):
            edit_providers = [MagicMock(return_value=False), MagicMock(return_value=False)]
            with patch("lumina.image.engine.EDIT_PROVIDERS", edit_providers):
                with patch("asyncio.to_thread") as mock_thread:
                    mock_thread.side_effect = lambda f, *a, **kw: f()
                    with patch("lumina.image.engine._try_edit_pil_overlay", return_value=True) as mock_pil:
                        with patch("lumina.image.engine.IMAGE_CACHE_DIR", "/tmp"):
                            result = await edit_image_async("edit", "/tmp/src.png")
                            assert result is not None
                            assert mock_pil.called

    @pytest.mark.asyncio
    async def test_all_edit_providers_and_pil_fail(self):
        with patch("os.path.exists", return_value=True):
            edit_providers = [MagicMock(return_value=False), MagicMock(return_value=False)]
            with patch("lumina.image.engine.EDIT_PROVIDERS", edit_providers):
                with patch("asyncio.to_thread") as mock_thread:
                    mock_thread.side_effect = lambda f, *a, **kw: f()
                    with patch("lumina.image.engine._try_edit_pil_overlay", return_value=False):
                        with patch("lumina.image.engine.IMAGE_CACHE_DIR", "/tmp"):
                            result = await edit_image_async("edit", "/tmp/src.png")
                            assert result is None
