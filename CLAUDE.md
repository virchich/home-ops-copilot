# CLAUDE.md - Project Context for AI Assistants

> This file provides stable context for Claude (or any LLM) working on this project.
> For current status and progress, check `TODO.md`.

## Project Overview

**Name**: Home Ops Copilot
**Purpose**: A RAG-powered assistant for home maintenance, troubleshooting, and parts management. Ingests PDFs, manuals, and notes about household systems and provides cited answers with risk assessments.

**Key Principle**: Every answer must include:
1. **Answer** - Short, actionable
2. **Citations** - Source doc + section/page if possible
3. **Risk level** - LOW / MED / HIGH
4. If HIGH risk → recommend calling a licensed professional

## Tech Stack

- **Language**: Python 3.13
- **Package Manager**: uv (not pip)
- **API**: FastAPI
- **RAG**: LlamaIndex
- **Evaluation**: Ragas

## Key Files

| File | Purpose |
|------|---------|
| `TODO.md` | Current status, weekly goals, session notes |
| `Makefile` | All commands (`make help` to list) |
| `app/core/config.py` | Centralized settings (pydantic-settings) |
| `app/rag/models.py` | Shared Pydantic models |
| `pyproject.toml` | Dependencies |

## Git Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

**Rules**:
- Lowercase, no period at end
- Imperative mood ("add" not "added")
- Keep under 72 characters

## Coding Conventions

- Type hints everywhere
- Pydantic models for structured data
- Config in `app/core/config.py` (use nested settings: `settings.rag.top_k`)
- Shared models in `app/rag/models.py`
- One module per concern

## Safety Rules (Critical)

These rules are non-negotiable:

1. **HIGH risk → always recommend professional** (electrician, plumber, HVAC tech)
2. **Never hallucinate citations** - only cite retrieved documents
3. **Return "insufficient evidence"** when retrieval is poor
4. **No step-by-step instructions** for gas/electrical/structural work

## Guidelines for AI Assistants

**Do**:
- Check `TODO.md` first for current status
- Run `make help` to see available commands
- Run tests after changes (`make test`)
- Use `uv add` for dependencies (not pip)
- Keep changes focused and incremental

**Don't**:
- Add cloud dependencies unless requested
- Add features outside current week's scope
- Skip evaluation when making RAG changes
- Over-engineer - keep it local-first and simple

## Questions to Ask

If unclear, ask before proceeding:
- Which documents are in scope?
- What's the expected behavior?
- Which approach do you prefer?
