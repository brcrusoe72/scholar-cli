"""Credibility ranking — THE core rep. This file is yours, Brian.

v1 ships as a passthrough: OpenAlex relevance order, untouched. That is an
honest baseline — measure it in the benchmark BEFORE improving it, so you
know your ranking actually beats the default instead of assuming it does.

Signals already on every Work, free, no extra requests:

    work.citations     int   — cited_by_count; age-adjust or it favors old papers
    work.venue         str?  — None usually means preprint/dataset, not journal
    work.work_type     str?  — "article", "review", "preprint", "dataset", ...
    work.is_retracted  bool  — a retracted paper should never rank, period
    work.year          int?  — recency, weighed against citation head start
    work.oa_url        str?  — readable now vs. abstract-only

Rules of the game:
- Hard filters first (retracted out), scores second.
- Every weight you pick must move the benchmark number, or it comes back out.
"""

from __future__ import annotations

from .openalex import Work


def rank(works: list[Work]) -> list[Work]:
    # TODO(Brian): replace passthrough with credibility ranking.
    return works
