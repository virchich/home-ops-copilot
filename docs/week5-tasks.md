# Week 5 — Seasonal Maintenance Planner (LangGraph)

> **Goal**: First LangGraph workflow for maintenance planning.
> **Deliverable**: "Winter maintenance plan" is generated cleanly.

---

## Phase 1: Foundation ✅

- [x] **1.1** Add LangGraph dependency (`uv add langgraph`) and verify import
- [x] **1.2** Define house profile schema — Pydantic model for house metadata (systems installed, climate zone, house age, etc.)
- [x] **1.3** Create sample house profile — JSON file representing actual house for testing

## Phase 2: Workflow Skeleton

- [ ] **2.1** Define workflow state schema — Pydantic model for data flowing through graph (input, retrieved docs, checklist items, final output)
- [ ] **2.2** Build minimal LangGraph workflow — Empty nodes wired together, passing state through
- [ ] **2.3** Add `/maintenance-plan` endpoint — FastAPI route that invokes the workflow

## Phase 3: Node Implementation

- [ ] **3.1** Retrieval node — Query index filtered by season + relevant device types from house profile
- [ ] **3.2** Checklist generation node — LLM call with strict JSON output (instructor) for structured checklist items
- [ ] **3.3** Markdown rendering node — Convert checklist JSON to Apple Notes-friendly markdown

## Phase 4: Polish & Test

- [ ] **4.1** Add season-specific prompts/logic — Different retrieval queries and checklist structure per season
- [ ] **4.2** End-to-end test — Generate plans for all 4 seasons, verify output quality
- [ ] **4.3** Add to eval suite — Golden examples for maintenance plan generation

---

## Session Notes

**2026-02-05** - Phase 1 Complete
- Added LangGraph 1.0.5 (brings in langchain-core, langgraph-checkpoint, langgraph-sdk)
- Created `app/workflows/` package with models:
  - `Season`, `ClimateZone`, `HouseType` enums
  - `InstalledSystem` for device details
  - `HouseProfile` with helper methods (`has_system()`, `get_installed_device_types()`)
  - `load_house_profile()` utility function
- Created `data/house_profile.json` with 7 systems (all installed 2018):
  - Furnace (Carrier, gas), Thermostat (Ecobee), HRV (Lifebreath)
  - Water heater (Giant, gas), Water softener (Fleck), Humidifier (GeneralAire)
  - Energy meter (Eaton)
- All tests pass (195), linting/mypy clean

---

## Open Questions

- ~~LangGraph vs PydanticGraph?~~ **Decided: LangGraph**
