"""Retrieval module for RAG queries.

This module handles loading the vector index and retrieving relevant chunks
for a given question. It implements a singleton pattern for the index to
avoid reloading on every request.

Key Concepts:
- VectorStoreIndex: The searchable collection of document chunks + embeddings
- VectorIndexRetriever: Finds similar chunks using cosine similarity
- NodeWithScore: A chunk (node) paired with its similarity score
- MetadataFilters: Filter chunks by metadata before similarity search

How Retrieval Works:
1. Your question gets embedded (converted to a vector)
2. (Optional) Filter chunks by metadata (e.g., device_type)
3. Compare that vector to filtered chunk vectors in the index
4. Return the top-k most similar chunks (highest cosine similarity)

Week 4 Enhancement: Metadata Filtering
- Detects device types from the question (e.g., "furnace filter" → furnace)
- Filters retrieval to only relevant document subsets
- Falls back to unfiltered search if no device detected
"""

import logging
from collections.abc import Sequence
from functools import lru_cache

from llama_index.core import Settings, StorageContext, load_index_from_storage
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.vector_stores import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)
from llama_index.embeddings.openai import OpenAIEmbedding

from app.core.config import settings
from app.llm.tracing import observe

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
# RERANKER (Week 4)
# =============================================================================
# Cross-encoder reranking improves precision by re-scoring retrieved chunks
# based on their relevance to the query. This is more accurate than
# bi-encoder similarity but slower, so we use it as a second pass.


@lru_cache(maxsize=1)
def get_reranker() -> SentenceTransformerRerank | None:
    """
    Get a cached reranker instance.

    Returns None if reranking is disabled in settings.
    The reranker is loaded once and cached for efficiency.

    Returns:
        SentenceTransformerRerank if enabled, None otherwise.
    """
    if not settings.rag.rerank_enabled:
        logger.info("Reranking is disabled")
        return None

    logger.info(f"Loading reranker model: {settings.rag.rerank_model}")
    reranker = SentenceTransformerRerank(
        model=settings.rag.rerank_model,
        top_n=settings.rag.rerank_top_n,
    )
    logger.info("Reranker loaded successfully")
    return reranker


def rerank_nodes(
    nodes: list[NodeWithScore],
    question: str,
) -> list[NodeWithScore]:
    """
    Rerank retrieved nodes using a cross-encoder model.

    Cross-encoders jointly encode the query and document, providing
    more accurate relevance scores than bi-encoder similarity.

    Args:
        nodes: Retrieved nodes with initial similarity scores
        question: The user's question

    Returns:
        Reranked nodes, limited to top_n most relevant
    """
    reranker = get_reranker()
    if reranker is None or not nodes:
        return nodes

    # Create a QueryBundle for the reranker
    query_bundle = QueryBundle(query_str=question)

    # Rerank
    reranked = reranker.postprocess_nodes(nodes, query_bundle)

    logger.info(
        f"Reranked {len(nodes)} nodes to {len(reranked)} (top_n={settings.rag.rerank_top_n})"
    )

    return reranked


# =============================================================================
# DEVICE TYPE DETECTION
# =============================================================================

# Mapping of keywords to device types
# Keys are device_type values from metadata.json, values are trigger keywords
# NOTE: Some keywords (e.g., humidity, condensation) appear in multiple device lists
# because multiple devices can address those issues.
DEVICE_KEYWORDS: dict[str, list[str]] = {
    "furnace": ["furnace", "heating system", "gas furnace", "filter size", "merv"],
    "thermostat": ["thermostat", "ecobee", "temperature setting", "schedule", "smart thermostat"],
    # HRV affects air quality, moisture, and condensation
    # NOTE: "humidity" included because HRV helps control indoor humidity
    "hrv": [
        "hrv",
        "ventilator",
        "ventilation",
        "air exchanger",
        "heat recovery",
        "condensation",
        "windows fog",
        "fresh air",
        "humidity",  # HRV controls humidity via ventilation
    ],
    # Humidifier affects indoor humidity levels
    # NOTE: "humidity" included because humidifier directly sets humidity
    "humidifier": ["humidifier", "humidistat", "dry air", "humidity"],
    "water_heater": ["water heater", "hot water", "tank temperature", "hot water tank"],
    "water_softener": ["water softener", "softener", "salt", "hard water", "regeneration"],
    "energy_meter": ["energy meter", "power meter", "electricity usage", "power consumption"],
}


def detect_device_types(question: str) -> list[str]:
    """
    Detect device types mentioned in a question.

    Uses keyword matching to identify which device(s) the question is about.
    This enables metadata filtering to retrieve only relevant documents.

    Args:
        question: The user's question

    Returns:
        List of device_type values (e.g., ["furnace", "humidifier"]).
        Empty list if no specific device detected.

    Examples:
        >>> detect_device_types("How do I change my furnace filter?")
        ['furnace']
        >>> detect_device_types("What humidity level should I set?")
        ['humidifier', 'hrv']  # Both relate to humidity
        >>> detect_device_types("How do I save energy?")
        []  # Too general, no specific device
    """
    question_lower = question.lower()
    detected = []

    for device_type, keywords in DEVICE_KEYWORDS.items():
        if any(keyword in question_lower for keyword in keywords):
            detected.append(device_type)

    logger.debug(f"Detected device types: {detected} for question: {question[:50]}...")
    return detected


def build_metadata_filters(device_types: list[str]) -> MetadataFilters | None:
    """
    Build LlamaIndex metadata filters from detected device types.

    Creates an OR filter that matches any of the detected device types.
    This allows retrieval to search across multiple relevant document sets.

    Args:
        device_types: List of device_type values to filter by

    Returns:
        MetadataFilters object for LlamaIndex, or None if no filters needed.
    """
    if not device_types:
        return None

    # Create OR filter: match ANY of the detected device types
    # Type annotation needed due to list invariance (mypy)
    filters: list[MetadataFilter | MetadataFilters] = [
        MetadataFilter(
            key="device_type",
            value=device_type,
            operator=FilterOperator.EQ,
        )
        for device_type in device_types
    ]

    return MetadataFilters(
        filters=filters,
        condition=FilterCondition.OR,
    )


# =============================================================================
# RETRIEVAL
# =============================================================================


@observe(name="retrieve")
def retrieve(
    question: str,
    top_k: int | None = None,
    auto_filter: bool = True,
    device_types: list[str] | None = None,
) -> list[NodeWithScore]:
    """
    Retrieve the most relevant chunks for a question.

    This is the core retrieval function. It:
    1. Loads the index (cached after first call)
    2. Detects device types from the question (if auto_filter=True)
    3. Creates a retriever with metadata filters
    4. Over-fetches candidates for reranking (if enabled)
    5. Embeds your question and finds similar chunks
    6. Falls back to unfiltered search if filtered results have low scores
    7. Reranks results with cross-encoder (if enabled)
    8. Returns chunks sorted by relevance (highest score first)

    Args:
        question: The user's question
        top_k: Number of chunks to retrieve (default from settings.rag.top_k)
        auto_filter: If True, automatically detect device types and filter.
            Set to False to search all documents regardless of question content.
        device_types: Explicit list of device types to filter by. If provided,
            these are used instead of auto-detection. Useful for workflows
            that know which devices to query (e.g., from a house profile).

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

        # With explicit device types (for workflows)
        >>> results = retrieve("winter maintenance", device_types=["furnace", "hrv"])
    """
    # Use settings default if not specified
    if top_k is None:
        top_k = settings.rag.top_k

    # Get the cached index
    index = get_index()

    # Over-fetch candidates when reranking is enabled
    # Reranking works best with more candidates to choose from
    fetch_k = top_k * 3 if settings.rag.rerank_enabled else top_k

    # Determine device types for filtering
    # Priority: explicit device_types > auto_filter > no filtering
    metadata_filters = None
    effective_device_types: list[str] = []

    if device_types:
        # Use explicitly provided device types (e.g., from house profile)
        effective_device_types = device_types
        metadata_filters = build_metadata_filters(effective_device_types)
        logger.info(f"Using explicit device types: {effective_device_types}")
    elif auto_filter:
        # Auto-detect device types from the question
        effective_device_types = detect_device_types(question)
        metadata_filters = build_metadata_filters(effective_device_types)
        if metadata_filters:
            logger.info(f"Auto-detected device types: {effective_device_types}")

    # Create a retriever with optional metadata filters
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=fetch_k,  # Over-fetch for reranking
        filters=metadata_filters,
    )

    # Retrieve with filters
    results = retriever.retrieve(question)

    # Hybrid fallback: If filtered results have low scores, try unfiltered
    # This handles cases where the device detection was too narrow
    if metadata_filters and _should_fallback_to_unfiltered(results):
        logger.info(
            f"Filtered results have low scores (top={_get_top_score(results):.3f}). "
            "Falling back to unfiltered search."
        )
        unfiltered_retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=fetch_k,  # Over-fetch for reranking
            filters=None,
        )
        results = unfiltered_retriever.retrieve(question)

    # Rerank results with cross-encoder (if enabled)
    results = rerank_nodes(results, question)

    # Log retrieval results
    _log_retrieval_results(results)

    return results


def _get_top_score(results: list[NodeWithScore]) -> float:
    """Get the top score from results, or 0.0 if empty."""
    if not results:
        return 0.0
    top_score = results[0].score
    return top_score if top_score is not None else 0.0


def _should_fallback_to_unfiltered(results: list[NodeWithScore]) -> bool:
    """
    Determine if we should fall back to unfiltered search.

    Falls back if:
    - No results were returned, OR
    - Top result score is below the minimum relevance threshold

    This ensures that overly aggressive filtering doesn't hurt retrieval quality.
    """
    if not results:
        return True

    top_score = _get_top_score(results)
    # Use the same threshold as the "insufficient evidence" check
    return top_score < settings.rag.min_relevance_score


def _log_retrieval_results(results: list[NodeWithScore]) -> None:
    """Log information about retrieval results for debugging."""
    if results:
        scores = [r.score for r in results if r.score is not None]
        if scores:
            sources = {r.node.metadata.get("device_type", "unknown") for r in results}
            logger.info(
                f"Retrieved {len(results)} chunks from {sources}. "
                f"Scores: max={max(scores):.3f}, min={min(scores):.3f}"
            )
    else:
        logger.warning("No chunks retrieved!")


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
