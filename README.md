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

## The number

TBD — benchmark in progress: % of top-5 results that are peer-reviewed
primary sources, `scholar` vs. default agent web search, across 20 research
questions. Harness: `benchmark/run_benchmark.py`.

## Non-goals (v1)

- **No general web search.** Tavily and built-in web search exist; this is the scholarly lane only.
- **No summarization.** The agent is the brain; this tool is the hands.
- **No full-text extraction yet.** v1 returns metadata + open-access links.
- **No multi-source fusion yet.** OpenAlex covers ~250M works. A second source gets added when a real query misses, not before.

## Development

```bash
uv sync --extra dev
uv run pytest        # 3 live contract tests against the real API (network required)
```

## License

MIT
