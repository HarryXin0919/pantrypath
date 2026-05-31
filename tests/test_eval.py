"""Tests for the evaluation harness (Precision@k / MRR / Coverage)."""

import pytest

from pantrypath.eval import EvalReport, evaluate, load_truth
from pantrypath.graph import build_graph, load_default_graph


@pytest.fixture(scope="module")
def sg():
    return load_default_graph()


def test_truth_loads_and_is_nonempty():
    cases = load_truth()
    assert len(cases) >= 10
    for c in cases:
        assert "target" in c and "accept" in c and c["accept"]


def test_metrics_in_range(sg):
    rep = evaluate(sg, load_truth(), k=3)
    assert isinstance(rep, EvalReport)
    assert 0.0 <= rep.precision_at_k <= 1.0
    assert 0.0 <= rep.mrr <= 1.0
    assert 0.0 <= rep.coverage <= 1.0
    assert rep.mrr <= rep.precision_at_k + 1e-9   # MRR can't exceed P@k


def test_engine_is_actually_good(sg):
    # On its own curated ground truth the engine should do very well.
    rep = evaluate(sg, load_truth(), k=3)
    assert rep.coverage == pytest.approx(1.0)     # every case solvable
    assert rep.precision_at_k >= 0.9              # almost all accepted in top-3
    assert rep.mrr >= 0.8                         # and usually ranked first


def test_perfect_case_scores_one():
    # Self-contained mini graph (unique node names => no interaction with anything).
    spec = {
        "ingredients": {"pf_a": {"tags": []}, "pf_b": {"tags": []}, "pf_c": {"tags": []}},
        "substitutions": [{"target": "pf_a",
                           "options": [{"components": ["pf_b", "pf_c"], "cost": 0.3}]}],
    }
    sg = build_graph(spec)
    cases = [{"target": "pf_a", "pantry": ["pf_b", "pf_c"], "accept": [["pf_b", "pf_c"]]}]
    rep = evaluate(sg, cases, k=3)
    assert rep.precision_at_k == pytest.approx(1.0)
    assert rep.mrr == pytest.approx(1.0)
    assert rep.coverage == pytest.approx(1.0)


def test_miss_scores_zero():
    spec = {
        "ingredients": {"ms_a": {"tags": []}, "ms_b": {"tags": []}, "ms_c": {"tags": []}},
        "substitutions": [{"target": "ms_a",
                           "options": [{"components": ["ms_b", "ms_c"], "cost": 0.3}]}],
    }
    sg = build_graph(spec)
    # accepted set is something the engine will never return -> hit rank None
    cases = [{"target": "ms_a", "pantry": ["ms_b", "ms_c"], "accept": [["ms_b"]]}]
    rep = evaluate(sg, cases, k=3)
    assert rep.precision_at_k == pytest.approx(0.0)
    assert rep.mrr == pytest.approx(0.0)
    assert rep.coverage == pytest.approx(1.0)      # solved, just not the accepted set
