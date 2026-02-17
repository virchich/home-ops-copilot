"""Application configuration using pydantic-settings.

This module centralizes all configuration for the application.
Settings are organized into nested groups for clarity:

- paths: Data directories (raw docs, index, metadata)
- rag: RAG pipeline settings (chunking, retrieval, embedding)
- llm: LLM settings (model, temperature, tokens)

Environment variables use `__` as nested delimiter:
    RAG__TOP_K=10
    LLM__TEMPERATURE=0.5
    PATHS__INDEX_DIR=./custom/index

Or set them in .env file.
"""

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# =============================================================================
# NESTED SETTINGS MODELS
# =============================================================================
# These are plain Pydantic models (not BaseSettings) that get composed
# into the main Settings class. They provide logical grouping.


class PathSettings(BaseModel):
    """Data directory paths.

    All paths are relative to the project root.
    """

    raw_docs_dir: Path = Field(
        default=Path("data/raw_docs"),
        description="Directory containing raw PDF documents",
    )
    metadata_file: Path = Field(
        default=Path("data/metadata.json"),
        description="JSON file with document metadata",
    )
    index_dir: Path = Field(
        default=Path("data/indexes"),
        description="Directory for persisted vector index",
    )


class RAGSettings(BaseModel):
    """RAG pipeline settings.

    These control document chunking, retrieval, and embedding.
    """

    # Chunking
    chunk_size: int = Field(
        default=512,
        description="Target tokens per chunk (512 is a good balance)",
        ge=100,
        le=2000,
    )
    chunk_overlap: int = Field(
        default=50,
        description="Token overlap between chunks (preserves context)",
        ge=0,
        le=200,
    )

    # Retrieval
    top_k: int = Field(
        default=5,
        description="Number of chunks to retrieve per query",
        ge=1,
        le=20,
    )
    min_relevance_score: float = Field(
        default=0.3,
        description="Minimum similarity score to consider a chunk relevant (0-1)",
        ge=0.0,
        le=1.0,
    )

    # Reranking (Week 4)
    rerank_enabled: bool = Field(
        default=False,
        description="Enable cross-encoder reranking (experimental - may reduce quality on technical docs)",
    )
    rerank_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Cross-encoder model for reranking (speed vs accuracy tradeoff)",
    )
    rerank_top_n: int = Field(
        default=5,
        description="Number of results to return after reranking",
        ge=1,
        le=20,
    )

    # Embedding
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model for vectorization",
    )


class LLMSettings(BaseModel):
    """LLM generation settings.

    These control how the language model generates responses.
    """

    model: str = Field(
        default="gpt-5.2",
        description="OpenAI model for generation",
    )
    temperature: float = Field(
        default=0.3,
        description="Sampling temperature (lower = more deterministic)",
        ge=0.0,
        le=2.0,
    )
    max_completion_tokens: int = Field(
        default=1000,
        description="Maximum tokens in the response",
        ge=100,
        le=4000,
    )


class ObservabilitySettings(BaseModel):
    """Langfuse observability settings.

    When enabled, all LLM calls, retrieval, and workflow nodes are
    traced to Langfuse Cloud. When disabled (default), everything
    is a no-op with zero overhead.

    Env vars: OBSERVABILITY__ENABLED=true, OBSERVABILITY__LANGFUSE_PUBLIC_KEY=pk-...
    """

    enabled: bool = Field(
        default=False,
        description="Enable Langfuse tracing (requires valid keys)",
    )
    langfuse_public_key: str = Field(
        default="",
        description="Langfuse public key (pk-...)",
    )
    langfuse_secret_key: str = Field(
        default="",
        description="Langfuse secret key (sk-...)",
    )
    langfuse_base_url: str = Field(
        default="https://us.cloud.langfuse.com",
        description="Langfuse base URL (e.g. https://us.cloud.langfuse.com for US region)",
    )


# =============================================================================
# MAIN SETTINGS CLASS
# =============================================================================


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Nested settings can be overridden with `__` delimiter:
        RAG__TOP_K=10
        LLM__TEMPERATURE=0.5

    Or in .env file:
        OPENAI_API_KEY=sk-...
        RAG__CHUNK_SIZE=256
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # Enables RAG__TOP_K style overrides
        extra="ignore",
    )

    # API Keys
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key",
    )

    # App metadata
    app_name: str = Field(
        default="Home Ops Copilot",
        description="Application name",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    # Nested settings groups
    paths: PathSettings = Field(default_factory=PathSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)


# Singleton instance - import this in other modules
settings = Settings()
