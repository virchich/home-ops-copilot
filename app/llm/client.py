"""Centralized LLM client with optional Langfuse tracing.

When observability is enabled, uses langfuse.openai.OpenAI which
auto-traces all LLM calls (token counts, latencies, inputs/outputs).
When disabled, uses the plain openai.OpenAI client.

Both paths are wrapped with instructor for structured Pydantic outputs.
"""

import logging
from functools import lru_cache

import instructor

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_llm_client() -> instructor.Instructor:
    """Get a cached instructor-patched OpenAI client.

    When ``settings.observability.enabled`` is True and Langfuse keys
    are configured, returns a client backed by ``langfuse.openai.OpenAI``
    which automatically traces every LLM call.

    Falls back to the plain ``openai.OpenAI`` client when:
    - Observability is disabled (default)
    - Langfuse keys are missing (logs a warning)
    - Langfuse import fails (logs a warning)

    Returns:
        instructor.Instructor: OpenAI client with instructor patching.
    """
    if settings.observability.enabled:
        obs = settings.observability
        if not obs.langfuse_public_key or not obs.langfuse_secret_key:
            logger.warning(
                "Observability enabled but Langfuse keys are missing. "
                "Falling back to plain OpenAI client."
            )
        else:
            try:
                from langfuse.openai import OpenAI as LangfuseOpenAI

                client = LangfuseOpenAI(api_key=settings.openai_api_key)
                logger.info("Using Langfuse-instrumented OpenAI client")
                return instructor.from_openai(client)
            except ImportError:
                logger.warning(
                    "langfuse package not installed. Falling back to plain OpenAI client."
                )

    from openai import OpenAI

    return instructor.from_openai(OpenAI(api_key=settings.openai_api_key))
