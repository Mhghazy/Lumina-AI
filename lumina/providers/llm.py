import os
from groq import AsyncGroq
from openai import AsyncOpenAI
from lumina.core.config import GEMMA_MODEL

# Initialize Groq client
groq_client = AsyncGroq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

# Initialize Google Gemma client via OpenAI compatibility layer
gemma_client = AsyncOpenAI(
    api_key=os.environ.get("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)
