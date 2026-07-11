"""Query-relevance filter — the fix the benchmark pointed to.

The benchmark showed scholar's failure mode is lexical ambiguity: OpenAlex
returns a paper because it matches ONE common word from the query ("plant"
profitability → botany papers) while missing the query's specific terms.

The fix, deterministic and LLM-free: score each result by how much of the
query it actually covers — weighting longer / more-specific terms more, so
matching just "plant" can't carry a result that misses "equipment",
"effectiveness", "profitability". Drop anything below a threshold, then order
the survivors. This is a relevance GATE, not another ranking weight.

Matching is morphology-tolerant without a stemmer: two words match if the
shorter (≥4 chars) is a prefix of the longer, so plant/plants,
profit/profitability, line/lines all match.
"""

from __future__ import annotations

import re

from .openalex import Work
from .ranking import rank

# Generic English + research-question scaffolding. These never signal topic.
STOPWORDS = {
    "the", "a", "an", "of", "on", "in", "to", "for", "and", "or", "with",
    "is", "are", "was", "were", "be", "been", "being", "by", "as", "at",
    "from", "that", "this", "these", "those", "it", "its", "into", "than",
    "then", "not", "no", "nor", "but", "if", "can", "could", "may", "might",
    "does", "do", "did", "what", "how", "why", "when", "where", "which",
    "who", "whom", "whose", "whether", "about", "evidence", "versus", "vs",
    "using", "use", "between", "among", "their", "there",
}

# Empirically tuned (n=20): on-topic papers score 0.40–0.80; the best
# off-topic noise on ambiguous-keyword queries tops out ~0.38. So 0.40 keeps
# real matches and drops the noise — an unmatched query returns empty, which
# is more honest than five off-topic papers. Override with --min-relevance.
DEFAULT_MIN_RELEVANCE = 0.40
_WORD = re.compile(r"[a-z0-9]+")


def content_terms(text: str) -> list[str]:
    """Lowercase topic words: stopwords and 1–2 char tokens removed."""
    return [w for w in _WORD.findall((text or "").lower())
            if w not in STOPWORDS and len(w) >= 3]


def _common_prefix_len(a: str, b: str) -> int:
    n = 0
    for ca, cb in zip(a, b):
        if ca != cb:
            break
        n += 1
    return n


def _matches(a: str, b: str) -> bool:
    if a == b:
        return True
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    # Two ways to match, no stemmer:
    #  - shorter (≥4) is a prefix of longer: plant→plants, line→lines, stop→stoppage
    #  - they share a ≥5-char stem: packaging↔packaged, maintain↔maintenance
    # Both stay tight enough to avoid art→party (shared prefix 0).
    if len(short) >= 4 and long.startswith(short):
        return True
    return _common_prefix_len(a, b) >= 5


def _present(term: str, text_words: set[str]) -> bool:
    return any(_matches(term, w) for w in text_words)


def _adjacent(a: str, b: str, seq: list[str]) -> bool:
    """Do query terms a, b appear as an adjacent pair in the text sequence?"""
    return any(_matches(a, seq[i]) and _matches(b, seq[i + 1])
               for i in range(len(seq) - 1))


# Term coverage says "are the query's words here?"; phrase coverage says "in
# the right combination?" — the latter is what separates a real "production
# line" paper from a sheep-"production" / "performance" false positive.
_TERM_W, _PHRASE_W = 0.6, 0.4


def score(query_terms: list[str], text_seq: list[str]) -> float:
    """Blend of weighted term coverage and adjacent-phrase coverage, in [0,1]."""
    if not query_terms:
        return 0.0
    text_words = set(text_seq)
    total = sum(len(t) for t in query_terms)
    hit = sum(len(t) for t in query_terms if _present(t, text_words))
    term_cov = hit / total

    bigrams = list(zip(query_terms, query_terms[1:]))
    if not bigrams:  # 1-word query: no phrase signal to add
        return term_cov
    phrase_cov = sum(_adjacent(a, b, text_seq) for a, b in bigrams) / len(bigrams)
    return _TERM_W * term_cov + _PHRASE_W * phrase_cov


def filter_and_rank(
    query: str,
    works: list[Work],
    min_relevance: float = DEFAULT_MIN_RELEVANCE,
    limit: int = 10,
) -> list[Work]:
    """Score works against the query, drop off-topic and retracted, then order
    by relevance (0.1 bands) with credibility as the in-band tiebreak."""
    query_terms = content_terms(query)
    for w in works:
        text_seq = content_terms(f"{w.title or ''} {w.abstract or ''}")
        w.relevance = round(score(query_terms, text_seq), 3)

    survivors = [w for w in works
                 if not w.is_retracted and (w.relevance or 0) >= min_relevance]

    # Credibility (ranking.py) only breaks ties between similarly-relevant
    # papers — relevance leads, per the benchmark finding.
    cred_index = {id(w): i for i, w in enumerate(rank(survivors))}
    survivors.sort(key=lambda w: (-round((w.relevance or 0) * 10), cred_index[id(w)]))
    return survivors[:limit]
