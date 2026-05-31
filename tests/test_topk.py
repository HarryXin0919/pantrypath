"""Tests for Top-k alternative substitutions (k-best rules per target)."""

import pytest

from pantrypath.graph import load_default_graph
from pantrypath.solver import solve, solve_topk


@pytest.fixture(scope="module")
def sg():
    return load_default_graph()


def test_topk_returns_ranked_alternatives(sg):
    # buttermilk has 4 rules; with all components on hand we should see several,
    # sorted by non-decreasing cost, deduped, capped at k.
    res = solve_topk(sg, "buttermilk",
                     pantry=["milk", "white_vinegar", "lemon_juice", "plain_yogurt", "water"],
                     k=3)
    assert len(res) == 3
    costs = [r.total_cost for r in res]
    assert costs == sorted(costs)              # ranked best-first
    assert costs[0] == pytest.approx(0.15)     # milk + (vinegar|lemon)
    assert costs[-1] == pytest.approx(0.20)    # yogurt + water
    # every alternative is a real, found solution with a tree
    assert all(r.found and r.tree is not None for r in res)


def test_topk_first_equals_solve(sg):
    pantry = ["milk", "white_vinegar", "plain_yogurt", "water"]
    best = solve(sg, "buttermilk", pantry)
    top = solve_topk(sg, "buttermilk", pantry, k=3)
    assert top[0].total_cost == pytest.approx(best.total_cost)
    assert set(top[0].leaves()) == set(best.leaves())


def test_topk_distinct_component_sets(sg):
    res = solve_topk(sg, "buttermilk",
                     pantry=["milk", "white_vinegar", "lemon_juice", "plain_yogurt", "water"],
                     k=5)
    # alternatives must differ in their actual ingredients used
    leafsets = [frozenset(r.leaves()) for r in res]
    assert len(leafsets) == len(set(leafsets))


def test_topk_k_larger_than_available(sg):
    # only milk+vinegar possible here -> exactly 1 alternative even if k=5
    res = solve_topk(sg, "buttermilk", pantry=["milk", "white_vinegar"], k=5)
    assert len(res) == 1
    assert res[0].total_cost == pytest.approx(0.15)


def test_topk_already_have(sg):
    res = solve_topk(sg, "milk", pantry=["milk"], k=3)
    assert len(res) == 1 and res[0].total_cost == 0.0 and res[0].steps == []


def test_topk_no_solution(sg):
    assert solve_topk(sg, "buttermilk", pantry=["sugar", "salt"], k=3) == []


def test_topk_respects_tags(sg):
    # vegan buttermilk impossible (milk not vegan) -> no alternatives
    res = solve_topk(sg, "buttermilk", pantry=["milk", "white_vinegar"],
                     k=3, require_tags=["vegan"])
    assert res == []


def test_topk_multihop_alternative(sg):
    # milk itself has two rules (powdered_milk+water 0.10, heavy_cream+water 0.12);
    # both available -> two ranked alternatives.
    res = solve_topk(sg, "milk", pantry=["powdered_milk", "heavy_cream", "water"], k=3)
    costs = [r.total_cost for r in res]
    assert costs == sorted(costs)
    assert costs[0] == pytest.approx(0.10)
    assert costs[1] == pytest.approx(0.12)
