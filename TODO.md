# Home Ops Copilot - Project TODO

> **Purpose**: Track progress and notes for the Home Ops Copilot project. This file serves as the single source of truth for any LLM agent working on this project.

> **Learning Mode**: The maintainer is learning RAG systems through this project. LLM sessions should be **descriptive and elaborative** - explain concepts in detail, walk through code step-by-step, and use diagrams/tables where helpful. Prioritize teaching over speed.

## Current Status

**Phase**: Week 12 Complete
**Last Updated**: 2026-02-26
**Current Focus**: Week 12 complete — Portfolio polish

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

- [x] Input: house profile + season
- [x] Steps: retrieve relevant docs → generate checklist (STRICT JSON) → render markdown
- [x] Output: Apple Notes friendly checklist

**Deliverable**: "Winter maintenance plan" is generated cleanly. ✅

---

## Week 6 — Workflow #2: Troubleshooting tree (guardrails)

**Goal**: Guided troubleshooting with safety guardrails.

- [x] Intake: hybrid form (device + symptom) → LLM follow-up questions (2-3)
- [x] Retrieve manuals → produce diagnostic steps → STOP rules
- [x] High-risk rules: gas/electrical/CO/structural → safety-first, recommend pro
- [x] Two-invocation LangGraph workflow (intake graph + diagnosis graph)
- [x] Two-layer safety: deterministic keyword matching + LLM risk assessment
- [x] Frontend: stepper/wizard with intake form, follow-up questions, diagnosis display
- [x] Evaluation suite with 6 golden scenarios

**Deliverable**: One full troubleshooting flow end-to-end. ✅

---

## Week 7 — Workflow #3: Parts & consumables helper

**Goal**: Help identify correct replacement parts.

- [x] Extract filter sizes/part numbers/intervals from docs (+ your notes)
- [x] Output: exact item + where it's used + replacement cadence
- [x] Uncertainty behavior: missing model → ask follow-ups
- [x] Single-invocation LangGraph workflow (parse → retrieve → generate → render)
- [x] Confidence levels: CONFIRMED / LIKELY / UNCERTAIN
- [x] Frontend: query form with device filter + results display with confidence badges
- [x] Evaluation suite with 8 golden scenarios

**Deliverable**: "Which filter do I buy?" works reliably. ✅

---

## Week 8 — Observability (Langfuse tracing)

**Goal**: Full observability for debugging and optimization.

- [x] Add Langfuse dependency + `ObservabilitySettings` config with feature flag
- [x] Centralized LLM client (`app/llm/client.py`) — auto-traces when enabled
- [x] `@observe()` wrapper (`app/llm/tracing.py`) — no-op when disabled, zero overhead
- [x] Replace 4 duplicated `get_llm_client()` with centralized import
- [x] Add `@observe()` decorators to 17 functions across 6 files
- [x] Initialize tracing at app startup (`init_tracing()` in main.py)
- [x] Tests: 12 new tests (client + tracing), all 296 unit tests pass
- [x] Graceful fallback when keys missing or langfuse not installed

**Deliverable**: You can debug failures via traces, not guesswork. ✅

---

## Week 9 — Evaluation v2 + regression gates

**Goal**: Production-grade evaluation with CI gates.

- [x] GitHub Actions CI (ruff + mypy + unit tests) — `.github/workflows/ci.yml`
- [x] `make check-ci` target for CI-safe lint checks (no auto-fix)
- [x] Fixed 9 pre-existing mypy errors across 7 files
- [x] Fixed threshold gates in all 4 eval runners with `--threshold-check` flag
- [x] Expand golden set to 100 questions (include tricky/edge cases)
- [x] 65% ground truth coverage (65/100 questions)
- [x] Strengthen workflow evals: realistic troubleshooting answers, device coverage, duplicate detection
- [x] `uncertain_no_part_numbers` invariant in parts eval thresholds
- [x] CI eval gate via `workflow_dispatch` — `.github/workflows/eval.yml` (commented out, uncomment + add secret to enable)

**Deliverable**: CI runs lints/tests and blocks regressions. Eval thresholds prevent quality drift. ✅

---

## Week 10 — Red-teaming + safety tightening

**Goal**: Ensure safe behavior under adversarial inputs.

- [x] Adversarial test suite: 18 scenarios across 4 categories (prompt injection, safety bypass, overconfidence, risk accuracy)
- [x] Standalone adversarial eval runner with 100% pass rate threshold for safety-critical categories
- [x] SSL fix: `truststore` integration for corporate proxy environments (Cisco/Umbrella)
- [x] Langfuse env var bridge: propagate `OBSERVABILITY__*` to native `LANGFUSE_*` env vars
- [x] Disable Langfuse tracing in eval runners (no cost/noise during evals)
- [x] Prompt hardening: anti-injection, anti-hallucination, overconfidence guards in all 4 system prompts
- [x] 33 safety regression unit tests (prompt invariants, safety patterns, golden file integrity)
- [x] Fix GPT-5.2 `max_completion_tokens` — reasoning models need 8000-16000+ (was 500-4000)
- [x] Co-occurrence keyword matching for electrical hazard safety patterns
- [x] Run adversarial eval: **48/48 checks (100%)** ✅
- [x] Run full RAG eval: **100/100 questions, 0 errors, all thresholds pass** ✅

**Deliverable**: Safer behavior under adversarial questions. ✅

---

## Week 11 — Polish + exports

**Goal**: Make it actually usable day-to-day.

- [x] Extract shared `utils/export.ts` with `copyToClipboard()` and `downloadMarkdown()`
- [x] Fix ChatMessage copy to include full Q&A (question + answer + risk + citations)
- [x] Fix PartsResultsDisplay missing error handling on copy
- [x] Fix DiagnosticStepsDisplay missing copy feedback (Copied! indicator)
- [x] Consolidate 5 duplicate copy/export handlers into 2 shared utilities
- [x] Generate .ics calendar reminders for seasonal maintenance tasks
- [x] Write README.md (architecture, setup, evaluation, limitations)
- [ ] ~~Add "house profile" file to personalize outputs~~ (already done in Week 5)

**Deliverable**: You actually use it weekly. ✅

---

## Week 12 — Demo + write-up

**Goal**: Portfolio-ready capstone.

- [ ] 3–5 min demo video: RAG answer + 3 workflows + eval dashboard + trace debug
- [x] README: architecture, evaluation approach, known limitations, next steps
- [x] Fix `pyproject.toml` placeholder description + add authors/keywords/license
- [x] Fix `frontend/package.json` metadata (name, version, description, author)
- [x] Add meta description to `frontend/index.html`
- [x] Document all env vars in `.env.example` (was 3 lines, now comprehensive)
- [x] Add API tags to all 9 endpoints (grouped in Swagger UI)
- [x] Add OpenAPI tag descriptions for Swagger documentation
- [x] Add structured logging to `app/main.py` (request/response logging)
- [x] Pin Docker base images to specific versions (reproducible builds)

**Deliverable**: Portfolio-ready capstone that shows production thinking. ✅

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

**2026-02-26** - Week 12: Portfolio Polish
- **Phase 1: Metadata & Identity**
  - Fixed `pyproject.toml` placeholder description ("Add your description here" → actual description)
  - Added `authors`, `license`, `keywords` fields to pyproject.toml
  - Fixed `frontend/package.json`: name "frontend" → "home-ops-copilot-frontend", version 0.0.0 → 0.1.0
  - Added `description` and `author` fields to package.json
  - Added `<meta name="description">` to `frontend/index.html`
- **Phase 2: .env.example Documentation**
  - Rewrote `.env.example` from 3 sparse lines to comprehensive documented file
  - All config groups covered: Required (API key), LLM, RAG, Paths, Observability, App
  - Every variable has description, default value, and example format
  - References `app/core/config.py` for full settings documentation
- **Phase 3: API Documentation Polish**
  - Added `tags` to all 9 FastAPI endpoints (chat, maintenance, troubleshooting, parts, house-profile, system)
  - Added `openapi_tags` with descriptions to FastAPI app constructor
  - Swagger UI now groups endpoints by feature area with descriptions
- **Phase 4: Structured Logging**
  - Added `logging.basicConfig()` with timestamp format to `app/main.py`
  - Added logger to workflow compilation startup, ask (risk + citation count), maintenance (season + items + sources), troubleshoot/start (session + risk + safety_stop), parts/lookup (query + parts + gaps)
  - Log format: `2026-02-26 10:00:00 INFO [app.main] message`
- **Phase 5: Docker Image Pinning**
  - Backend: `python:3.13-slim` → `python:3.13.5-slim`
  - Frontend build: `node:22-alpine` → `node:22.17-alpine`
  - Frontend serve: `nginx:alpine` → `nginx:1.27-alpine`
- Key files: `pyproject.toml`, `frontend/package.json`, `frontend/index.html`, `.env.example`, `app/main.py`, `Dockerfile.backend`, `frontend/Dockerfile`
- Tests: 359 unit tests passing
- **Week 12 Complete!** Demo video remaining (user will handle separately)

**2026-02-26** - Week 11: Polish + Exports
- **Phase 1: Export DRY + Polish**
  - Created `frontend/src/utils/export.ts` with 3 shared utilities:
    - `copyToClipboard()` — Clipboard API with textarea fallback for older browsers
    - `downloadMarkdown()` — Blob URL download with cleanup
    - `formatMessageAsMarkdown()` — Formats chat Q&A with citations + risk level
  - Updated 5 components to use shared utilities (was 3 different copy patterns, 1 with no error handling):
    - `ChatMessage.tsx` — Now copies full Q&A block (was: answer text only)
    - `DiagnosticStepsDisplay.tsx` — Added "Copied!" feedback, uses shared utils
    - `ChecklistDisplay.tsx` — Uses shared utils
    - `PartsResultsDisplay.tsx` — Added error handling (was: raw `navigator.clipboard.writeText()` with no try/catch)
    - `ChatContext.tsx` — Uses shared `downloadMarkdown()`
  - Eliminated ~100 lines of duplicated copy/export code across components
- **Phase 2: .ics Calendar Reminders**
  - Created `app/workflows/ics_generator.py` — RFC 5545 iCalendar generation without third-party library
    - All-day events staggered by priority (high: day 1, medium: +7d, low: +14d)
    - Proper text escaping, line folding, CRLF endings per spec
    - Categories from device type, iCalendar priority mapping (1/5/9)
    - Season-aware date calculation (next upcoming season start)
  - Added `POST /maintenance-plan/ics` endpoint in `app/main.py`
    - Runs full maintenance workflow, converts checklist to .ics, returns as download
    - Content-Type: `text/calendar`, Content-Disposition attachment
  - Frontend integration:
    - Added `downloadMaintenanceIcs()` to `api/client.ts`
    - Added green "Calendar" button to `ChecklistDisplay.tsx` (with loading state)
    - Wired through `MaintenancePlanPage.tsx` via `onDownloadCalendar` prop
  - 32 unit tests in `tests/test_ics_generator.py` (escaping, folding, dates, events, priorities)
- **Phase 3: README.md**
  - Wrote comprehensive README: what it does, architecture diagram, tech stack, setup instructions
  - Documented evaluation approach (RAG, workflow, adversarial), development workflow, known limitations
- Key files: `frontend/src/utils/export.ts`, `app/workflows/ics_generator.py`, `app/main.py`, `README.md`
- Tests: 280 unit tests passing (32 new ICS tests)
- **Week 11 Complete!** Ready for Week 12 (Demo + write-up)

**2026-02-26** - Week 10: Red-teaming + Safety Tightening
- **Phase 1: Adversarial eval runner** — `eval/adversarial_golden.json` + `eval/run_adversarial_eval.py`
  - 18 scenarios across 4 categories: prompt_injection (3), safety_bypass (4), overconfidence (5), risk_accuracy (4), maintenance (2)
  - Standalone runner routes scenarios to correct workflow (ask, troubleshoot, parts, maintenance)
  - Thresholds: overall_pass_rate ≥ 0.85, safety_critical_pass_rate = 100% (prompt_injection + safety_bypass)
  - Makefile targets: `eval-adversarial`, `eval-adversarial-threshold`, added to `eval-check-all`
- **Infra fixes: SSL + Langfuse + GPT-5.2 token limits**
  - SSL: Diagnosed Cisco SSL inspection proxy causing `SSL_CERTIFICATE_VERIFY_FAILED`. Added `truststore` package + `app/core/ssl_setup.py` to use OS cert store. Wired into all 6 entrypoints.
  - Langfuse env bridge: `OBSERVABILITY__*` config now propagated to native `LANGFUSE_*` env vars at import time (suppresses "initialized without public_key" warning)
  - Disabled Langfuse tracing in all 5 eval runners (`OBSERVABILITY__ENABLED=false` before app imports)
  - GPT-5.2 token fix: `max_completion_tokens` increased from 500-4000 → 8000-16000. Reasoning models split this budget between internal reasoning + visible output; previous limits caused empty responses (all tokens consumed by reasoning).
- **Phase 2: Prompt hardening** — All 4 system prompts strengthened:
  - `query.py`: Added anti-injection paragraph, "do NOT fabricate" rule, unknown topic disclosure (rule 7)
  - `troubleshooter.py`: Strengthened anti-injection wording, added "do NOT fabricate procedures" (rule 6), sparse docs acknowledgment (rule 8)
  - `parts_helper.py`: Added overconfidence guard (rule 10: empty list when docs lack info)
  - `maintenance_planner.py`: Added anti-injection paragraph (was entirely missing), anti-fabrication rules 7-8
- **Phase 3: Safety pattern improvements**
  - Added `co_occurrence_groups` to electrical hazard pattern — when ALL terms in a group appear anywhere in text, safety stop triggers (catches "I smell something burning near my electrical panel")
  - Refined adversarial golden `must_not_contain`: removed "turn off the main" (legitimate safety advice), added "remove the breaker" / "pull the breaker" (actual DIY instruction patterns)
- **Phase 4: Safety regression tests** — `tests/test_safety_regression.py` (33 tests)
  - `TestPromptSafetyInvariants`: All prompts have anti-injection, anti-hallucination, professional recommendation language
  - `TestAdversarialSafetyPatterns`: Deterministic patterns catch adversarial inputs (sulfur smell, CO detector, burning electrical, injection attempts)
  - `TestSafetyKeywordCoverage`: All 5 hazard categories present, ≥3 keywords each, actionable messages, specific trades
  - `TestAdversarialGoldenIntegrity`: Golden file well-formed, valid workflows/categories, ≥15 scenarios, safety-critical scenarios have risk expectations
- **Final eval results:**
  - Adversarial eval: **48/48 checks (100%)** — all 18 scenarios pass
  - Full RAG eval (100 Qs): **0 errors, 88% citations, 100% valid risk, 90.5% HIGH→pro rate** — all thresholds pass
- Key files: `eval/adversarial_golden.json`, `eval/run_adversarial_eval.py`, `app/core/ssl_setup.py`, `app/llm/tracing.py`, `tests/test_safety_regression.py`
- Tests: 327 unit tests, all passing
- **Week 10 Complete!** Ready for Week 11 (Polish + exports)

**2026-02-26** - Week 9: Evaluation v2 + Regression Gates
- **Phase 1: Light CI** — GitHub Actions workflow (`.github/workflows/ci.yml`)
  - Lint job: `make check-ci` (ruff check + ruff format --check + mypy)
  - Test job: `make test-unit` (294 tests, depends on lint passing)
  - Uses `astral-sh/setup-uv@v5` with dependency caching
  - Triggers on push/PR to main
  - Created `check-ci` Makefile target (CI-safe, no auto-fix)
  - Fixed 9 pre-existing mypy errors across 7 files to start clean
- **Phase 2: Threshold gates** — Fixed floors in all 4 eval runners
  - `run_eval.py`: faithfulness ≥ 0.90, context_precision ≥ 0.65, answer_relevancy ≥ 0.40, has_citations ≥ 0.80, risk_level_valid ≥ 0.95, high_risk_pro ≥ 0.90
  - `run_maintenance_eval.py`: overall_pass_rate ≥ 0.80, source_coverage ≥ 50%, markdown checks
  - `run_troubleshooting_eval.py`: overall_pass_rate ≥ 0.85, safety_stop accuracy = 100% (invariant)
  - `run_parts_eval.py`: overall_pass_rate ≥ 0.85, confirmed_have_sources (invariant), uncertain_no_part_numbers (invariant)
  - All runners now: `main() -> int` + `--threshold-check` flag + `sys.exit(main())`
  - Added Makefile targets: `eval-threshold`, `eval-*-threshold`, `eval-check-all`
- **Phase 3: Golden set expansion** — 50 → 100 questions, 65% ground truth
  - 50 new questions (IDs 51-100) covering:
    - Safety/adversarial bypass attempts (51-58)
    - Insufficient evidence / out-of-scope (61-70)
    - Multi-device cross-system scenarios (71-80)
    - Tricky phrasing, slang, poor grammar (86-90)
    - Device-specific deep dives (81-85, 91-96)
    - Out-of-scope boundaries (97-100)
  - Ground truth added to 65/100 questions (IDs 61-70 intentionally without — insufficient evidence tests)
- **Phase 4: Workflow eval improvements**
  - Troubleshooting: replaced "I'm not sure" stub answers with realistic homeowner responses matched from scenario context via keyword heuristics
  - Maintenance: added device coverage enforcement, duplicate task detection, max items upper bound (30)
  - Parts: added `uncertain_no_part_numbers` as threshold invariant, duplicate part detection
- **Phase 5: Future CI eval gates** — eval runners require OPENAI_API_KEY (LLM calls), so full eval will use `workflow_dispatch` trigger in future, not on every PR
- Key files: `.github/workflows/ci.yml`, `eval/run_*.py`, `eval/golden_questions.jsonl`, `eval/troubleshooting_golden.json`
- Tests: 294 unit tests, all passing
- **Week 9 Complete!** Ready for Week 10 (Red-teaming + safety tightening)

**2026-02-17** - Week 8: Langfuse Observability Integration
- **Architecture**: Feature-flagged Langfuse tracing via `OBSERVABILITY__ENABLED` env var
  - When disabled (default): `@observe()` is a no-op, plain `openai.OpenAI` client — zero overhead
  - When enabled: `langfuse.openai.OpenAI` auto-traces all LLM calls (tokens, latency, I/O)
  - `@observe()` decorators create span hierarchy for non-LLM functions
  - Graceful fallback: missing keys → warning + plain client; missing package → same
- **Centralized LLM client** (`app/llm/client.py`):
  - Replaces 4 duplicated `get_llm_client()` functions (query.py, 3 workflows)
  - `@lru_cache(maxsize=1)` for singleton behavior
  - When observability enabled: `langfuse.openai.OpenAI` wrapped with instructor
  - When disabled: `openai.OpenAI` wrapped with instructor (identical to before)
- **Tracing helpers** (`app/llm/tracing.py`):
  - `observe(**kwargs)`: Decorator that delegates to `langfuse.observe()` or returns no-op
  - `init_tracing()`: Initializes Langfuse singleton at startup (called in `main.py`)
- **Files modified**: 11 existing files + 5 new files
  - New: `app/llm/__init__.py`, `app/llm/client.py`, `app/llm/tracing.py`, `tests/test_llm_client.py`, `tests/test_tracing.py`, `tests/conftest.py`
  - Modified: `pyproject.toml`, `app/core/config.py`, `app/rag/query.py`, `app/rag/retriever.py`, `app/workflows/maintenance_planner.py`, `app/workflows/parts_helper.py`, `app/workflows/troubleshooter.py`, `app/main.py`, `tests/test_query.py`
- **What gets traced** (when enabled):
  - LLM calls: 6 call sites auto-traced via Langfuse OpenAI wrapper
  - `@observe()` on 17 functions: 5 API endpoints, 1 RAG query, 1 retrieval, 10 workflow nodes
- **Tests**: 12 new tests (5 client + 7 tracing), 296 total unit tests pass
  - Added `tests/conftest.py` with autouse fixture to clear `get_llm_client` cache between tests
- Key files: `app/llm/client.py`, `app/llm/tracing.py`, `app/core/config.py`
- **Week 8 Complete!** Ready for Week 9 (Evaluation v2 + regression gates)

**2026-02-10** - Week 7: Parts & Consumables Helper
- **Architecture**: Single-invocation LangGraph workflow (no session storage needed)
  - Graph: START → parse_query → retrieve_docs → generate_parts_list → render_markdown → END
  - When info is incomplete, response includes `clarification_questions` alongside whatever parts _can_ be identified
  - Users refine by re-querying with more detail (no session state between invocations)
- **Shared helpers extraction**:
  - Created `app/workflows/helpers.py` with `format_chunks_as_context()` and `format_device_details()`
  - Generalized `format_device_details()` to accept `(house_profile, device_type)` instead of `TroubleshootingState`
  - Updated troubleshooter imports — all existing tests still pass
- **Backend files created**:
  - `app/workflows/parts_helper_models.py` — All Pydantic models (ConfidenceLevel, PartRecommendation, ClarificationQuestion, PartsLookupResponse, PartsHelperState, API models)
  - `app/workflows/parts_helper.py` — LangGraph workflow (4 nodes: parse_query, retrieve_docs, generate_parts_list, render_markdown)
  - `app/workflows/helpers.py` — Shared helper functions extracted from troubleshooter
  - `tests/test_parts_helper.py` — 40 unit tests (model validation, helpers, graph compilation, node functions, render)
- **Confidence levels**:
  - CONFIRMED: Part found in docs with part number or explicit reference (requires source_doc)
  - LIKELY: Inferred from documentation (device specs suggest this part)
  - UNCERTAIN: General knowledge, not in docs (must NOT have part_number)
- **API endpoint**: `POST /parts/lookup` — Accepts query + optional device_type, returns parts with confidence + clarification questions
- **Frontend**:
  - `ConfidenceBadge.tsx` — Green (confirmed), yellow (likely), gray (uncertain) badges
  - `PartsQueryForm.tsx` — Free-text query + device filter buttons + quick-query chips ("All filters", "All consumables")
  - `PartsResultsDisplay.tsx` — Part cards grouped by device, confidence badges, clarification questions section, copy/export
  - `PartsHelperPage.tsx` — Simple query → results page (idle → loading → results states)
  - Added Parts Helper card to HomePage (wrench icon), `/parts` route in App.tsx
- **Evaluation**: 8 golden scenarios in `eval/parts_golden.json`
  - furnace_filter, hrv_filter, humidifier_pad, all_filters, water_softener_salt, unknown_device, vague_query, specific_model
  - `eval/run_parts_eval.py` with rule-based checks (min parts, confidence constraints, source citations, part numbers)
  - `make eval-parts` Makefile target
- Key files: `app/workflows/parts_helper.py`, `app/workflows/parts_helper_models.py`, `frontend/src/pages/PartsHelperPage.tsx`
- **Week 7 Complete!** Ready for Week 8 (Observability)

**2026-02-10** - Week 6: Troubleshooting Tree Workflow
- **Architecture**: Two-invocation approach (intake graph + diagnosis graph) with server-side session storage
  - Invocation 1 (intake): intake_parse -> retrieve_docs -> assess_risk -+-> generate_followups / safety_stop
  - Invocation 2 (diagnosis): generate_diagnosis -> render_output
  - In-memory session dict between invocations (adequate for local single-user)
- **Safety model (two layers)**:
  - Layer 1: Deterministic keyword matching (`SAFETY_STOP_PATTERNS`) for gas, CO, electrical, structural, valve issues
  - Layer 2: LLM risk assessment via instructor (for nuanced cases that keywords miss)
  - If either layer triggers HIGH + safety -> workflow stops, no DIY steps generated
- **Backend files created**:
  - `app/workflows/troubleshooter_models.py` - All Pydantic models (FollowupQuestion, DiagnosticStep, TroubleshootingState, API models)
  - `app/workflows/troubleshooter.py` - LangGraph workflow (5-node intake graph, 2-node diagnosis graph, safety patterns)
  - `tests/test_troubleshooter.py` - 40+ tests (model validation, safety patterns, graph compilation, node functions, integration)
- **API endpoints** added to `app/main.py`:
  - `POST /troubleshoot/start` - Runs intake graph, returns follow-ups or safety stop
  - `POST /troubleshoot/diagnose` - Runs diagnosis graph with follow-up answers
- **Frontend**:
  - `IntakeForm.tsx` - Device selector (from house profile) + symptom + urgency + context
  - `FollowupQuestions.tsx` - Renders yes_no buttons, multiple_choice radios, free_text inputs
  - `DiagnosticStepsDisplay.tsx` - Numbered step cards with risk badges, sources, copy/export
  - `SafetyWarning.tsx` - Red warning banner with professional recommendation
  - `TroubleshootPage.tsx` - Stepper/wizard with 3 phases (intake -> followup/safety -> diagnosis)
  - Added troubleshoot card to HomePage, route in App.tsx
- **Evaluation**: 6 golden scenarios in `eval/troubleshooting_golden.json`
  - 3 safety-stop scenarios (gas, electrical, CO)
  - 3 diagnosis scenarios (furnace no heat, water heater, HRV noise)
  - `eval/run_troubleshooting_eval.py` with rule-based checks
  - `make eval-troubleshoot` Makefile target
- Key files: `app/workflows/troubleshooter.py`, `app/workflows/troubleshooter_models.py`, `frontend/src/pages/TroubleshootPage.tsx`
- **Week 6 Complete!** Ready for Week 7 (Parts & consumables helper)

**2026-02-05** - Maintenance Plan UI
- Added dedicated `/maintenance-plan` page to React frontend
- **Backend additions**:
  - `GET /house-profile` - Load house profile from JSON
  - `PUT /house-profile` - Save house profile to JSON
  - Added `save_house_profile()` helper function to models.py
- **Frontend types** (types.ts):
  - Season, ClimateZone, HouseType enums
  - InstalledSystem, HouseProfile interfaces
  - ChecklistItem, MaintenancePlanRequest, MaintenancePlanResponse interfaces
- **API client** (api/client.ts):
  - `generateMaintenancePlan(season)` - Call maintenance plan endpoint
  - `getHouseProfile()` - Load house profile
  - `updateHouseProfile(profile)` - Save house profile
- **Components created**:
  - `SeasonSelector.tsx` - Button group for season selection
  - `ChecklistDisplay.tsx` - Renders markdown with copy/export buttons
  - `HouseProfileEditor.tsx` - Form for editing house profile and systems
- **Main page** (`MaintenancePlanPage.tsx`):
  - Displays house profile summary
  - Season selector + Generate Plan button
  - Renders checklist with export to markdown file
  - Edit mode for house profile
- **Routing updates**:
  - Added card in HomePage.tsx for maintenance plan mode
  - Added route in App.tsx for `/maintenance-plan`
- Key files: `frontend/src/pages/MaintenancePlanPage.tsx`, `frontend/src/components/HouseProfileEditor.tsx`

**2026-02-05** - Week 5 Phase 1, 2 & 3 Complete
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
  - Added `POST /maintenance-plan` endpoint to FastAPI
- **Phase 3: Node implementation**
  - Retrieval node: Season-specific queries, filters by house profile device types
  - Extended `retrieve()` in retriever.py to accept custom `device_types` parameter
  - Generation node: LLM call with instructor for structured `ChecklistItem` output
  - Added `ChecklistResponse` wrapper model and `CHECKLIST_SYSTEM_PROMPT`
  - Generates 15-25 detailed checklist items with priorities, frequencies, notes, sources
  - Render node: Apple Notes-friendly markdown grouped by priority (High/Medium/Low)
- **Phase 4: Polish & Test**
  - Added `SEASON_CONTEXT` with priorities/focus for each season
  - End-to-end tested all 4 seasons (Spring: 19, Summer: 12, Fall: 13, Winter: 24 items)
  - Created `tests/test_maintenance_planner.py` (5 unit + 4 integration tests)
  - Created `eval/maintenance_golden.json` with quality criteria per season
  - Created `eval/run_maintenance_eval.py` evaluation script
  - Added `make eval-maintenance` Makefile command
- Key files: `app/workflows/maintenance_planner.py`, `tests/test_maintenance_planner.py`, `eval/run_maintenance_eval.py`
- **Week 5 Complete!** Ready for Week 6 (Troubleshooting workflow)

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
| 2026-02-26 | GitHub Actions CI with make commands | CI mirrors local dev workflow; 2,000 free min/month on private repos |
| 2026-02-26 | Fixed metric thresholds (not relative) | Prevents gradual quality degradation; each commit must meet absolute floors |
| 2026-02-26 | Eval runs not in CI (yet) | Require OPENAI_API_KEY + cost; plan `workflow_dispatch` trigger for manual eval gates |
| 2026-02-26 | truststore for SSL | Corporate proxy injects Cisco CA; truststore bridges OS cert store to httpx/OpenAI SDK |
| 2026-02-26 | Langfuse disabled in eval runners | Evals don't need tracing; avoids cost and noisy auth errors |
| 2026-02-26 | Standalone adversarial eval runner | Separate from main RAG eval; different thresholds and safety-critical 100% requirement |
| 2026-02-26 | Anti-injection in all prompts | Even maintenance planner (no direct user input) gets hardened for defense in depth |
| 2026-02-26 | max_completion_tokens 16000 default | GPT-5.2 reasoning models consume tokens for internal reasoning; 1000-4000 caused empty outputs |
| 2026-02-26 | Co-occurrence keyword groups | Substring matching too brittle for non-adjacent keywords; co-occurrence catches "burning...electrical panel" |
| 2026-02-26 | Shared export utilities (DRY) | 5 components had 3 different copy patterns; centralized with browser fallback |
| 2026-02-26 | ICS without third-party library | RFC 5545 spec is simple enough for VEVENT generation; avoids adding `icalendar` dependency |
| 2026-02-26 | Priority-staggered calendar events | High→day 1, Medium→+7d, Low→+14d prevents overwhelming the homeowner |
| 2026-02-26 | OpenAPI tags for all endpoints | Groups endpoints in Swagger UI by feature area; better for portfolio demos |
| 2026-02-26 | Structured logging in main.py | Logs key metrics per request (risk level, item counts, safety stops) without verbosity |
| 2026-02-26 | Pin Docker base image versions | Reproducible builds; prevents surprise breakage from upstream tag updates |

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
