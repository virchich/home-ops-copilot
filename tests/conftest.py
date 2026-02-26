"""Shared test fixtures and configuration."""

from collections.abc import Generator

import pytest

from app.llm.client import get_llm_client


@pytest.fixture(autouse=True)
def _clear_llm_client_cache() -> Generator[None]:
    """Clear the LLM client lru_cache after every test.

    Prevents test pollution when one test mocks get_llm_client()
    and the cached mock bleeds into subsequent tests.
    """
    yield
    get_llm_client.cache_clear()
