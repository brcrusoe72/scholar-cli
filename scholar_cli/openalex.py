"""OpenAlex client — the one source in v1.

Design rules for this module:
- No API key, no server, no fallback chain. One typed request, one typed response.
- Errors are LOUD. A failed request raises OpenAlexError with the real status
  and body. Nothing returns an empty list to hide a failure (see: the wolf
  case study — silent 401s look identical to "no results").
- `select=` trims the payload to only the fields we use. Smaller responses,
  fewer tokens when an agent pipes --json.
"""

from __future__ import annotations

import os
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


def search(
    query: str,
    since: int | None = None,
    oa_only: bool = False,
    count: int = 10,
    mailto: str | None = None,
) -> list[Work]:
    """Search OpenAlex works, relevance-ordered.

    `mailto` (or env SCHOLAR_MAILTO) opts into OpenAlex's polite pool:
    same data, better rate limits. https://docs.openalex.org/how-to-use-the-api
    """
    params: dict[str, str | int] = {
        "search": query,
        "per-page": count,
        "select": SELECT_FIELDS,
    }
    filters = []
    if since is not None:
        filters.append(f"from_publication_date:{since}-01-01")
    if oa_only:
        filters.append("open_access.is_oa:true")
    if filters:
        params["filter"] = ",".join(filters)
    mailto = mailto or os.environ.get("SCHOLAR_MAILTO")
    if mailto:
        params["mailto"] = mailto

    try:
        resp = httpx.get(WORKS_URL, params=params, timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        raise OpenAlexError(f"OpenAlex request failed: {exc!r}") from exc

    if resp.status_code != 200:
        raise OpenAlexError(
            f"OpenAlex returned HTTP {resp.status_code}: {resp.text[:300]}"
        )

    body = resp.json()
    if "results" not in body:
        raise OpenAlexError(
            f"OpenAlex response missing 'results' key: {str(body)[:300]}"
        )

    return [_parse_work(raw) for raw in body["results"]]


def _parse_work(raw: dict) -> Work:
    # OpenAlex nests venue under primary_location.source; either level can be
    # null (preprints, datasets), so guard each hop.
    source = (raw.get("primary_location") or {}).get("source") or {}
    open_access = raw.get("open_access") or {}
    authors = [
        (a.get("author") or {}).get("display_name")
        for a in (raw.get("authorships") or [])[:3]
    ]
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
    )
