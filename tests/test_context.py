"""Context layer: one pure unit test + live contract tests (network)."""

import pytest

from scholar_cli.openalex import _deinvert, citing_works, get_work

# Gut-microbiome/depression systematic review (IJMS 2022) — stable, and unlike
# many older Nature papers it has an OPEN abstract in OpenAlex, plus 123 refs
# and 180+ citers, so all three context layers are populated.
KNOWN_DOI = "10.3390/ijms23094494"


def test_deinvert_rebuilds_word_order():
    inverted = {"context": [1], "deep": [0], "deep.": [3], "layered": [2]}
    assert _deinvert(inverted) == "deep context layered deep."


def test_get_work_by_doi_returns_abstract_and_edges():
    work, refs, related = get_work(KNOWN_DOI)
    assert "microbiome" in work.title.lower()
    assert work.abstract and len(work.abstract) > 100
    assert refs, "expected referenced_works"
    assert work.openalex_id


def test_citing_works_returns_ranked_citers():
    work, _, _ = get_work(KNOWN_DOI)
    citers = citing_works(work.openalex_id, count=3)
    assert len(citers) == 3
    assert all(c.citations > 0 for c in citers)


def test_garbage_ref_raises_value_error_not_silent():
    with pytest.raises(ValueError):
        get_work("not a doi at all")
