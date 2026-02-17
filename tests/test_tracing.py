"""Tests for the tracing helpers (app.llm.tracing).

Tests cover:
- observe() is a no-op when observability is disabled
- observe() delegates to langfuse when enabled
- init_tracing() is a no-op when disabled
- init_tracing() initializes Langfuse when enabled with keys
- init_tracing() warns when keys are missing
"""

from unittest.mock import MagicMock, patch

from app.llm.tracing import init_tracing, observe


class TestObserveDisabled:
    """Tests for observe() when observability is disabled."""

    def test_returns_function_unchanged(self) -> None:
        """observe() should be a no-op when observability is disabled."""
        with patch("app.llm.tracing.settings") as mock_settings:
            mock_settings.observability.enabled = False

            @observe(name="test_fn")
            def my_function(x: int) -> int:
                return x * 2

            # Function should work normally
            assert my_function(5) == 10

    def test_preserves_function_identity(self) -> None:
        """No-op observe should return the exact same function object."""
        with patch("app.llm.tracing.settings") as mock_settings:
            mock_settings.observability.enabled = False

            def my_function() -> str:
                return "hello"

            decorated = observe(name="test")(my_function)
            assert decorated is my_function


class TestObserveEnabled:
    """Tests for observe() when observability is enabled."""

    def test_delegates_to_langfuse_observe(self) -> None:
        """observe() should delegate to langfuse.observe when enabled."""
        mock_langfuse_observe = MagicMock()
        mock_decorated = MagicMock()
        mock_langfuse_observe.return_value = mock_decorated

        with (
            patch("app.llm.tracing.settings") as mock_settings,
            patch("langfuse.observe", mock_langfuse_observe),
        ):
            mock_settings.observability.enabled = True

            result = observe(name="test_span")

            mock_langfuse_observe.assert_called_once_with(name="test_span")
            assert result is mock_decorated

    def test_falls_back_to_noop_when_import_fails(self) -> None:
        """observe() should be a no-op if langfuse import fails."""
        with patch("app.llm.tracing.settings") as mock_settings:
            mock_settings.observability.enabled = True

            import builtins

            original_import = builtins.__import__

            def mock_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
                if "langfuse" in name:
                    raise ImportError("No module named 'langfuse'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):

                @observe(name="test_fn")
                def my_function(x: int) -> int:
                    return x + 1

                assert my_function(3) == 4


class TestInitTracingDisabled:
    """Tests for init_tracing() when observability is disabled."""

    def test_is_noop_when_disabled(self) -> None:
        """init_tracing() should do nothing when observability is disabled."""
        with patch("app.llm.tracing.settings") as mock_settings:
            mock_settings.observability.enabled = False

            # Should not raise
            init_tracing()


class TestInitTracingEnabled:
    """Tests for init_tracing() when observability is enabled."""

    def test_initializes_langfuse_with_keys(self) -> None:
        """init_tracing() should create a Langfuse instance with config keys."""
        mock_langfuse_cls = MagicMock()

        with (
            patch("app.llm.tracing.settings") as mock_settings,
            patch("langfuse.Langfuse", mock_langfuse_cls),
        ):
            mock_settings.observability.enabled = True
            mock_settings.observability.langfuse_public_key = "pk-test"
            mock_settings.observability.langfuse_secret_key = "sk-test"
            mock_settings.observability.langfuse_base_url = "https://us.cloud.langfuse.com"

            init_tracing()

            mock_langfuse_cls.assert_called_once_with(
                public_key="pk-test",
                secret_key="sk-test",
                base_url="https://us.cloud.langfuse.com",
            )

    def test_warns_when_keys_missing(self) -> None:
        """init_tracing() should warn and skip when keys are missing."""
        with (
            patch("app.llm.tracing.settings") as mock_settings,
            patch("app.llm.tracing.logger") as mock_logger,
        ):
            mock_settings.observability.enabled = True
            mock_settings.observability.langfuse_public_key = ""
            mock_settings.observability.langfuse_secret_key = ""

            init_tracing()

            mock_logger.warning.assert_called_once()
            assert "missing" in mock_logger.warning.call_args[0][0].lower()

    def test_handles_langfuse_import_error(self) -> None:
        """init_tracing() should warn gracefully if langfuse not installed."""
        with patch("app.llm.tracing.settings") as mock_settings:
            mock_settings.observability.enabled = True
            mock_settings.observability.langfuse_public_key = "pk-test"
            mock_settings.observability.langfuse_secret_key = "sk-test"

            import builtins

            original_import = builtins.__import__

            def mock_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
                if "langfuse" in name:
                    raise ImportError("No module named 'langfuse'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                # Should not raise
                init_tracing()
