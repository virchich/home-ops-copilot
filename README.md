# Home Ops Copilot

A RAG-powered assistant for home maintenance, troubleshooting, and parts management. Ingests equipment manuals and documentation, then provides cited answers with risk assessments and safety guardrails.

## What It Does

**Ask questions** about your home systems and get answers grounded in your actual manuals — not generic internet advice.

- **Chat** — Ask anything about your furnace, HRV, water heater, etc. Every answer includes citations, risk level, and a professional recommendation when needed.
- **Seasonal Maintenance Planner** — Generate a prioritized checklist for any season based on your house profile and equipment docs. Export as Markdown or download calendar reminders (.ics).
- **Troubleshooting Wizard** — Guided intake → follow-up questions → diagnostic steps. Two-layer safety system (deterministic + LLM) stops dangerous scenarios before generating DIY advice.
- **Parts & Consumables Helper** — Identify correct replacement parts with confidence levels (Confirmed / Likely / Uncertain). Asks clarifying questions when information is incomplete.

### Safety First

Every response includes a risk assessment (LOW / MED / HIGH). High-risk topics involving gas, electrical, carbon monoxide, or structural work trigger an immediate safety stop with professional referral — no DIY instructions are generated.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 React Frontend                   │
│  Chat │ Maintenance │ Troubleshoot │ Parts       │
└──────────────────────┬──────────────────────────┘
                       │ REST API
┌──────────────────────┴──────────────────────────┐
│                FastAPI Backend                    │
│                                                  │
│  ┌──────────┐  ┌────────────────────────────┐   │
│  │ /ask     │  │ LangGraph Workflows        │   │
│  │ RAG Query│  │  • Maintenance Planner     │   │
│  │          │  │  • Troubleshooting Tree    │   │
│  │          │  │  • Parts Helper            │   │
│  └────┬─────┘  └─────────────┬──────────────┘   │
│       │                      │                   │
│  ┌────┴──────────────────────┴──────────────┐   │
│  │           RAG Pipeline                    │   │
│  │  LlamaIndex: Embed → Index → Retrieve    │   │
│  │  Metadata filtering │ Section-aware chunks│   │
│  └───────────────────────────────────────────┘   │
│                                                  │
│  ┌───────────────────────────────────────────┐   │
│  │           Safety System                    │   │
│  │  Layer 1: Deterministic keyword patterns   │   │
│  │  Layer 2: LLM risk assessment (instructor) │   │
│  │  Co-occurrence matching for complex hazards│   │
│  └───────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
         │
    ┌────┴────┐
    │ OpenAI  │  GPT-5.2 + text-embedding-3-small
    └─────────┘
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| LlamaIndex for RAG | Good balance of features and simplicity |
| LangGraph for workflows | Explicit control flow over pure agents |
| instructor for LLM outputs | Pydantic-validated structured outputs |
| Two-layer safety | Deterministic patterns catch known hazards fast; LLM handles nuance |
| Local-first persistence | File-based vector index, no database setup needed |
| Feature-flagged Langfuse | Zero overhead when disabled; full tracing when enabled |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.13 |
| Package Manager | uv |
| API | FastAPI |
| RAG | LlamaIndex (text-embedding-3-small) |
| Workflows | LangGraph |
| LLM | OpenAI GPT-5.2 (via instructor) |
| Observability | Langfuse (opt-in) |
| Evaluation | Ragas + custom rule-based evals |
| Frontend | React + TypeScript + Tailwind CSS |
| CI | GitHub Actions (ruff + mypy + pytest) |

## Getting Started

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ (for frontend)
- OpenAI API key

### Setup

```bash
# Clone and install
git clone https://github.com/yourusername/home-ops-copilot.git
cd home-ops-copilot
make install

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Ingest your documents
# Place PDF manuals in data/raw_docs/ and update data/metadata.json
make ingest-rebuild

# Start the backend
make run

# In another terminal — start the frontend
make frontend-install
make frontend-dev
```

The app is now running at `http://localhost:5173` (frontend) and `http://localhost:8000` (API).

### Docker

```bash
# Build and start everything
make docker-build
make docker-up

# Stop
make docker-down
```

## Project Structure

```
app/
├── core/           # Config (pydantic-settings), SSL setup
├── llm/            # Centralized LLM client, Langfuse tracing
├── rag/            # Ingestion, retrieval, query, models
└── workflows/      # LangGraph workflows (maintenance, troubleshoot, parts, ICS)

eval/
├── golden_questions.jsonl       # 100 RAG eval questions (65% with ground truth)
├── adversarial_golden.json      # 18 adversarial safety scenarios
├── troubleshooting_golden.json  # 6 troubleshooting scenarios
├── parts_golden.json            # 8 parts lookup scenarios
├── maintenance_golden.json      # 4 seasonal maintenance scenarios
└── run_*.py                     # Eval runners with threshold gates

frontend/src/
├── api/            # API client
├── components/     # 18 React components
├── contexts/       # Chat context (localStorage persistence)
├── pages/          # 5 pages (Chat, Home, Maintenance, Troubleshoot, Parts)
└── utils/          # Shared clipboard/export utilities

tests/              # 350+ tests (unit + integration)
```

## Evaluation

The project uses a multi-layered evaluation approach to prevent quality drift:

### RAG Evaluation (100 questions)
- **Ragas metrics**: Faithfulness, context precision, answer relevancy
- **Custom metrics**: Citation rate, risk level validity, HIGH→professional rate
- **Threshold gates**: Every metric has a floor (e.g., faithfulness ≥ 0.90)

### Workflow Evaluations
- **Maintenance**: Source coverage ≥ 50%, markdown formatting, no duplicate tasks
- **Troubleshooting**: Safety stop accuracy = 100% (invariant), realistic diagnostic steps
- **Parts**: Confirmed parts must have sources, uncertain parts must not have part numbers

### Adversarial Safety Evaluation (18 scenarios)
Tests across 4 categories:
- **Prompt injection** — system ignores injected override instructions
- **Safety bypass** — refuses unsafe advice regardless of claimed experience
- **Overconfidence** — indicates uncertainty when knowledge base lacks info
- **Risk accuracy** — gas/electrical/structural = always HIGH

Safety-critical categories (prompt injection + safety bypass) require **100% pass rate**.

### Running Evals

```bash
# Individual evals
make eval                    # RAG eval (100 questions)
make eval-maintenance        # Seasonal maintenance eval
make eval-troubleshoot       # Troubleshooting eval
make eval-parts              # Parts helper eval
make eval-adversarial        # Adversarial safety eval

# With threshold gates (fails on regression)
make eval-check-all          # All evals with gates
```

## Development

```bash
make check          # Lint + format + type check (auto-fix)
make test           # Run all tests
make test-unit      # Unit tests only (fast, no API calls)
make help           # See all available commands
```

### CI Pipeline

GitHub Actions runs on every push/PR to main:
1. **Lint** — ruff check + ruff format --check + mypy
2. **Test** — pytest (unit tests, no API key needed)

Eval runs are manual (`make eval-check-all`) since they require an OpenAI API key and cost ~$1-2 per full run.

## Known Limitations

- **Single-user local app** — session storage is in-memory, no auth
- **7 documents** — knowledge base is limited to the ingested manuals
- **English only** — prompts and safety patterns are English-language
- **No real-time updates** — documents must be re-ingested after changes
- **Reranking disabled** — cross-encoder reranker hurt quality on technical docs; kept as opt-in

## License

Private project — not licensed for redistribution.
