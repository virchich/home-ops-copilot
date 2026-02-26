"""Tracing helpers for Langfuse observability.

Provides:
- ``observe()``: A decorator that traces function calls when observability
  is enabled, and acts as a no-op when disabled.
- ``init_tracing()``: Initializes the Langfuse singleton at app startup.

When ``settings.observability.enabled`` is False (the default), both
functions have zero overhead — ``observe()`` returns the original function
unmodified, and ``init_tracing()`` is a no-op.
"""

import logging
import os
from collections.abc import Callable
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Propagate OBSERVABILITY__* keys to native LANGFUSE_* env vars eagerly.
#
# The Langfuse SDK auto-initialises from LANGFUSE_PUBLIC_KEY / SECRET_KEY
# the first time it is imported.  Our config uses the OBSERVABILITY__*
# prefix, so without this bridge the SDK logs a noisy "initialized without
# public_key" warning.  Using setdefault ensures we never clobber env vars
# the user set directly.
# ---------------------------------------------------------------------------
if settings.observability.enabled:
    _obs = settings.observability
    if _obs.langfuse_public_key:
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", _obs.langfuse_public_key)
    if _obs.langfuse_secret_key:
        os.environ.setdefault("LANGFUSE_SECRET_KEY", _obs.langfuse_secret_key)
    if _obs.langfuse_base_url:
        os.environ.setdefault("LANGFUSE_HOST", _obs.langfuse_base_url)


def observe(**kwargs: Any) -> Callable[..., Any]:
    """Decorator that traces function execution via Langfuse when enabled.

    When observability is enabled, delegates to ``langfuse.decorators.observe()``.
    When disabled, returns the function unmodified (zero overhead).

    Args:
        **kwargs: Passed through to ``langfuse.decorators.observe()``
            (e.g., ``name``, ``as_type``).

    Returns:
        Decorated function (traced) or the original function (no-op).

    Example::

        @observe(name="retrieve_docs")
        def retrieve_docs(state):
            ...
    """
    if settings.observability.enabled:
        try:
            from langfuse import observe as langfuse_observe

            return langfuse_observe(**kwargs)  # type: ignore[no-any-return]
        except ImportError:
            logger.warning("langfuse not installed; @observe() is a no-op")

    # No-op: return the function unchanged
    def noop_decorator(fn: Callable) -> Callable:
        return fn

    return noop_decorator


def init_tracing() -> None:
    """Initialize Langfuse tracing at app startup.

    Configures the Langfuse singleton with API keys from settings.
    Only runs when observability is enabled and keys are present.
    Safe to call multiple times (idempotent).

    Note: native ``LANGFUSE_*`` env vars are set at module load time
    (above) so the SDK's auto-init picks up keys before any import.
    """
    if not settings.observability.enabled:
        logger.debug("Observability disabled; skipping Langfuse init")
        return

    obs = settings.observability
    if not obs.langfuse_public_key or not obs.langfuse_secret_key:
        logger.warning(
            "Observability enabled but Langfuse keys are missing. Tracing will not be active."
        )
        return

    try:
        from langfuse import Langfuse

        Langfuse(
            public_key=obs.langfuse_public_key,
            secret_key=obs.langfuse_secret_key,
            base_url=obs.langfuse_base_url,
        )
        logger.info(f"Langfuse tracing initialized (base_url={obs.langfuse_base_url})")
    except ImportError:
        logger.warning("langfuse package not installed; tracing not available")
    except Exception:
        logger.exception("Failed to initialize Langfuse tracing")
