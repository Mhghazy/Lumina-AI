class MockImageProvider:
    def __init__(self, name: str, succeed_on_attempt: int = 1):
        self.name = name
        self.succeed_on_attempt = succeed_on_attempt
        self.attempts = 0

    async def generate(self, prompt: str, filepath: str) -> bool:
        self.attempts += 1
        if self.attempts >= self.succeed_on_attempt:
            return True
        raise Exception(f"{self.name} failed on attempt {self.attempts}")


class MockImageProviderBypass:
    """Provider that always succeeds regardless of prompt content."""
    async def generate(self, prompt: str, filepath: str) -> bool:
        return True
