"""Benchmark harness — produces the table behind THE number.

For each question in questions.txt, fetch the top 5 results and emit a
markdown table with an empty "primary?" column. Scoring is deliberately
manual: you read each hit and mark y/n for "peer-reviewed primary source
(or peer-reviewed review) that actually addresses the question."

THE number = % of "y" across all rows. Run the same questions through your
comparison target (e.g. default web search in Claude) and score with the
same standard. Publish both.

Usage:
    uv run python benchmark/run_benchmark.py            # -> benchmark/results.md
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from scholar_cli.openalex import OpenAlexError, search  # noqa: E402
from scholar_cli.ranking import rank  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
TOP_N = 5


def load_questions() -> list[str]:
    lines = (HERE / "questions.txt").read_text().splitlines()
    return [q.strip() for q in lines if q.strip() and not q.startswith("#")]


def main() -> int:
    questions = load_questions()
    if len(questions) < 20:
        print(f"note: only {len(questions)}/20 questions — fine for a dry run, "
              f"not enough to publish a number.")

    out = ["# scholar benchmark — top-5 credibility", "",
           "Score `primary?` as y/n: peer-reviewed primary source (or "
           "peer-reviewed review) that addresses the question.", ""]
    rows = 0
    for q in questions:
        out.append(f"## {q}")
        out.append("")
        out.append("| # | title | year | venue | citations | link | primary? |")
        out.append("|---|-------|------|-------|-----------|------|----------|")
        try:
            works = rank(search(q, count=TOP_N))
        except OpenAlexError as exc:
            out.append(f"| - | SEARCH FAILED: {exc} | | | | | |")
            out.append("")
            continue
        for i, w in enumerate(works, 1):
            link = w.oa_url or w.doi or w.openalex_id or ""
            title = w.title.replace("|", "/")[:90]
            out.append(f"| {i} | {title} | {w.year or ''} | {w.venue or ''} "
                       f"| {w.citations} | {link} | |")
            rows += 1
        out.append("")

    results = HERE / "results.md"
    results.write_text("\n".join(out))
    print(f"wrote {results} — {rows} rows to score.")
    print("THE number = count(y) / rows. Same questions, same standard, "
          "through the comparison target next.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
