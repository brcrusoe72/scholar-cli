"""Benchmark harness — produces the table behind THE number.

For each question, fetch the top 10 works ONCE, then show two orderings of
the same works side by side: `api#` (OpenAlex relevance) and `cred#`
(ranking.py). You score each work once — y/n in `primary?` for
"peer-reviewed primary source (or peer-reviewed review) that actually
addresses the question" — and the tally computes both numbers:

    primary@5, API order    — the honest baseline
    primary@5, cred order   — does ranking.py earn its keep?

The README headline number compares scholar against default agent web
search: run the same questions there, score with the same standard.

Usage:
    uv run python benchmark/run_benchmark.py            # -> benchmark/results.md
    # ... edit results.md, fill the primary? column with y or n ...
    uv run python benchmark/run_benchmark.py --tally    # compute the numbers
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from scholar_cli.openalex import OpenAlexError, search  # noqa: E402
from scholar_cli.ranking import rank  # noqa: E402
from scholar_cli.relevance import filter_and_rank  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE / "results.md"
FILTERED = HERE / "results_filtered.md"
FETCH_N = 10
CANDIDATES = 30  # over-fetch, matching the CLI's search path
TOP_K = 5

HEADER = "| api# | cred# | title | year | venue | cites | link | primary? |"
DIVIDER = "|------|-------|-------|------|-------|-------|------|----------|"


def load_questions() -> list[str]:
    lines = (HERE / "questions.txt").read_text().splitlines()
    return [q.strip() for q in lines if q.strip() and not q.startswith("#")]


def generate() -> int:
    questions = load_questions()
    if len(questions) < 20:
        print(f"note: only {len(questions)}/20 questions — fine for a dry run, "
              f"not enough to publish a number.")

    out = ["# scholar benchmark", "",
           f"Score `primary?` y/n: peer-reviewed primary source (or "
           f"peer-reviewed review) that addresses the question. "
           f"`cred# -` means ranking.py dropped it (retracted).", ""]
    rows = 0
    for q in questions:
        out += [f"## {q}", "", HEADER, DIVIDER]
        try:
            works = search(q, count=FETCH_N)
        except OpenAlexError as exc:
            out += [f"| - | - | SEARCH FAILED: {exc} | | | | | |", ""]
            continue
        cred_pos = {id(w): i + 1 for i, w in enumerate(rank(works))}
        for i, w in enumerate(works, 1):
            link = w.oa_url or w.doi or w.openalex_id or ""
            title = w.title.replace("|", "/")[:90]
            out.append(f"| {i} | {cred_pos.get(id(w), '-')} | {title} "
                       f"| {w.year or ''} | {w.venue or ''} "
                       f"| {w.citations} | {link} | |")
            rows += 1
        out.append("")

    RESULTS.write_text("\n".join(out))
    print(f"wrote {RESULTS} — {rows} rows to score, then run with --tally.")
    return 0


def generate_filtered() -> int:
    """Write the SHIPPED path's top-5 (over-fetch + relevance filter) per
    question, to score the post-filter number."""
    out = ["# scholar benchmark — filtered (shipped path)", "",
           "Relevance filter on; top-5 shown. Score `primary?` y/n by the same "
           "rubric. An empty query = no result cleared the relevance gate.", ""]
    rows = 0
    for q in load_questions():
        out += [f"## {q}", "",
                "| # | rel | title | year | venue | cites | link | primary? |",
                "|---|-----|-------|------|-------|-------|------|----------|"]
        try:
            works = filter_and_rank(q, search(q, count=CANDIDATES), limit=TOP_K)
        except OpenAlexError as exc:
            out += [f"| - | - | SEARCH FAILED: {exc} | | | | | |", ""]
            continue
        if not works:
            out += ["| - | - | (no result cleared the relevance gate) | | | | | |", ""]
            continue
        for i, w in enumerate(works, 1):
            link = w.oa_url or w.doi or w.openalex_id or ""
            title = w.title.replace("|", "/")[:90]
            out.append(f"| {i} | {w.relevance} | {title} | {w.year or ''} "
                       f"| {w.venue or ''} | {w.citations} | {link} | |")
            rows += 1
        out.append("")
    FILTERED.write_text("\n".join(out))
    print(f"wrote {FILTERED} — {rows} rows to score.")
    return 0


def tally() -> int:
    if not RESULTS.exists():
        print("error: no results.md — generate first.", file=sys.stderr)
        return 1
    api_top, cred_top, unscored = [], [], 0
    for line in RESULTS.read_text().splitlines():
        if not line.startswith("|") or line.startswith(("| api#", "|---", "|--")):
            continue
        cells = [c.strip() for c in line.split("|")]
        # cells: ['', api#, cred#, title, year, venue, cites, link, primary?, '']
        if len(cells) < 10 or not cells[1].isdigit():
            continue
        mark = cells[8].lower()
        if mark not in ("y", "n"):
            unscored += 1
            continue
        hit = mark == "y"
        if int(cells[1]) <= TOP_K:
            api_top.append(hit)
        if cells[2].isdigit() and int(cells[2]) <= TOP_K:
            cred_top.append(hit)

    if unscored:
        print(f"{unscored} rows unscored — numbers below are partial.")
    for name, marks in (("API order   ", api_top), ("cred order  ", cred_top)):
        if marks:
            print(f"primary@{TOP_K}, {name}: {sum(marks)}/{len(marks)} "
                  f"= {100 * sum(marks) / len(marks):.0f}%")
        else:
            print(f"primary@{TOP_K}, {name}: no scored rows")
    return 0


if __name__ == "__main__":
    if "--tally" in sys.argv:
        sys.exit(tally())
    elif "--filtered" in sys.argv:
        sys.exit(generate_filtered())
    else:
        sys.exit(generate())
