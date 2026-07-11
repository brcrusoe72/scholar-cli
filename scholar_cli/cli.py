"""scholar — scholarly search CLI for AI agents.

    scholar "gut microbiome depression" --since 2022 --oa
    scholar context 10.1038/nature14539
    scholar context "attention is all you need" --json
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .openalex import OpenAlexError, citing_works, get_work, search, works_by_ids
from .ranking import rank
from .relevance import DEFAULT_MIN_RELEVANCE, filter_and_rank
from .render import context_to_json, context_to_terminal, to_json, to_terminal

REFS_SHOWN = 5
CITING_SHOWN = 5
RELATED_SHOWN = 3


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Subcommand-optional: `scholar context X` dispatches, anything else is a
    # search, so `scholar "query"` keeps working for agents and humans alike.
    if argv and argv[0] == "context":
        return _context_cmd(argv[1:])
    if argv and argv[0] == "search":
        argv = argv[1:]
    return _search_cmd(argv)


def _search_cmd(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="scholar",
        description="Scholarly search CLI for AI agents. One source (OpenAlex), no API key. "
        "Subcommands: search (default), context.",
    )
    parser.add_argument("query", help="search query")
    parser.add_argument("--since", type=int, metavar="YEAR", help="only works published in YEAR or later")
    parser.add_argument("--oa", action="store_true", help="open-access works only")
    parser.add_argument("--count", type=int, default=10, help="number of results (default 10)")
    parser.add_argument("--min-relevance", type=float, default=DEFAULT_MIN_RELEVANCE,
                        metavar="0-1", help=f"drop results below this query-coverage score "
                        f"(default {DEFAULT_MIN_RELEVANCE}; 0 disables)")
    parser.add_argument("--no-filter", action="store_true",
                        help="skip the relevance filter (raw OpenAlex order)")
    parser.add_argument("--json", action="store_true", help="JSON output for agents")
    parser.add_argument("--mailto", help="email for OpenAlex polite pool (or env SCHOLAR_MAILTO)")
    parser.add_argument("--version", action="version", version=f"scholar {__version__}")
    args = parser.parse_args(argv)

    # Over-fetch candidates so the filter can surface on-topic papers OpenAlex
    # ranked below the ambiguous-keyword noise, then gate + order down to count.
    candidate_count = min(max(args.count * 3, 25), 50)
    try:
        candidates = search(
            args.query, since=args.since, oa_only=args.oa,
            count=candidate_count, mailto=args.mailto,
        )
    except OpenAlexError as exc:
        return _fail(exc)

    if args.no_filter:
        works = rank(candidates)[: args.count]
    else:
        works = filter_and_rank(
            args.query, candidates,
            min_relevance=args.min_relevance, limit=args.count,
        )
    print(to_json(works) if args.json else to_terminal(works))
    return 0


def _context_cmd(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="scholar context",
        description="Deep context for one work: abstract, what it builds on "
        "(references), what built on it (citations), and related work.",
    )
    parser.add_argument("work", help="DOI, OpenAlex ID, or a title to resolve via search")
    parser.add_argument("--json", action="store_true", help="JSON output for agents")
    parser.add_argument("--mailto", help="email for OpenAlex polite pool (or env SCHOLAR_MAILTO)")
    args = parser.parse_args(argv)

    try:
        try:
            work, ref_ids, rel_ids = get_work(args.work, mailto=args.mailto)
        except ValueError:
            # Not a DOI/ID — resolve as a search query, take the top hit.
            hits = search(args.work, count=1, mailto=args.mailto)
            if not hits or not hits[0].openalex_id:
                print(f"error: no work found for {args.work!r}", file=sys.stderr)
                return 1
            work, ref_ids, rel_ids = get_work(hits[0].openalex_id, mailto=args.mailto)

        refs = rank(works_by_ids(ref_ids[:50], mailto=args.mailto))[:REFS_SHOWN]
        citing = citing_works(work.openalex_id or "", count=CITING_SHOWN, mailto=args.mailto) \
            if work.openalex_id else []
        related = rank(works_by_ids(rel_ids[:10], mailto=args.mailto))[:RELATED_SHOWN]
    except OpenAlexError as exc:
        return _fail(exc)

    if args.json:
        print(context_to_json(work, refs, citing, related))
    else:
        print(context_to_terminal(work, refs, citing, related))
    return 0


def _fail(exc: OpenAlexError) -> int:
    # Loud and unmistakable. An agent must never mistake a failure for
    # "no results" — exit code + stderr, never an empty success payload.
    print(f"error: {exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
