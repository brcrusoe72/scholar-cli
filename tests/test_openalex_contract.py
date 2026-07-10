"""Contract tests against the LIVE OpenAlex API (network required).

Three real requests that verify the API still honors the contract we depend
on. This catches the failure that actually kills tools like this — the
upstream API changing shape — which 500 lines of mocks never would.

Run: uv run pytest
"""

import pytest

from scholar_cli.openalex import OpenAlexError, search


def test_search_returns_parsed_works():
    works = search("photosynthesis efficiency", count=5)
    assert len(works) == 5
    for w in works:
        assert w.title
        assert isinstance(w.citations, int)
        assert isinstance(w.is_retracted, bool)


def test_since_filter_is_respected():
    works = search("machine learning", since=2023, count=10)
    assert works, "expected results for a broad query"
    years = [w.year for w in works if w.year is not None]
    assert years and min(years) >= 2023


def test_bad_filter_fails_loud_not_empty():
    # An invalid filter must raise, not come back as zero results.
    with pytest.raises(OpenAlexError):
        search("anything", since="banana", count=5)  # type: ignore[arg-type]
