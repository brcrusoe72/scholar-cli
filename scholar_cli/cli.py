"""scholar — scholarly search CLI for AI agents.

    scholar "gut microbiome depression" --since 2022 --oa
    scholar "constraint management OEE" --json
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .openalex import OpenAlexError, search
from .ranking import rank
from .render import to_json, to_terminal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scholar",
        description="Scholarly search CLI for AI agents. One source (OpenAlex), no API key.",
    )
    parser.add_argument("query", help="search query")
    parser.add_argument("--since", type=int, metavar="YEAR", help="only works published in YEAR or later")
    parser.add_argument("--oa", action="store_true", help="open-access works only")
    parser.add_argument("--count", type=int, default=10, help="number of results (default 10)")
    parser.add_argument("--json", action="store_true", help="JSON output for agents")
    parser.add_argument("--mailto", help="email for OpenAlex polite pool (or env SCHOLAR_MAILTO)")
    parser.add_argument("--version", action="version", version=f"scholar {__version__}")
    args = parser.parse_args(argv)

    try:
        works = search(
            args.query,
            since=args.since,
            oa_only=args.oa,
            count=args.count,
            mailto=args.mailto,
        )
    except OpenAlexError as exc:
        # Loud and unmistakable. An agent must never mistake a failure for
        # "no results" — exit code + stderr, never an empty success payload.
        print(f"error: {exc}", file=sys.stderr)
        return 1

    works = rank(works)
    print(to_json(works) if args.json else to_terminal(works))
    return 0


if __name__ == "__main__":
    sys.exit(main())
