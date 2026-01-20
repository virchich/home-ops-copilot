"""Retrieval module for RAG queries.

This module handles loading the vector index and retrieving relevant chunks
for a given question. It implements a singleton pattern for the index to
avoid reloading on every request.

Key Concepts:
- VectorStoreIndex: The searchable collection of document chunks + embeddings
- VectorIndexRetriever: Finds similar chunks using cosine similarity
- NodeWithScore: A chunk (node) paired with its similarity score

How Retrieval Works:
1. Your question gets embedded (converted to a vector)
2. We compare that vector to all chunk vectors in the index
3. Return the top-k most similar chunks (highest cosine similarity)
"""

import logging
from collections.abc import Sequence
from functools import lru_cache

from llama_index.core import Settings, StorageContext, load_index_from_storage
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import NodeWithScore
from llama_index.embeddings.openai import OpenAIEmbedding

from app.core.config import settings

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION (from centralized settings)
# =============================================================================
# All config values are now in app/core/config.py
# Override via environment variables: RAG__TOP_K=10, PATHS__INDEX_DIR=./custom


# =============================================================================
# INDEX LOADING (SINGLETON)
# =============================================================================
# We use @lru_cache to ensure the index is loaded only once.
# This is important because:
# 1. Loading from disk takes time (~100ms)
# 2. The index is read-only during queries
# 3. We don't want to reload on every API request


@lru_cache(maxsize=1)
def get_index() -> VectorStoreIndex:
    """
    Load and cache the vector index.

    This function loads the index from disk exactly once, then returns
    the cached version on subsequent calls. The @lru_cache decorator
    handles the caching automatically.

    Returns:
        VectorStoreIndex: The loaded index ready for querying

    Raises:
        FileNotFoundError: If the index hasn't been built yet
        RuntimeError: If the index fails to load

    Note:
        If you rebuild the index, you'll need to restart the server
        (or call get_index.cache_clear()) to pick up changes.
    """
    logger.info(f"Loading vector index from {settings.paths.index_dir}...")

    # Configure the embedding model
    # IMPORTANT: Must match the model used during ingestion!
    # If these don't match, retrieval quality will be terrible.
    embed_model = OpenAIEmbedding(
        model=settings.rag.embedding_model,
        api_key=settings.openai_api_key,
    )
    Settings.embed_model = embed_model

    try:
        # Load the persisted index
        storage_context = StorageContext.from_defaults(persist_dir=str(settings.paths.index_dir))
        index = load_index_from_storage(storage_context)

        # Verify it's the right type
        if not isinstance(index, VectorStoreIndex):
            raise RuntimeError(f"Expected VectorStoreIndex, got {type(index)}")

        logger.info(f"Index loaded successfully. Contains {len(index.docstore.docs)} chunks.")
        return index

    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Index not found at {settings.paths.index_dir}. "
            "Run 'make ingest' to build the index first."
        ) from e
    except Exception as e:
        raise RuntimeError(f"Failed to load index: {e}") from e


# =============================================================================
# RETRIEVAL
# =============================================================================


def retrieve(question: str, top_k: int | None = None) -> list[NodeWithScore]:
    """
    Retrieve the most relevant chunks for a question.

    This is the core retrieval function. It:
    1. Loads the index (cached after first call)
    2. Creates a retriever with the specified top_k
    3. Embeds your question and finds similar chunks
    4. Returns chunks sorted by relevance (highest score first)

    Args:
        question: The user's question
        top_k: Number of chunks to retrieve (default from settings.rag.top_k)

    Returns:
        List of NodeWithScore objects, each containing:
        - node: The chunk (text + metadata)
        - score: Similarity score (0-1, higher = more similar)

    Example:
        >>> results = retrieve("How do I change my furnace filter?")
        >>> for r in results:
        ...     print(f"Score: {r.score:.3f}")
        ...     print(f"Source: {r.node.metadata['file_name']}")
        ...     print(f"Text: {r.node.text[:100]}...")
    """
    # Use settings default if not specified
    if top_k is None:
        top_k = settings.rag.top_k

    # Get the cached index
    index = get_index()

    # Create a retriever
    # VectorIndexRetriever is the basic retriever that uses cosine similarity
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=top_k,
    )

    # Retrieve!
    # Under the hood, this:
    # 1. Embeds the question using text-embedding-3-small
    # 2. Computes cosine similarity with all chunk vectors
    # 3. Returns top_k chunks sorted by similarity
    results = retriever.retrieve(question)

    # Log some info for debugging
    if results:
        scores = [r.score for r in results if r.score is not None]
        if scores:
            logger.info(
                f"Retrieved {len(results)} chunks. Scores: max={max(scores):.3f}, min={min(scores):.3f}"
            )
    else:
        logger.warning("No chunks retrieved!")

    return results


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def format_contexts_for_llm(nodes: Sequence[NodeWithScore]) -> str:
    """
    Format retrieved nodes as context for the LLM.

    Creates a structured text block that the LLM can use to answer questions.
    Each chunk is labeled with its source for citation tracking.

    Args:
        nodes: Retrieved chunks with scores

    Returns:
        Formatted string with all contexts, ready for the LLM prompt
    """
    if not nodes:
        return "No relevant documents found."

    contexts = []
    for i, node in enumerate(nodes, 1):
        metadata = node.node.metadata
        source = metadata.get("file_name", "Unknown")
        device = metadata.get("device_name", "Unknown device")

        contexts.append(f"[Source {i}: {source} - {device}]\n{node.node.get_content()}\n")

    return "\n---\n".join(contexts)


def get_node_metadata(node: NodeWithScore) -> dict:
    """
    Extract metadata from a retrieved node for citation building.

    Args:
        node: A retrieved node with score

    Returns:
        Dictionary with citation-relevant fields
    """
    metadata = node.node.metadata
    return {
        "file_name": metadata.get("file_name", "Unknown"),
        "device_type": metadata.get("device_type", ""),
        "device_name": metadata.get("device_name", ""),
        "manufacturer": metadata.get("manufacturer", ""),
        "score": node.score,
    }


def build_source_mapping(nodes: Sequence[NodeWithScore]) -> dict[int, dict]:
    """
    Build a mapping from source index to node metadata.

    This mapping is used to validate and enrich LLM-generated citations.
    The source indices (1, 2, 3, ...) correspond to the [Source N] labels
    used in format_contexts_for_llm().

    Args:
        nodes: Retrieved nodes with scores

    Returns:
        Dictionary mapping source index (1-based) to metadata dict.
        Example: {1: {"file_name": "manual.pdf", "device_name": "Furnace", ...}}
    """
    mapping = {}
    for i, node in enumerate(nodes, 1):
        mapping[i] = get_node_metadata(node)
    return mapping
