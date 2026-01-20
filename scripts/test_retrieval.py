#!/usr/bin/env python3
"""Test script to verify retrieval is working.

Run with: uv run python scripts/test_retrieval.py

This script tests the retrieval module by:
1. Loading the vector index
2. Running a few test queries
3. Displaying the results with scores and metadata
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.retriever import format_contexts_for_llm, get_node_metadata, retrieve


def test_query(question: str) -> None:
    """Run a test query and display results."""
    print(f"\n{'=' * 70}")
    print(f"QUESTION: {question}")
    print("=" * 70)

    results = retrieve(question, top_k=3)

    if not results:
        print("❌ No results found!")
        return

    print(f"\n✅ Found {len(results)} chunks:\n")

    for i, result in enumerate(results, 1):
        metadata = get_node_metadata(result)
        print(f"--- Result {i} ---")
        print(f"  Score:    {metadata['score']:.4f}")
        print(f"  Source:   {metadata['file_name']}")
        print(f"  Device:   {metadata['device_name']}")
        print(f"  Type:     {metadata['device_type']}")
        print(f"  Text preview: {result.node.get_content()[:200]}...")
        print()

    # Also show formatted context for LLM
    print("\n--- Formatted for LLM ---")
    print(format_contexts_for_llm(results)[:500] + "...")


def main() -> None:
    """Run test queries."""
    print("Testing retrieval module...")
    print("This will load the index and run a few test queries.\n")

    # Test queries covering different document types
    test_queries = [
        "How do I change the furnace filter?",
        "What is the model number of my thermostat?",
        "How often should I clean the HRV?",
        "What temperature should I set my water heater to?",
    ]

    for question in test_queries:
        test_query(question)

    print("\n" + "=" * 70)
    print("✅ Retrieval test complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
