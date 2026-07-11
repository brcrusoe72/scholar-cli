"""Relevance filter — pure logic, built around the real benchmark failures."""

from scholar_cli.openalex import Work
from scholar_cli.relevance import content_terms, filter_and_rank, score


def _w(title, abstract="", **kw):
    base = dict(year=2020, doi=None, venue="J", citations=10, oa_url=None,
                is_retracted=False, openalex_id=None)
    base.update(kw)
    return Work(title=title, abstract=abstract, **base)


def test_content_terms_drops_stopwords_and_short():
    terms = content_terms("does overall equipment effectiveness affect it")
    assert "overall" in terms and "equipment" in terms and "effectiveness" in terms
    assert "does" not in terms and "it" not in terms


def test_prefix_match_handles_plurals():
    q = content_terms("packaging line stoppage")
    assert score(q, ["lines"]) > 0             # line→lines
    assert score(q, ["packaged", "goods"]) > 0  # packag* shared stem


def test_phrase_match_beats_scattered_words():
    q = content_terms("operator cross training production line performance")
    # Same words, wrong combination (bank performance / sheep production).
    scattered = content_terms("bank environmental performance and green production practices")
    # The real phrase present.
    on_topic = content_terms("operator cross training on the production line improves performance")
    assert score(q, on_topic) > score(q, scattered)


def test_the_actual_botany_false_positive_is_dropped():
    # Q1 from the benchmark: this scored a top slot but is off-topic.
    query = "does overall equipment effectiveness correlate with plant profitability"
    botany = _w("Natural Antioxidants in Foods and Medicinal Plants: Extraction")
    on_topic = _w("Managing overall equipment effectiveness to optimize factory profitability",
                  abstract="We study how OEE affects plant profitability and equipment performance.")
    kept = filter_and_rank(query, [botany, on_topic], min_relevance=0.30, limit=10)
    titles = [w.title for w in kept]
    assert on_topic.title in titles
    assert botany.title not in titles  # matched only "plant" — dropped


def test_retracted_dropped_even_if_relevant():
    query = "shift work sleep metabolism"
    r = _w("Shift work disrupts sleep and metabolism", is_retracted=True,
           abstract="shift work sleep metabolism circadian")
    kept = filter_and_rank(query, [r], min_relevance=0.30, limit=10)
    assert kept == []


def test_relevance_score_recorded_on_results():
    query = "preventive maintenance downtime"
    w = _w("Preventive maintenance reduces unplanned downtime",
           abstract="preventive maintenance downtime reliability")
    kept = filter_and_rank(query, [w], min_relevance=0.30, limit=10)
    assert kept and kept[0].relevance is not None and kept[0].relevance > 0.5
