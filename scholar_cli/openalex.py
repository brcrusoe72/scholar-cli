"""OpenAlex client — the one source in v1.

Design rules for this module:
- No API key, no server, no fallback chain. Typed requests, typed responses.
- Errors are LOUD. A failed request raises OpenAlexError with the real status
  and body. Nothing returns an empty list to hide a failure (see: the wolf
  case study — silent 401s look identical to "no results").
- `select=` trims the payload to only the fields we use. Smaller responses,
  fewer tokens when an agent pipes --json.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import httpx

WORKS_URL = "https://api.openalex.org/works"
TIMEOUT_SECONDS = 15.0

# Only what render/ranking actually consume. Add a field here only when
# something downstream reads it.
SELECT_FIELDS = ",".join(
    [
        "id",
        "display_name",
        "publication_year",
        "doi",
        "type",
        "cited_by_count",
        "is_retracted",
        "primary_location",
        "open_access",
        "authorships",
    ]
)

# Search pulls abstracts too — the relevance filter scores against title +
# abstract, and one common word in a title isn't enough to judge topic.
SEARCH_SELECT = SELECT_FIELDS + ",abstract_inverted_index"

# The single-work fetch also pulls the context layers: abstract + graph edges.
CONTEXT_SELECT = SELECT_FIELDS + ",abstract_inverted_index,referenced_works,related_works"


class OpenAlexError(RuntimeError):
    """Raised on any non-success from OpenAlex. Never swallowed."""


@dataclass
class Work:
    title: str
    year: int | None
    doi: str | None
    venue: str | None
    citations: int
    oa_url: str | None
    authors: list[str] = field(default_factory=list)
    work_type: str | None = None
    is_retracted: bool = False
    openalex_id: str | None = None
    abstract: str | None = None
    relevance: float | None = None


def search(
    query: str,
    since: int | None = None,
    oa_only: bool = False,
    count: int = 10,
    mailto: str | None = None,
) -> list[Work]:
    """Search OpenAlex works, relevance-ordered. Includes abstracts so the
    relevance filter has enough text to judge topic."""
    params: dict[str, str | int] = {
        "search": query,
        "per-page": count,
        "select": SEARCH_SELECT,
    }
    filters = []
    if since is not None:
        filters.append(f"from_publication_date:{since}-01-01")
    if oa_only:
        filters.append("open_access.is_oa:true")
    if filters:
        params["filter"] = ",".join(filters)
    body = _get(WORKS_URL, params, mailto)
    return _parse_results(body)


def get_work(ref: str, mailto: str | None = None) -> tuple[Work, list[str], list[str]]:
    """Fetch one work by DOI or OpenAlex ID, plus its graph edges.

    Returns (work, referenced_work_ids, related_work_ids).
    Raises ValueError if `ref` doesn't look like a DOI/ID — callers may then
    fall back to resolving it as a search query.
    """
    body = _get(f"{WORKS_URL}/{_normalize_ref(ref)}", {"select": CONTEXT_SELECT}, mailto)
    return (
        _parse_work(body),
        body.get("referenced_works") or [],
        body.get("related_works") or [],
    )


def works_by_ids(ids: list[str], mailto: str | None = None) -> list[Work]:
    """Batch-fetch works by OpenAlex ID (max 50 per request)."""
    if not ids:
        return []
    short = [i.rsplit("/", 1)[-1] for i in ids][:50]
    params = {
        "filter": "ids.openalex:" + "|".join(short),
        "select": SELECT_FIELDS,
        "per-page": len(short),
    }
    return _parse_results(_get(WORKS_URL, params, mailto))


def citing_works(work_id: str, count: int = 5, mailto: str | None = None) -> list[Work]:
    """Most-cited works that cite this one — the forward layer."""
    params = {
        "filter": f"cites:{work_id.rsplit('/', 1)[-1]}",
        "sort": "cited_by_count:desc",
        "per-page": count,
        "select": SELECT_FIELDS,
    }
    return _parse_results(_get(WORKS_URL, params, mailto))


def _get(url: str, params: dict, mailto: str | None = None) -> dict:
    # `mailto` (or env SCHOLAR_MAILTO) opts into OpenAlex's polite pool:
    # same data, better rate limits.
    mailto = mailto or os.environ.get("SCHOLAR_MAILTO")
    if mailto:
        params["mailto"] = mailto
    try:
        resp = httpx.get(url, params=params, timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        raise OpenAlexError(f"OpenAlex request failed: {exc!r}") from exc
    if resp.status_code != 200:
        raise OpenAlexError(
            f"OpenAlex returned HTTP {resp.status_code}: {resp.text[:300]}"
        )
    return resp.json()


def _parse_results(body: dict) -> list[Work]:
    if "results" not in body:
        raise OpenAlexError(
            f"OpenAlex response missing 'results' key: {str(body)[:300]}"
        )
    return [_parse_work(raw) for raw in body["results"]]


def _normalize_ref(ref: str) -> str:
    ref = ref.strip()
    if "openalex.org/" in ref:
        return ref.rsplit("/", 1)[-1]
    if ref.lower().startswith("doi:"):
        return ref
    if "doi.org/" in ref:
        return "doi:" + ref.split("doi.org/", 1)[1]
    if ref.startswith("10."):
        return "doi:" + ref
    if re.fullmatch(r"[Ww]\d+", ref):
        return ref.upper()
    raise ValueError(f"not a DOI or OpenAlex ID: {ref!r}")


def _parse_work(raw: dict) -> Work:
    # OpenAlex nests venue under primary_location.source; either level can be
    # null (preprints, datasets), so guard each hop.
    source = (raw.get("primary_location") or {}).get("source") or {}
    open_access = raw.get("open_access") or {}
    authors = [
        (a.get("author") or {}).get("display_name")
        for a in (raw.get("authorships") or [])[:3]
    ]
    inverted = raw.get("abstract_inverted_index")
    return Work(
        title=raw.get("display_name") or "(untitled)",
        year=raw.get("publication_year"),
        doi=raw.get("doi"),
        venue=source.get("display_name"),
        citations=raw.get("cited_by_count") or 0,
        oa_url=open_access.get("oa_url"),
        authors=[a for a in authors if a],
        work_type=raw.get("type"),
        is_retracted=bool(raw.get("is_retracted")),
        openalex_id=raw.get("id"),
        abstract=_deinvert(inverted) if inverted else None,
    )


def _deinvert(inverted: dict[str, list[int]]) -> str:
    # OpenAlex ships abstracts as {word: [positions]}; flatten back to text.
    return " ".join(w for _, w in sorted(
        (pos, word) for word, positions in inverted.items() for pos in positions
    ))
