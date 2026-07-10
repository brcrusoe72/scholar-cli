"""Output formatting: human lines for the terminal, JSON for agents."""

from __future__ import annotations

import dataclasses
import json

from .openalex import Work


def to_json(works: list[Work]) -> str:
    return json.dumps([dataclasses.asdict(w) for w in works], indent=2)


def to_terminal(works: list[Work]) -> str:
    if not works:
        return "No results."
    lines = []
    for i, w in enumerate(works, 1):
        authors = ", ".join(w.authors) if w.authors else "unknown authors"
        venue = w.venue or "no venue (preprint/dataset?)"
        flags = []
        if w.is_retracted:
            flags.append("RETRACTED")
        if w.oa_url:
            flags.append("open access")
        flag_str = f"  [{', '.join(flags)}]" if flags else ""
        lines.append(f"{i}. {w.title} ({w.year}){flag_str}")
        lines.append(f"   {authors} — {venue} — {w.citations} citations")
        lines.append(f"   {w.oa_url or w.doi or w.openalex_id or ''}")
        lines.append("")
    return "\n".join(lines).rstrip()
