# Week 4 Evaluation Baseline

> Captured: 2026-01-27
> Purpose: Compare before/after retrieval quality improvements

## Baseline Metrics (5 questions)

| Category | Metric | Value |
|----------|--------|-------|
| **Format** | Successful calls | 100% |
| | Has citations | 100% |
| | Valid risk level | 100% |
| **Ragas** | Faithfulness | **0.815** |
| | Answer Relevancy | **0.507** |
| | Context Precision | **0.861** |

## Key Observations

- Context Precision solid (0.861) — retrieved chunks are mostly relevant
- Faithfulness good (0.815) — answers grounded in retrieved content
- Answer Relevancy weak (0.507) — main area for improvement

## Week 4 Improvements

- [ ] Metadata filtering
- [ ] Improved chunking (heading/section-aware)
- [ ] Reranking

## Post-Improvement Results

### After Metadata Filtering + Hybrid Fallback (5 questions)

| Metric | Baseline | After | Delta |
|--------|----------|-------|-------|
| Faithfulness | 0.815 | **0.886** | +0.071 (+8.7%) |
| Answer Relevancy | 0.507 | 0.431 | -0.076 (-15%) |
| Context Precision | 0.861 | **0.861** | 0 |

### After Section-Aware Chunking (5 questions)

| Metric | Baseline | +Metadata Filter | +Section Chunking |
|--------|----------|------------------|-------------------|
| Faithfulness | 0.815 | 0.886 | **0.872** |
| Answer Relevancy | 0.507 | 0.431 | 0.457 |
| Context Precision | 0.861 | 0.861 | 0.726 |

**Notes**:
- Chunk count increased from ~250 to 416 (more granular sections)
- Context precision dropped — more chunks means more competition for top-k
- Faithfulness remains high — answers still well-grounded
- Small sample size (3 questions with ground truth) makes metrics noisy

## Implementation Summary

### 1. Metadata Filtering
- **Device type detection** — Keywords map questions to document types (furnace, hrv, etc.)
- **Metadata filtering** — LlamaIndex filters to relevant document subsets
- **Hybrid fallback** — Falls back to unfiltered search if filtered results have low scores

### 2. Section-Aware Chunking
- **Section detection** — Detects ALL CAPS headings in PDF text
- **Markdown preprocessing** — Converts to ## headings for structure-aware parsing
- **Two-stage chunking** — MarkdownNodeParser first, then SentenceSplitter for large sections
- **Section metadata** — Preserves section title in chunk metadata
