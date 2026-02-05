# Home Ops Copilot - Project TODO

> **Purpose**: Track progress and notes for the Home Ops Copilot project. This file serves as the single source of truth for any LLM agent working on this project.

> **Learning Mode**: The maintainer is learning RAG systems through this project. LLM sessions should be **descriptive and elaborative** - explain concepts in detail, walk through code step-by-step, and use diagrams/tables where helpful. Prioritize teaching over speed.

## Current Status

**Phase**: Week 5 In Progress
**Last Updated**: 2026-02-05
**Current Focus**: Week 5 - Seasonal Maintenance Planner (LangGraph) - Phase 2 Complete

---

## Week 1 — Setup + eval-first baseline

**Goal**: Get the foundation in place with an eval-first approach.

- [x] Create repo + venv (uv) + pre-commit
- [x] FastAPI "hello world" endpoint (`/health`)
- [x] Create golden set: 50 real questions (furnace, HRV, filters, windows condensation, etc.)
- [x] Write a minimal eval runner that calls your API and saves outputs
- [x] Add `/ask` endpoint with structured LLM responses (instructor + Pydantic)
- [x] Add config module (pydantic-settings)
- [x] Add Makefile for project orchestration
- [x] Add unit tests (71 tests covering config, API, eval helpers)

**Deliverable**: `make eval` produces a baseline report with format metrics. ✅

---

## Week 2 — Ingestion pipeline v1

**Goal**: Build the document ingestion pipeline.

- [x] Collect 20–50 docs into `data/raw_docs/`
- [x] Create metadata schema (device, model, room, purchase date, tags, doc_type)
- [x] Implement extract→chunk→persist pipeline
- [x] Persist index locally (don't over-engineer: local first)

**Deliverable**: `make ingest-rebuild` builds an index from your folder. ✅

---

## Week 3 — RAG chat v1 (citations working)

**Goal**: Get basic RAG working with citations.

- [x] Implement query endpoint: `POST /ask {question}`
- [x] Return: answer + top_k sources (citations)
- [x] Add "insufficient evidence" fallback (no sources → say you can't confirm)
- [x] Validate citations against retrieved sources (filter hallucinations)

**Deliverable**: You can ask 10 questions and get cited answers. ✅

---

## Week 4 — Retrieval quality pass (most important week)

**Goal**: Improve retrieval quality significantly.

- [x] Improve chunking (split by headings/sections if possible)
- [x] Add metadata filtering (e.g., only furnace docs when question mentions furnace)
- [x] Add basic reranking (if available in your setup)
- [x] Run golden set again + track lift with Ragas

**Deliverable**: Measurable improvement on retrieval/grounding. ✅

---

## Week 4.5 — UI: Chat Interface (React + Node.js)

**Goal**: Build a usable chat interface for the RAG system.

- [x] Set up React + Node.js frontend project (Vite or Next.js)
- [x] Chat interface with question input and response display
- [x] Display answer, citations (with source links), and risk level badge
- [x] Show retrieved chunks (expandable/collapsible)
- [x] Connect to existing FastAPI `/ask` endpoint

**Deliverable**: Can ask questions and see cited answers in a browser.

---

## Week 5 — Workflow #1: Seasonal maintenance planner (LangGraph)

**Goal**: First LangGraph workflow for maintenance planning.

- [ ] Input: house profile + season
- [ ] Steps: retrieve relevant docs → generate checklist (STRICT JSON) → render markdown
- [ ] Output: Apple Notes friendly checklist

**Deliverable**: "Winter maintenance plan" is generated cleanly.

---

## Week 6 — Workflow #2: Troubleshooting tree (guardrails)

**Goal**: Guided troubleshooting with safety guardrails.

- [ ] Intake: ask 3–6 targeted questions (symptom + constraints)
- [ ] Retrieve manuals → produce diagnostic steps → STOP rules
- [ ] High-risk rules: gas/electrical → safety-first, recommend pro

**Deliverable**: One full troubleshooting flow end-to-end.

---

## Week 7 — Workflow #3: Parts & consumables helper

**Goal**: Help identify correct replacement parts.

- [ ] Extract filter sizes/part numbers/intervals from docs (+ your notes)
- [ ] Output: exact item + where it's used + replacement cadence
- [ ] Uncertainty behavior: missing model → ask follow-ups

**Deliverable**: "Which filter do I buy?" works reliably.

---

## Week 8 — Observability (Langfuse tracing)

**Goal**: Full observability for debugging and optimization.

- [ ] Trace: ingestion, retrieval results, generation, workflow steps
- [ ] Log: latency, token usage, retrieval hit count, failures
- [ ] Add tags: device type, workflow name, risk level

**Deliverable**: You can debug failures via traces, not guesswork.

---

## Week 9 — Evaluation v2 + regression gates

**Goal**: Production-grade evaluation with CI gates.

- [ ] Expand golden set to 100 questions (include tricky/edge cases)
- [ ] Ragas metrics thresholds (block merges on regression)
- [ ] Add format tests: citations present, JSON valid for workflows

**Deliverable**: CI runs evals and blocks regressions.

---

## Week 10 — Red-teaming + safety tightening

**Goal**: Ensure safe behavior under adversarial inputs.

- [ ] Test prompts that try to force unsafe DIY advice
- [ ] Ensure the system refuses high-risk step-by-step and escalates to professionals
- [ ] "Overconfidence" test: must cite or must say uncertain

**Deliverable**: Safer behavior under adversarial questions.

---

## Week 11 — Polish + exports

**Goal**: Make it actually usable day-to-day.

- [ ] Export outputs as clean Markdown blocks (Apple Notes copy/paste)
- [ ] Optional: generate .ics reminders for seasonal tasks
- [ ] Add "house profile" file to personalize outputs

**Deliverable**: You actually use it weekly.

---

## Week 12 — Demo + write-up

**Goal**: Portfolio-ready capstone.

- [ ] 3–5 min demo video: RAG answer + 3 workflows + eval dashboard + trace debug
- [ ] README: architecture, evaluation approach, known limitations, next steps

**Deliverable**: Portfolio-ready capstone that shows production thinking.

---

## Quick Start Tickets (High Leverage)

These are the first things to tackle in Week 1:

1. [x] FastAPI skeleton + `/ask` endpoint stub
2. [x] Ingest: load a single PDF manual → chunk → index → query *(Week 2)*
3. [x] Return citations in the response (even if ugly at first) *(Week 3)*
4. [x] Build `golden_questions.jsonl` (50 Qs) + `run_eval.py`
5. [ ] Add Langfuse trace wrapper around `/ask` endpoint *(Week 8)*

---

## Session Notes

> Use this section to leave notes for future sessions. Include what was accomplished, blockers, and next steps.

### Session Log

<!-- Add entries in reverse chronological order -->

**2026-02-05** - Week 5 Phase 1 & 2 Complete
- **Phase 1: LangGraph setup**
  - Added `langgraph>=1.0.5` dependency
  - Created `app/workflows/` package for LangGraph workflows
  - Models: `Season`, `ClimateZone`, `HouseType`, `InstalledSystem`, `HouseProfile`
  - Created `data/house_profile.json` with 7 systems (all installed 2018)
  - Decision: LangGraph chosen over PydanticGraph
- **Phase 2: Workflow skeleton**
  - Added workflow state models: `MaintenancePlanState`, `ChecklistItem`, `RetrievedChunk`
  - Added API models: `MaintenancePlanRequest`, `MaintenancePlanResponse`
  - Created `app/workflows/maintenance_planner.py` with LangGraph workflow
  - Graph structure: START → retrieve_docs → generate_checklist → render_markdown → END
  - All nodes are stubs (pass-through) - real logic in Phase 3
  - Added `POST /maintenance-plan` endpoint to FastAPI
  - Tested all 4 seasons via endpoint
- Key files: `app/workflows/models.py`, `app/workflows/maintenance_planner.py`, `app/main.py`
- Next: Phase 3 - Node Implementation (RAG retrieval, LLM generation, markdown rendering)

**2026-01-27** - Week 4 Complete
- **Section-aware chunking**: Added heading detection for ALL CAPS patterns in PDFs
  - `_is_section_heading()` detects headings (>80% uppercase, 12-60 chars, ≥2 words)
  - `preprocess_text_with_sections()` converts to markdown `## HEADING` format
  - Exclusion patterns filter noise (HAZARD, WARNING, etc.)
  - Two-stage chunking: `MarkdownNodeParser` → `SentenceSplitter`
- **Metadata filtering**: Device type detection from question keywords
  - `detect_device_types()` maps keywords to device_type metadata
  - `build_metadata_filters()` creates OR filters for LlamaIndex
  - Hybrid fallback: if filtered results score low, retry unfiltered
  - Device keywords: furnace, thermostat, hrv, humidifier, water_heater, water_softener, energy_meter
- **Cross-encoder reranking**: Implemented but disabled by default
  - Added `SentenceTransformerRerank` with `cross-encoder/ms-marco-MiniLM-L-6-v2`
  - Config: `rerank_enabled`, `rerank_model`, `rerank_top_n`
  - Over-fetches 3x top_k when enabled for better candidate pool
  - Fixed `_has_sufficient_evidence()` to handle logit scores (-2 threshold)
  - **Finding**: MS-MARCO model hurts quality on technical docs (disabled by default)
- **Eval improvements**:
  - Added cache clearing in `run_eval.py` for consistent results
  - Updated tests for bi-encoder vs cross-encoder score handling
- **Results** (Ragas metrics):
  - Faithfulness: 0.815 → **0.949** (+16% improvement)
  - Answer Relevancy: 0.507 → 0.476 (similar)
  - Context Precision: 0.861 → 0.726 (slight decrease)
- Key files: `app/rag/retriever.py`, `app/rag/extractors.py`, `app/rag/ingest.py`, `app/rag/query.py`, `app/core/config.py`
- Total tests: 195

**2026-01-19** - Week 3 Complete
- **Phase 2**: Integrated retrieval into `/ask` endpoint
  - `query()` now calls `retrieve()` to get relevant chunks from vector index
  - Formats chunks as `[Source N: filename - device]` for LLM context
  - Updated system prompt to instruct citation format
  - Response includes `contexts` field for evaluation
- **Phase 3**: Citation validation and enrichment
  - Added `build_source_mapping()` to map source index → node metadata
  - Added `enrich_citations()` to validate LLM citations against retrieved sources
  - Matching strategies: Source N pattern, file_name - device_name, file_name substring
  - Hallucinated citations (not matching any source) are filtered out
- **Phase 4**: Insufficient evidence fallback
  - Added `min_relevance_score` setting (default: 0.3)
  - Added `_has_sufficient_evidence()` to check top retrieval score
  - Returns fallback response for out-of-scope questions (skips LLM call)
- Test improvements:
  - Refactored unit tests to test behavior over implementation
  - Added error handling tests, citation enrichment tests, fallback tests
  - Added integration test for out-of-scope questions
  - Total tests: 146 (135 unit + 11 integration)
- Key files: `app/rag/query.py`, `app/rag/retriever.py`, `app/core/config.py`

**2026-01-12** - Week 2 Complete
- Added 7 PDF manuals to `data/raw_docs/` (furnace, thermostat, HRV, water heater, water softener, humidifier, energy meter)
- Created Pydantic metadata schema (`app/rag/schema.py`) with device type, location, tags, etc.
- Created `data/metadata.json` with metadata for all 7 documents
- Built ingestion pipeline (`app/rag/ingest.py`) with extract→chunk→persist flow
- Used LlamaIndex with OpenAI `text-embedding-3-small` for embeddings
- Added `pdfplumber` fallback for PDFs that fail with `pypdf` (font encoding issues)
- Created `scripts/check_docs.py` to validate PDFs have metadata entries
- Added Makefile commands: `ingest`, `ingest-rebuild`, `check-docs`
- Pipeline creates 250 chunks from 7 documents (~317K characters)
- Embedding cost: < $0.01

**2026-01-08** - Week 1 Complete
- Created eval runner (`eval/run_eval.py`) with format checks and Ragas metrics
- Added `/ask` endpoint with structured LLM responses using **instructor** library
- Added config module (`app/core/config.py`) with pydantic-settings
- Created query module (`app/rag/query.py`) with OpenAI integration
- Added 5 questions with ground truth to golden set for future Ragas evaluation
- Created Makefile with commands: install, check, test, eval, eval-quick, run, clean, clean-reports
- Added dev dependencies: ruff, mypy, pytest
- Added 71 unit tests for stable components (config, API, eval helpers, format metrics)
- Fixed GPT-5.2 compatibility (max_completion_tokens instead of max_tokens)
- Fixed Ragas deprecated imports and API changes
- Eval runner skips Ragas metrics when no contexts (Week 1 behavior - no retrieval yet)

**2025-01-07** - Project initialized
- Created TODO.md and CLAUDE.md
- Initialized uv project with Python 3.13
- Created .venv with `uv venv`
- Project uses **uv** as package manager (not poetry/pip)
- Added FastAPI + uvicorn, created `app/main.py` with `/health` endpoint
- Created `eval/golden_questions.jsonl` with 50 questions across 9 categories

---

## Decisions Made

> Document key architectural or design decisions here for context.

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-01-07 | Use LlamaIndex for RAG | Good balance of features and simplicity for personal project |
| 2025-01-07 | Use LangGraph for workflows | Explicit control flow over pure agents |
| 2025-01-07 | Local-first persistence | Don't over-engineer; can add cloud later if needed |
| 2025-01-07 | Use uv as package manager | Fast, modern, handles venv + deps in one tool |
| 2026-01-08 | Use instructor for LLM outputs | Pydantic-validated structured outputs, cleaner than manual parsing |
| 2026-01-08 | GPT-5.2 as default model | Access to latest capabilities |
| 2026-01-08 | Makefile for orchestration | Simple, universal, no extra dependencies |
| 2026-01-08 | Custom eval metrics first | Rule-based checks (pro recommendations, safety mentions) work without retrieval |
| 2026-01-12 | pypdf + pdfplumber fallback | pypdf is faster but fails on some fonts; pdfplumber handles edge cases |
| 2026-01-12 | Local file-based vector index | Simple persistence, no database setup needed; can migrate to Postgres/MongoDB later |
| 2026-01-12 | 512 token chunks with 50 overlap | Good balance of precision and context; sentence-aware splitting |
| 2026-01-19 | Validate citations against retrieved sources | Prevents hallucinated citations; only returns citations matching actual sources |
| 2026-01-19 | Insufficient evidence fallback | Skips LLM call when retrieval quality is poor; saves cost and prevents hallucination |
| 2026-01-19 | min_relevance_score = 0.3 | Conservative threshold; can tune based on eval results |
| 2026-01-27 | Section-aware chunking with fallback | Detects ALL CAPS headings; gracefully falls back for docs without clear structure |
| 2026-01-27 | Metadata filtering with hybrid fallback | Filter by device type, but retry unfiltered if scores are low |
| 2026-01-27 | Reranking disabled by default | MS-MARCO cross-encoder hurts quality on technical docs; keep feature for experimentation |

---

## Blockers / Questions

> Track any blockers or open questions here.

- None currently

---

## Resources & References

- LlamaIndex docs: https://docs.llamaindex.ai/
- LangGraph docs: https://langchain-ai.github.io/langgraph/
- Ragas docs: https://docs.ragas.io/
- Langfuse docs: https://langfuse.com/docs
