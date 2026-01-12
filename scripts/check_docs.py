#!/usr/bin/env python3
"""Check for PDFs missing from metadata.json.

Run with: python -m scripts.check_docs
Or: make check-docs
"""

import json
import sys
from pathlib import Path

RAW_DOCS_DIR = Path("data/raw_docs")
METADATA_FILE = Path("data/metadata.json")


def main() -> int:
    """Check for missing metadata entries and return exit code."""

    # Get all PDFs in raw_docs
    if not RAW_DOCS_DIR.exists():
        print(f"Directory not found: {RAW_DOCS_DIR}")
        return 1

    pdf_files = {f.name for f in RAW_DOCS_DIR.glob("*.pdf")}

    if not pdf_files:
        print("No PDF files found in data/raw_docs/")
        return 0

    # Get all files listed in metadata.json
    if not METADATA_FILE.exists():
        print(f"Metadata file not found: {METADATA_FILE}")
        print(f"All {len(pdf_files)} PDFs are missing metadata!")
        return 1

    with open(METADATA_FILE) as f:
        data = json.load(f)

    metadata_files = {doc["file_name"] for doc in data.get("documents", [])}

    # Find differences
    missing_metadata = pdf_files - metadata_files
    orphaned_metadata = metadata_files - pdf_files

    # Report results
    all_good = True

    if missing_metadata:
        all_good = False
        print("PDFs missing from metadata.json:")
        for filename in sorted(missing_metadata):
            print(f"  - {filename}")
        print()

    if orphaned_metadata:
        all_good = False
        print("Metadata entries with no PDF file:")
        for filename in sorted(orphaned_metadata):
            print(f"  - {filename}")
        print()

    if all_good:
        print(f"All {len(pdf_files)} PDFs have metadata entries.")
        return 0
    else:
        print(f"Summary: {len(pdf_files)} PDFs, {len(metadata_files)} metadata entries")
        if missing_metadata:
            print(f"  {len(missing_metadata)} PDF(s) need metadata")
        if orphaned_metadata:
            print(f"  {len(orphaned_metadata)} orphaned metadata entry(ies)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
