"""Gemini via LangChain. Returns None when no key is configured, so the app still works without an LLM."""
from functools import lru_cache

from app.config import get_settings


@lru_cache
def get_llm():
    s = get_settings()
    if not s.google_api_key:
        return None
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=s.gemini_model, google_api_key=s.google_api_key, temperature=0,
                                  timeout=20, max_retries=1)
