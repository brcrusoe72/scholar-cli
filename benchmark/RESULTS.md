# scholar benchmark — results

## Update 2026-07-11 — relevance filter (v0.3.0)

The 2026-07-10 benchmark found scholar's bottleneck was query relevance, not
ranking. v0.3.0 adds a deterministic relevance filter: over-fetch candidates,
score each by weighted query-term coverage **plus adjacent-phrase coverage**,
drop anything below 0.40, then order survivors. Same 20 questions, same rubric:

| metric | before (v0.2) | after filter (v0.3) |
|---|---|---|
| **precision** (on-target ÷ results returned) | 26% (26/100) | **52%** (35/67) |
| primary@5 (on-target per 5 slots) | 26% | **35%** |
| queries returning misleading off-topic noise | most | **0** |

**Precision nearly doubled** — when scholar returns a result it's now on-target
about half the time, vs. a quarter. The win comes two ways: over-fetching +
filtering *surfaces* on-topic papers OpenAlex buried (12h/8h-shift safety 2→5,
data-center demand 2→4, gut-microbiome/depression 1→4, LLM predictive
maintenance 1→3, AI-coding 0→2), and the phrase gate *drops* the ambiguous-word
false positives (OEE↔"plant" botany, "production line"↔sheep production,
"packaging lines"↔high-speed circuits). Two manufacturing-practitioner queries
now return **empty** — an honest "no strong scholarly match" beats five
off-topic papers.

**The honest cost:** the filter also drops genuine matches on vocabulary
variants — a "preventive maintenance" query loses "*predictive* maintenance"
papers (preventive≠predictive under prefix matching), so preventive-maintenance
fell 5→3 and a few others slipped. Net is still strongly positive, and the
tradeoff is tunable (`--min-relevance`, `--no-filter`). Regenerate:
`run_benchmark.py --filtered`; raw per-query results in `results_filtered.md`.

---

## Baseline (2026-07-10)

**The number: scholar 26% vs. default web search 18%.**

Across 20 research questions, the share of the top-5 results that are a
peer-reviewed primary source (or peer-reviewed systematic review) that
*actually addresses the question*. Higher is better.

| | scholar | web search |
|---|---|---|
| **primary@5** | **26%** (26/100) | **18%** (18/100) |
| per-question wins | 7 | 4 |
| ties | 9 | |

## Method

- 20 questions in `questions.txt`, spanning Brian's real domains
  (manufacturing floor, shift-work health, power/energy, AI, personal).
- **scholar**: top-5 in credibility-ranked order (`ranking.py`).
- **web search**: top-5 links from the agent's default web search, same queries.
- **Rubric (identical for both)**: a result scores **y** only if it is
  peer-reviewed (real journal/conference venue) **and** on-topic enough that
  a researcher on the question would cite it. Preprints (arXiv/bioRxiv),
  lab/government reports (NREL/OSTI), theses, trade blogs, vendor pages, and
  news all score **n** — even when useful.
- Single-judge scoring (one reviewer, one pass) against that rubric. n=20.

## Per-question (primary@5)

| # | question | scholar | web |
|---|----------|:---:|:---:|
| 1 | OEE ↔ plant profitability | 0 | 0 |
| 2 | changeover reduction, food mfg | 1 | 1 |
| 3 | cross-training ↔ line performance | 0 | 0 |
| 4 | tiered huddles ↔ manufacturing KPIs | 0 | 0 |
| 5 | minor stops, packaging lines | 0 | 0 |
| 6 | preventive maintenance ↔ downtime | **5** | 0 |
| 7 | shift work ↔ sleep & metabolism | **5** | 4 |
| 8 | 12h vs 8h shifts ↔ safety | 2 | 2 |
| 9 | turnover interventions, hourly mfg | 1 | 0 |
| 10 | grid battery storage cost | 0 | 0 |
| 11 | data-center electricity demand | 2 | 0 |
| 12 | US retail price drivers (T&D) | 0 | 0 |
| 13 | LCOE nuclear vs renewables+storage | 0 | 1 |
| 14 | electricity price ↔ plant location | 0 | 2 |
| 15 | RAG ↔ LLM hallucination | 3 | 0 |
| 16 | LLMs for predictive maintenance | 1 | 3 |
| 17 | LLM agents ↔ multi-step tool use | 2 | 0 |
| 18 | AI coding ↔ developer productivity | 0 | 0 |
| 19 | gut microbiome ↔ depression | 1 | 4 |
| 20 | adult ADHD task-initiation | 3 | 1 |
| | **total** | **26** | **18** |

## What the number actually says

**1. Scholar wins, but the win is entirely on well-specified queries.**
On unambiguous scientific questions it dominates: preventive maintenance 5/0,
shift-work/sleep 5/4, RAG/hallucination 3/0. That's the product working — for
"what does the research say," it beats web search decisively.

**2. Scholar's failure mode is lexical ambiguity, and it's brutal.**
Four questions scored a flat 0/5 because OpenAlex's keyword search matched the
wrong sense of a word:
- "OEE ↔ **plant** profitability" → papers on *botanical* plants (antioxidants, root traits, soil microbes).
- "cross-**training** ↔ **production** line" → machine-learning *training* and *data clustering*.
- "minor **stops** in packaging **lines**" → quantum chemistry and coronal physics.
Scholar has no query understanding — it inherits OpenAlex's lexical match verbatim.

**3. Ranking is not the lever — relevance is.**
Comparing credibility order vs. raw API order did **not** materially raise the
number, and in specific cases it *hurt*: on the changeover query, `ranking.py`
demoted the directly-on-topic SMED paper out of the top-5 because it had fewer
citations; on battery-storage cost, the actual NREL cost-projection reports were
buried because they have no journal venue. Tuning weights won't fix a relevance
problem.

**4. Web search is the mirror image:** highly relevant, rarely peer-reviewed.
Its results are dominated by trade blogs and vendor pages (TeepTrak, Shoplogix,
UpKeep, Poka) — useful to read, but not citable. The exception is health/medical
queries, where the open web surfaces PubMed/PMC directly and web *beats* scholar
(gut-microbiome 4/1, predictive-maintenance 3/1).

## The next rep this points to

The benchmark says the highest-leverage fix is **query relevance**, not ranking:
add a title/abstract on-topic filter (or a relevance floor) so ambiguous
keywords stop returning off-sense papers, then re-run this benchmark. Target:
lift the four 0/5 questions and push primary@5 from 26% toward the ~55%+ the
well-specified queries already hit.

## Limitations (stated plainly)

- Single judge, one pass — not blind, not multi-rater.
- Strict "peer-reviewed primary source" rubric; counting preprints/reports as
  credible would raise **both** numbers (scholar more than web).
- n=20. Directional, not publication-grade.
