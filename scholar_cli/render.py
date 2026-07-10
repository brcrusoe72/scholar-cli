"""Output formatting: human lines for the terminal, JSON for agents."""

from __future__ import annotations

import dataclasses
import json
import textwrap

from .openalex import Work

ABSTRACT_WRAP = 96


def to_json(works: list[Work]) -> str:
    return json.dumps([dataclasses.asdict(w) for w in works], indent=2)


def to_terminal(works: list[Work]) -> str:
    if not works:
        return "No results."
    lines = []
    for i, w in enumerate(works, 1):
        lines += _work_lines(w, prefix=f"{i}. ")
        lines.append("")
    return "\n".join(lines).rstrip()


def context_to_json(work: Work, refs: list[Work], citing: list[Work],
                    related: list[Work]) -> str:
    return json.dumps({
        "work": dataclasses.asdict(work),
        "builds_on": [dataclasses.asdict(w) for w in refs],
        "cited_by": [dataclasses.asdict(w) for w in citing],
        "related": [dataclasses.asdict(w) for w in related],
    }, indent=2)


def context_to_terminal(work: Work, refs: list[Work], citing: list[Work],
                        related: list[Work]) -> str:
    lines = _work_lines(work, prefix="")
    if work.abstract:
        lines.append("")
        lines += textwrap.wrap("Abstract: " + work.abstract, width=ABSTRACT_WRAP)
    for title, group in (
        ("Builds on (its most credible references)", refs),
        ("Cited by (what built on it)", citing),
        ("Related", related),
    ):
        lines += ["", f"── {title} " + "─" * max(0, 60 - len(title))]
        lines.append(to_terminal(group) if group else "(none found)")
    return "\n".join(lines)


def _work_lines(w: Work, prefix: str) -> list[str]:
    authors = ", ".join(w.authors) if w.authors else "unknown authors"
    venue = w.venue or "no venue (preprint/dataset?)"
    flags = []
    if w.is_retracted:
        flags.append("RETRACTED")
    if w.oa_url:
        flags.append("open access")
    flag_str = f"  [{', '.join(flags)}]" if flags else ""
    pad = " " * len(prefix)
    return [
        f"{prefix}{w.title} ({w.year}){flag_str}",
        f"{pad}{authors} — {venue} — {w.citations} citations",
        f"{pad}{w.oa_url or w.doi or w.openalex_id or ''}",
    ]
