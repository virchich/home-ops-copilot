"""SSL certificate setup for environments with custom CA bundles.

Injects ``truststore`` so that Python's ``ssl`` module (and by extension
``httpx``, the OpenAI SDK, etc.) uses the **operating-system certificate
store** instead of the bundled ``certifi`` CA file.

This fixes SSL_CERTIFICATE_VERIFY_FAILED errors in environments where an
SSL-inspection proxy injects its own CA that the OS trusts but
``certifi`` does not.

Call ``configure_ssl()`` once, early in each entrypoint (FastAPI startup,
eval runners, CLI scripts) — before any HTTP client is created.

Safety:
- Read-only: does not modify Keychain or any system files.
- Process-scoped: only affects the current Python process.
- No-op when truststore is unavailable (graceful fallback).
"""

import logging

logger = logging.getLogger(__name__)

_configured = False


def configure_ssl() -> None:
    """Inject truststore into Python's SSL layer (idempotent).

    Safe to call multiple times — only the first call has an effect.
    Falls back silently if ``truststore`` is not installed.
    """
    global _configured  # noqa: PLW0603
    if _configured:
        return

    try:
        import truststore

        truststore.inject_into_ssl()
        _configured = True
        logger.debug("truststore injected: using OS certificate store")
    except ImportError:
        logger.debug("truststore not installed; using default certifi CA bundle")
    except Exception:
        logger.warning(
            "truststore injection failed; using default certifi CA bundle", exc_info=True
        )
