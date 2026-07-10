"""Unit tests for ranking — pure logic, no network.

(Contract tests hit the live API; ranking is deterministic, so it gets
plain unit tests. Different failure modes, different test styles.)
"""

from datetime import date

from scholar_cli.openalex import Work
from scholar_cli.ranking import rank


def _work(**kw) -> Work:
    base = dict(
        title="t", year=None, doi=None, venue=None, citations=0,
        oa_url=None, authors=[], work_type=None, is_retracted=False,
        openalex_id=None,
    )
    base.update(kw)
    return Work(**base)


def test_retracted_is_hard_dropped():
    works = [_work(title="bad", is_retracted=True), _work(title="good")]
    ranked = rank(works)
    assert [w.title for w in ranked] == ["good"]


def test_credible_paper_climbs_over_bare_relevance():
    thin = _work(title="thin")  # relevance slot 1, no signals
    strong = _work(
        title="strong",
        year=date.today().year,
        citations=200,
        venue="Real Journal",
        work_type="article",
        oa_url="https://example.org/pdf",
    )
    ranked = rank([thin, strong])
    assert ranked[0].title == "strong"


def test_ties_keep_relevance_order():
    a, b = _work(title="first"), _work(title="second")
    ranked = rank([a, b])
    assert [w.title for w in ranked] == ["first", "second"]
