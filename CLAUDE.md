# CLAUDE.md - Project Context for AI Assistants

> This file provides context for Claude (or any LLM) when working on this project. Read this first before making changes.

## Project Overview

**Name**: Home Ops Copilot
**Purpose**: A RAG-powered assistant for home maintenance, troubleshooting, and parts management. It ingests PDFs, manuals, receipts, and notes about household systems and provides cited answers with risk assessments.

**Key Principle**: Every answer must include:
1. **Answer** - Short, actionable
2. **Citations** - Source doc + section/page if possible
3. **Risk level** - LOW / MED / HIGH
4. If HIGH risk → stop and recommend calling a licensed professional

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.13 | Core language |
| Package Manager | uv | Fast dependency management + venv |
| API | FastAPI + Uvicorn | REST API and potential local UI |
| RAG | LlamaIndex | Document ingestion, chunking, retrieval, citations |
| Workflows | LangGraph | Agentic control flow for multi-step tasks |
| Evaluation | Ragas | Offline eval metrics for RAG quality |
| Observability | Langfuse | Tracing, cost/latency monitoring, debugging |
| Optional | promptfoo (Node CLI) | Quick eval matrix / red-teaming |

## Repository Structure

```
app/
├── main.py                 # FastAPI entrypoint
├── api/                    # Routes
├── core/                   # Config, logging, settings
├── rag/
│   ├── ingest.py          # Load docs, chunk, index
│   ├── index.py           # Build/load index
│   └── query.py           # RAG query engine w/ citations
├── workflows/
│   ├── maintenance.py     # Seasonal maintenance planner
│   ├── troubleshoot.py    # Troubleshooting tree
│   └── parts.py           # Parts & consumables helper
└── observability/
    └── langfuse.py        # Trace helpers / decorators

data/
├── raw_docs/              # PDFs, receipts, notes (input)
├── processed/             # Extracted text + metadata JSON
└── indexes/               # Persisted vector index

eval/
├── golden_questions.jsonl # 50 → 100 questions over time
├── run_ragas.py           # Runs metrics + saves report
└── reports/               # JSON/CSV results

scripts/
├── dev_ingest.sh
└── dev_run_api.sh

README.md
TODO.md                    # Progress tracking (check this for current status)
CLAUDE.md                  # This file
```

## Architecture

### Data Flow

```
[PDFs/Notes/Receipts]
    → Ingest (extract text + metadata)
    → Chunk (split by sections/headings)
    → Vector Index (persist locally)

[User Question]
    → Retrieve (vector search + metadata filter)
    → Rerank (optional)
    → Generate (answer + citations + risk level)
    → Return structured response
```

### Three Core Workflows (LangGraph)

1. **Seasonal Maintenance Planner**
   - Input: house profile + season
   - Output: Apple Notes friendly checklist

2. **Troubleshooting Tree**
   - Input: symptoms + constraints
   - Output: diagnostic steps with STOP rules for high-risk situations

3. **Parts & Consumables Helper**
   - Input: "Which filter do I need?"
   - Output: exact part + where used + replacement cadence

## Git Conventions

### Conventional Commits

All commits MUST follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, semicolons, etc.)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, config, etc.)

**Examples:**
```bash
feat(rag): add query function with instructor for structured outputs
fix(eval): handle empty citations in format metrics
docs: update README with setup instructions
chore: add openai and pydantic-settings dependencies
```

**Rules:**
- Use lowercase for type and description
- No period at the end of the description
- Keep description under 72 characters
- Use imperative mood ("add" not "added")
- Prefer multiple small commits over one large commit

## Coding Conventions

### Python Style
- Use type hints everywhere
- Prefer dataclasses or Pydantic models for structured data
- Keep functions focused and small
- Use meaningful variable names

### File Organization
- One module per concern
- Keep imports at top, organized: stdlib → third-party → local
- Config in `app/core/` not scattered

### API Design
- RESTful endpoints
- Consistent response format:
  ```python
  {
      "answer": str,
      "citations": List[Citation],
      "risk_level": "LOW" | "MED" | "HIGH",
      "metadata": dict
  }
  ```

### Error Handling
- Return "insufficient evidence" when retrieval is poor
- Never hallucinate citations
- HIGH risk → always recommend professional

### Testing & Evaluation
- Golden set questions are the primary quality metric
- Ragas metrics for retrieval quality
- Format tests for JSON validity in workflows

## Current Status

**Check `TODO.md` for current progress and session notes.**

As of 2025-01-07: Project initialized, ready to begin Week 1.

## Common Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Add a dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>

# Sync dependencies (install from pyproject.toml)
uv sync

# Start development server
uv run uvicorn app.main:app --reload

# Run ingestion pipeline
uv run python -m app.rag.ingest

# Run evaluation
uv run python -m eval.run_ragas

# Run tests (when added)
uv run pytest
```

## Dependencies to Install

**Always use `uv add` to install dependencies** (not pip).

```bash
# Core
uv add fastapi uvicorn
uv add llama-index
uv add langgraph
uv add ragas
uv add langfuse

# Document processing
uv add pypdf2  # or pdfplumber
uv add python-multipart

# Dev tools
uv add --dev pre-commit pytest ruff
```

## Important Notes for AI Assistants

1. **Always check TODO.md first** - It has the current status and session notes
2. **Eval-first mindset** - Changes should be measurable via the golden set
3. **Local-first** - Don't over-engineer; keep persistence simple
4. **Safety critical** - HIGH risk topics must always recommend professionals
5. **Citations required** - Every answer needs source attribution
6. **Keep it boring** - Use proven patterns, ship incrementally

## What NOT to Do

- Don't add cloud dependencies unless explicitly requested
- Don't hallucinate citations or invent source documents
- Don't provide step-by-step instructions for gas/electrical work
- Don't add features not in the current week's scope
- Don't skip the evaluation step when making RAG changes

## Questions to Ask the User

If unclear about any of these, ask before proceeding:
- Which documents are in scope for ingestion?
- What's the house profile (for personalized workflows)?
- Which LLM provider to use (OpenAI, Anthropic, local)?
