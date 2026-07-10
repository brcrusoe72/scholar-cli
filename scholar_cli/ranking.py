"""Credibility ranking.

Two-layer design:
1. Hard filters — a retracted paper never ranks, period.
2. Scoring — relevance (the API's order) is the STRONGEST signal, because a
   mega-cited paper that's off-topic is worse than an on-topic one. Credibility
   signals re-rank within relevance, they don't replace it.

Every constant below is a hypothesis, not a fact. The benchmark tally
(benchmark/run_benchmark.py --tally) compares this ordering against raw API
order; a weight that doesn't move that number comes back out.
"""

from __future__ import annotations

import math
from datetime import date

from .openalex import Work

# Top-relevance result starts this far ahead of the bottom one.
RELEVANCE_WEIGHT = 3.0
# Citations are log-scaled and age-adjusted (citations per year), so a 2023
# paper with 150 cites can outrank a 2002 paper coasting on age.
CITATION_WEIGHT = 1.5
# Venue present = it cleared some editorial bar; None usually means
# preprint server, dataset, or paratext.
VENUE_BONUS = 1.0
TYPE_BONUS = {"article": 1.0, "review": 1.0, "book-chapter": 0.5}
# Readable right now beats abstract-only.
OA_BONUS = 0.5


def rank(works: list[Work]) -> list[Work]:
    kept = [w for w in works if not w.is_retracted]
    n = len(kept)
    if n == 0:
        return []
    scored = [(_score(w, idx, n), idx, w) for idx, w in enumerate(kept)]
    # Stable on ties: equal scores keep relevance order.
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [w for _, _, w in scored]


def _score(w: Work, idx: int, n: int) -> float:
    score = RELEVANCE_WEIGHT * (n - idx) / n
    score += CITATION_WEIGHT * math.log10(1 + _citations_per_year(w))
    if w.venue:
        score += VENUE_BONUS
    score += TYPE_BONUS.get(w.work_type or "", 0.0)
    if w.oa_url:
        score += OA_BONUS
    return score


def _citations_per_year(w: Work) -> float:
    if not w.year:
        return 0.0
    age = max(1, date.today().year - w.year + 1)
    return w.citations / age
