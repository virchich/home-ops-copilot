"""Document ingestion pipeline for Home Ops Copilot.

This module implements the extract → chunk → persist pipeline:
1. EXTRACT: Load PDFs from data/raw_docs/ and extract text
2. CHUNK: Split documents into smaller pieces (~512 tokens)
3. PERSIST: Create embeddings and save to a vector index

Run with: python -m app.rag.ingest

Key Concepts:
- Document: A full PDF file with its text and metadata
- Node: A chunk of a document (what actually gets indexed)
- Index: The searchable collection of all nodes with their embeddings
- Embedding: A vector (list of numbers) representing the meaning of text
"""

import json
import logging
from pathlib import Path
from typing import cast

from llama_index.core import (
    Document,
    Settings,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding

from app.core.config import settings
from app.rag.schema import DocumentMetadata, MetadataFile

# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths
RAW_DOCS_DIR = Path("data/raw_docs")
METADATA_FILE = Path("data/metadata.json")
INDEX_DIR = Path("data/indexes")

# Chunking settings
CHUNK_SIZE = 512  # tokens per chunk (sweet spot for most use cases)
CHUNK_OVERLAP = 50  # tokens of overlap between chunks (preserves context)

# Set up logging so we can see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# STEP 1: LOAD METADATA
# =============================================================================
# The metadata tells us about each document: device type, manufacturer, etc.
# We'll attach this to each document so it flows through to the chunks.


def load_metadata() -> dict[str, DocumentMetadata]:
    """
    Load document metadata from metadata.json.

    Returns:
        Dictionary mapping file_name -> DocumentMetadata
        This makes it easy to look up metadata when loading each PDF.
    """
    logger.info(f"Loading metadata from {METADATA_FILE}")

    if not METADATA_FILE.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {METADATA_FILE}\n"
            "Create data/metadata.json with your document metadata."
        )

    # Load and validate with Pydantic
    with open(METADATA_FILE) as f:
        data = json.load(f)

    metadata_file = MetadataFile(**data)  # Pydantic validates the structure

    # Convert to dict for easy lookup by filename
    metadata_dict = {doc.file_name: doc for doc in metadata_file.documents}

    logger.info(f"Loaded metadata for {len(metadata_dict)} documents")
    return metadata_dict


# =============================================================================
# STEP 2: LOAD DOCUMENTS (EXTRACT)
# =============================================================================
# This is the "Extract" step - we're extracting text from PDFs.
# LlamaIndex's SimpleDirectoryReader handles the PDF parsing for us.


def load_documents(metadata_dict: dict[str, DocumentMetadata]) -> list[Document]:
    """
    Load PDF documents and attach metadata to each.

    This uses pypdf under the hood to extract text from PDFs.
    Each PDF becomes a LlamaIndex Document with:
    - text: The extracted text content
    - metadata: Our custom metadata (device_type, manufacturer, etc.)

    Args:
        metadata_dict: Mapping of filename -> DocumentMetadata

    Returns:
        List of LlamaIndex Document objects
    """
    logger.info(f"Loading documents from {RAW_DOCS_DIR}")

    if not RAW_DOCS_DIR.exists():
        raise FileNotFoundError(f"Raw docs directory not found: {RAW_DOCS_DIR}")

    documents = []
    pdf_files = list(RAW_DOCS_DIR.glob("*.pdf"))

    if not pdf_files:
        raise ValueError(f"No PDF files found in {RAW_DOCS_DIR}")

    logger.info(f"Found {len(pdf_files)} PDF files")

    for pdf_path in pdf_files:
        file_name = pdf_path.name

        # Get metadata for this file (if it exists)
        if file_name not in metadata_dict:
            logger.warning(f"No metadata found for {file_name}, skipping")
            continue

        meta = metadata_dict[file_name]

        # Extract text from PDF using pypdf
        # LlamaIndex provides a SimpleDirectoryReader, but we'll do it manually
        # for more control and to show you what's happening
        try:
            text = extract_text_from_pdf(pdf_path)
        except Exception as e:
            logger.error(f"Failed to extract text from {file_name}: {e}")
            continue

        if not text.strip():
            logger.warning(f"No text extracted from {file_name}, skipping")
            continue

        # Create LlamaIndex Document with our metadata
        # The metadata dict will be attached to every chunk (node) later
        doc = Document(
            text=text,
            metadata={
                "file_name": meta.file_name,
                "device_type": meta.device_type.value,
                "device_name": meta.device_name,
                "manufacturer": meta.manufacturer,
                "doc_type": meta.doc_type.value,
                "location": meta.location.value,
                "tags": ", ".join(meta.tags),  # Store as string for filtering
                "description": meta.description or "",
            },
        )
        documents.append(doc)
        logger.info(f"Loaded: {file_name} ({len(text):,} chars)")

    logger.info(f"Successfully loaded {len(documents)} documents")
    return documents


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract text from a PDF file.

    Tries pypdf first (faster), falls back to pdfplumber (more robust)
    if pypdf fails due to font encoding or other issues.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Extracted text as a single string
    """
    # Try pypdf first - it's faster for simple PDFs
    try:
        return _extract_with_pypdf(pdf_path)
    except Exception as e:
        logger.warning(f"pypdf failed for {pdf_path.name}: {e}, trying pdfplumber...")

    # Fall back to pdfplumber - handles complex fonts better
    return _extract_with_pdfplumber(pdf_path)


def _extract_with_pypdf(pdf_path: Path) -> str:
    """Extract text using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    text_parts = []

    for page_num, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()
        if page_text:
            text_parts.append(f"\n[Page {page_num}]\n{page_text}")

    return "\n".join(text_parts)


def _extract_with_pdfplumber(pdf_path: Path) -> str:
    """Extract text using pdfplumber (more robust for complex PDFs)."""
    import pdfplumber

    text_parts = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"\n[Page {page_num}]\n{page_text}")

    return "\n".join(text_parts)


# =============================================================================
# STEP 3: BUILD INDEX (CHUNK + EMBED + PERSIST)
# =============================================================================
# This is where the magic happens:
# 1. Split documents into chunks (nodes)
# 2. Create embeddings for each chunk
# 3. Store in a vector index


def build_index(documents: list[Document]) -> VectorStoreIndex:
    """
    Build a vector index from documents.

    Process:
    1. Split each document into chunks (~512 tokens each)
    2. For each chunk, call OpenAI to get an embedding vector
    3. Store chunks + vectors in the index

    The index enables semantic search: given a question, find the
    most similar chunks based on embedding similarity.

    Args:
        documents: List of LlamaIndex Document objects

    Returns:
        VectorStoreIndex ready for querying
    """
    logger.info("Building vector index...")

    # Configure the embedding model
    # This is what converts text -> vectors
    embed_model = OpenAIEmbedding(
        model="text-embedding-3-small",  # Good balance of quality and cost
        api_key=settings.openai_api_key,
    )

    # Configure the text splitter (chunker)
    # SentenceSplitter tries to split at sentence boundaries
    # This keeps chunks more coherent than splitting mid-sentence
    node_parser = SentenceSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    # Set global settings for LlamaIndex
    # These will be used by VectorStoreIndex.from_documents()
    Settings.embed_model = embed_model
    Settings.node_parser = node_parser

    # Build the index
    # This does a LOT under the hood:
    # 1. Splits documents into nodes (chunks)
    # 2. Calls OpenAI API to get embeddings for each chunk
    # 3. Stores everything in an in-memory vector store
    logger.info(f"Processing {len(documents)} documents...")
    logger.info(f"Chunk size: {CHUNK_SIZE} tokens, overlap: {CHUNK_OVERLAP} tokens")

    index = VectorStoreIndex.from_documents(
        documents,
        show_progress=True,  # Show progress bar
    )

    # Count how many chunks (nodes) were created
    num_nodes = len(index.docstore.docs)
    logger.info(f"Created {num_nodes} chunks (nodes) from {len(documents)} documents")

    return index


# =============================================================================
# STEP 4: PERSIST INDEX
# =============================================================================
# Save the index to disk so we don't have to rebuild it every time.
# This saves the embeddings + text + metadata.


def persist_index(index: VectorStoreIndex) -> None:
    """
    Save the index to disk.

    Creates files in data/indexes/:
    - docstore.json: The text chunks and their metadata
    - index_store.json: Index structure
    - vector_store.json: The embedding vectors

    Next time, we can load this instead of rebuilding from scratch.
    """
    logger.info(f"Persisting index to {INDEX_DIR}")

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=str(INDEX_DIR))

    logger.info(f"Index saved to {INDEX_DIR}")


def load_existing_index() -> VectorStoreIndex | None:
    """
    Load an existing index from disk if it exists.

    Returns:
        VectorStoreIndex if found, None otherwise
    """
    if not INDEX_DIR.exists():
        return None

    try:
        logger.info(f"Loading existing index from {INDEX_DIR}")

        # Need to configure embedding model before loading
        embed_model = OpenAIEmbedding(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key,
        )
        Settings.embed_model = embed_model

        storage_context = StorageContext.from_defaults(persist_dir=str(INDEX_DIR))
        index = cast(VectorStoreIndex, load_index_from_storage(storage_context))

        logger.info("Existing index loaded successfully")
        return index
    except Exception as e:
        logger.warning(f"Could not load existing index: {e}")
        return None


# =============================================================================
# MAIN PIPELINE
# =============================================================================


def run_ingestion(force_rebuild: bool = False) -> VectorStoreIndex:
    """
    Run the full ingestion pipeline.

    Args:
        force_rebuild: If True, rebuild index even if one exists

    Returns:
        The vector index (either loaded or newly built)
    """
    logger.info("=" * 60)
    logger.info("Starting ingestion pipeline")
    logger.info("=" * 60)

    # Try to load existing index (unless force rebuild)
    if not force_rebuild:
        existing_index = load_existing_index()
        if existing_index is not None:
            logger.info("Using existing index. Use --rebuild to force rebuild.")
            return existing_index

    # Step 1: Load metadata
    metadata_dict = load_metadata()

    # Step 2: Load documents
    documents = load_documents(metadata_dict)

    if not documents:
        raise ValueError("No documents were loaded!")

    # Step 3: Build index (chunk + embed)
    index = build_index(documents)

    # Step 4: Persist to disk
    persist_index(index)

    logger.info("=" * 60)
    logger.info("Ingestion complete!")
    logger.info("=" * 60)

    return index


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest documents into vector index")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuild index even if one exists",
    )
    args = parser.parse_args()

    run_ingestion(force_rebuild=args.rebuild)
