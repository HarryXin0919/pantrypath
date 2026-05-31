"""Unit tests for the PantryPath solver."""

import pytest

from pantrypath.graph import build_graph, load_default_graph
from pantrypath.solver import solve


@pytest.fixture(scope="module")
def sg():
    return load_default_graph()


def test_already_have(sg):
    res = solve(sg, "milk", pantry=["milk"])
    assert res.found and res.total_cost == 0.0 and res.steps == []


def test_compound_buttermilk(sg):
    # The headline example: buttermilk = milk + vinegar.
    res = solve(sg, "buttermilk", pantry=["milk", "white_vinegar"])
    assert res.found
    assert set(res.leaves()) == {"milk", "white_vinegar"}
    assert res.total_cost == pytest.approx(0.15)


def test_picks_cheapest_option(sg):
    # With both milk+vinegar (0.15) and yogurt+water (0.20) possible, choose cheaper.
    res = solve(sg, "buttermilk",
                pantry=["milk", "white_vinegar", "plain_yogurt", "water"])
    assert res.total_cost == pytest.approx(0.15)


def test_multi_hop_chain(sg):
    # No milk, but powdered_milk + water -> milk, then milk + vinegar -> buttermilk.
    res = solve(sg, "buttermilk", pantry=["powdered_milk", "water", "white_vinegar"])
    assert res.found
    assert set(res.leaves()) == {"powdered_milk", "water", "white_vinegar"}
    # milk (0.10) + buttermilk step (0.15) = 0.25
    assert res.total_cost == pytest.approx(0.25)


def test_no_solution(sg):
    res = solve(sg, "buttermilk", pantry=["sugar", "salt"])
    assert not res.found


def test_unknown_ingredient(sg):
    res = solve(sg, "unobtanium", pantry=["milk"])
    assert not res.found


def test_dietary_filter_blocks_dairy(sg):
    # egg via flaxseed+water is vegan; applesauce is vegan too. Require vegan -> still found.
    res = solve(sg, "egg", pantry=["flaxseed", "water"], require_tags=["vegan"])
    assert res.found and set(res.leaves()) == {"flaxseed", "water"}


def test_dietary_filter_rejects(sg):
    # buttermilk from milk+vinegar is NOT vegan (milk lacks the tag) -> blocked.
    res = solve(sg, "buttermilk", pantry=["milk", "white_vinegar"],
                require_tags=["vegan"])
    assert not res.found


def test_tiny_handbuilt_graph():
    spec = {
        "ingredients": {"a": {"tags": []}, "b": {"tags": []}, "c": {"tags": []}},
        "substitutions": [
            {"target": "a", "options": [{"components": ["b", "c"], "cost": 0.5}]},
        ],
    }
    sg = build_graph(spec)
    res = solve(sg, "a", pantry=["b", "c"])
    assert res.found and res.total_cost == pytest.approx(0.5)
    assert set(res.leaves()) == {"b", "c"}
