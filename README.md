# scholar

Scholarly search CLI for AI agents. One command, one source (OpenAlex), no API key, no server.

```bash
uv tool install /path/to/scholar    # or, once published: uvx scholar-cli
scholar "gut microbiome depression" --since 2022 --oa
```

```
1. The gut microbiome in depression: ... (2023)  [open access]
   A. Author, B. Author — Nature Reviews Microbiology — 412 citations
   https://doi.org/10...
```

Agents use `--json`:

```bash
scholar "constraint management OEE" --count 5 --json
```

## Deep context for one work

`scholar context` takes a DOI, an OpenAlex ID, or a title and returns the
layered context around a single paper — its abstract, the work it **builds
on** (its most credible references), what **cited** it, and **related**
work. One call, four layers, so an agent can walk a citation graph instead
of re-searching.

```bash
scholar context 10.1038/nature14539
scholar context "attention is all you need" --json
```

```
Attention Is All You Need (2017)  [open access]
...
── Builds on (its most credible references) ──
1. Deep Residual Learning for Image Recognition ...
── Cited by (what built on it) ──
1. BERT: Pre-training of Deep Bidirectional Transformers ...
── Related ──
...
```

## Why

General web search feeds agents SEO slop and press releases. The scholarly
world already ships free, keyless, structured APIs where credibility is
data — venue, citations, retraction flags — not vibes. `scholar` is the
zero-config front door to that.

## Flags

| Flag | Does |
|---|---|
| `--since YEAR` | only works published YEAR or later |
| `--oa` | open-access only |
| `--count N` | results to return (default 10) |
| `--json` | structured output for agents |
| `--mailto EMAIL` | OpenAlex polite pool (better rate limits); or env `SCHOLAR_MAILTO` |

`context` takes `--json` and `--mailto` too.

## The number

**scholar 26% vs. default web search 18%** — share of the top-5 results that
are peer-reviewed primary sources addressing the question, across 20 research
questions ([full results + method](benchmark/RESULTS.md)).

The win is real but honest: scholar dominates well-specified scientific
queries (preventive-maintenance 5/0, shift-work 5/4) and ties or loses on
short ambiguous keywords, where OpenAlex's lexical search returns the wrong
sense of a word ("plant profitability" → botany). The benchmark's clear next
lever is **query relevance**, not ranking. Reproduce: `benchmark/run_benchmark.py`.

## Non-goals (v1)

- **No general web search.** Tavily and built-in web search exist; this is the scholarly lane only.
- **No summarization.** The agent is the brain; this tool is the hands.
- **No full-text extraction yet.** v1 returns metadata, abstracts + open-access links.
- **No multi-source fusion yet.** OpenAlex covers ~250M works. A second source gets added when a real query misses, not before.

## Development

```bash
uv sync --extra dev
uv run pytest        # 3 live contract tests against the real API (network required)
```

## License

MIT
