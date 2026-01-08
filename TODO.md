# Home Ops Copilot - Project TODO

> **Purpose**: Track progress and notes for the Home Ops Copilot project. This file serves as the single source of truth for any LLM agent working on this project.

## Current Status

**Phase**: Week 1 Complete
**Last Updated**: 2026-01-08
**Current Focus**: Ready for Week 2 - Ingestion pipeline

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

- [ ] Collect 20–50 docs into `data/raw_docs/`
- [ ] Create metadata schema (device, model, room, purchase date, tags, doc_type)
- [ ] Implement extract→chunk→persist pipeline
- [ ] Persist index locally (don't over-engineer: local first)

**Deliverable**: `python -m app.rag.ingest` builds an index from your folder.

---

## Week 3 — RAG chat v1 (citations working)

**Goal**: Get basic RAG working with citations.

- [ ] Implement query endpoint: `POST /ask {question}`
- [ ] Return: answer + top_k sources (citations)
- [ ] Add "insufficient evidence" fallback (no sources → say you can't confirm)

**Deliverable**: You can ask 10 questions and get cited answers.

---

## Week 4 — Retrieval quality pass (most important week)

**Goal**: Improve retrieval quality significantly.

- [ ] Improve chunking (split by headings/sections if possible)
- [ ] Add metadata filtering (e.g., only furnace docs when question mentions furnace)
- [ ] Add basic reranking (if available in your setup)
- [ ] Run golden set again + track lift with Ragas

**Deliverable**: Measurable improvement on retrieval/grounding.

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
2. [ ] Ingest: load a single PDF manual → chunk → index → query *(Week 2)*
3. [ ] Return citations in the response (even if ugly at first) *(Week 3)*
4. [x] Build `golden_questions.jsonl` (50 Qs) + `run_eval.py`
5. [ ] Add Langfuse trace wrapper around `/ask` endpoint *(Week 8)*

---

## Session Notes

> Use this section to leave notes for future sessions. Include what was accomplished, blockers, and next steps.

### Session Log

<!-- Add entries in reverse chronological order -->

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
