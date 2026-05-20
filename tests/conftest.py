import sys
import os
from unittest.mock import MagicMock, AsyncMock

os.environ.setdefault("GROQ_API_KEY", "test-dummy-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-dummy-key")
os.environ.setdefault("TOGETHER_API_KEY", "test-dummy-key")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.mock_providers.mock_llm import (
    MockAsyncLLMClient,
    MOCK_SEARCH_NEEDED,
    MOCK_SEARCH_NOT_NEEDED,
    MOCK_MARKDOWN_WRAPPED_JSON,
)
from tests.mock_providers.mock_search_engines import (
    MALICIOUS_HTML_SCRIPT,
    MALICIOUS_HTML_GIANT,
    MALICIOUS_HTML_MALFORMED,
    MALICIOUS_HTML_UNICODE,
    MALICIOUS_HTML_HIDDEN_INSTRUCTION,
    MOCK_GOOGLE_EMPTY,
    MOCK_BING_STANDARD,
)
from tests.mock_providers.mock_image_providers import (
    MockImageProvider,
    MockImageProviderBypass,
)
