MOCK_SEARCH_NEEDED = {
    "needs_search": True,
    "query": "python async programming",
    "type": "text"
}
MOCK_SEARCH_NOT_NEEDED = {"needs_search": False}
MOCK_MALFORMED_JSON = "{invalid"
MOCK_MARKDOWN_WRAPPED_JSON = '```json\n{"needs_search":false}\n```'
MOCK_TRIPLE_BACKTICK_NO_NEWLINE = '```{"needs_search":true}```'


class MockMessage:
    def __init__(self, content: str):
        self.content = content


class MockChoice:
    def __init__(self, content: str):
        self.message = MockMessage(content)


class MockCompletion:
    def __init__(self, content: str):
        self.choices = [MockChoice(content)]


class MockAsyncChatCompletions:
    def __init__(self, response_content: str = "{}", raise_on_create: bool = False):
        self.response_content = response_content
        self.raise_on_create = raise_on_create

    async def create(self, *args, **kwargs):
        if self.raise_on_create:
            raise Exception("Mock API Error")
        return MockCompletion(self.response_content)


class MockAsyncChat:
    def __init__(self, response_content: str = "{}", raise_on_create: bool = False):
        self.completions = MockAsyncChatCompletions(response_content, raise_on_create)


class MockAsyncLLMClient:
    def __init__(self, response_content: str = "{}", raise_on_create: bool = False):
        self._chat = MockAsyncChat(response_content, raise_on_create)

    @property
    def chat(self):
        return self._chat
