"""Tests for recipe-block parsing + batch substitution (Phase 3: 菜谱整段解析)."""

import pytest

from pantrypath.graph import load_default_graph
from pantrypath.recipe import analyze_recipe, parse_recipe


@pytest.fixture(scope="module")
def sg():
    return load_default_graph()


# --------------------------- parsing ---------------------------------------

def test_parse_strips_quantities_and_units(sg):
    text = "2 cups all-purpose flour\n1 cup buttermilk\n1/2 cup sugar"
    got = [p.ingredient for p in parse_recipe(text, sg) if p.ingredient]
    assert got == ["all_purpose_flour", "buttermilk", "sugar"]


def test_parse_longest_match_wins(sg):
    # "powdered milk" must map to powdered_milk, NOT the shorter `milk`.
    got = [p.ingredient for p in parse_recipe("1/2 cup powdered milk", sg) if p.ingredient]
    assert got == ["powdered_milk"]


def test_parse_unmatched_line(sg):
    # vanilla extract is not in the knowledge base -> reported, not crashed.
    parsed = parse_recipe("1 tsp vanilla extract", sg)
    assert len(parsed) == 1 and parsed[0].ingredient is None


def test_parse_comma_separated_single_line(sg):
    got = [p.ingredient for p in parse_recipe("buttermilk, sugar, egg", sg) if p.ingredient]
    assert got == ["buttermilk", "sugar", "egg"]


# --------------------------- analysis --------------------------------------

def test_analyze_splits_have_missing_unmatched(sg):
    recipe = (
        "2 cups all-purpose flour\n"
        "1 cup buttermilk\n"
        "1/2 cup sugar\n"
        "1 large egg\n"
        "1 tsp vanilla extract\n"
    )
    pantry = ["all_purpose_flour", "milk", "white_vinegar", "sugar"]
    report = analyze_recipe(sg, recipe, pantry)

    # already-have recipe ingredients
    assert set(report.have) == {"all_purpose_flour", "sugar"}
    # vanilla isn't known -> unmatched
    assert any("vanilla" in u for u in report.unmatched)

    missing = {ing: res for ing, res in report.missing}
    assert set(missing) == {"buttermilk", "egg"}
    # buttermilk solvable via milk + white_vinegar
    assert missing["buttermilk"].found
    assert missing["buttermilk"].total_cost == pytest.approx(0.15)
    assert set(missing["buttermilk"].leaves()) == {"milk", "white_vinegar"}
    # egg NOT solvable (no flaxseed/water/applesauce in pantry)
    assert not missing["egg"].found


def test_analyze_dedupes_repeated_ingredient(sg):
    report = analyze_recipe(sg, "1 cup buttermilk\n2 tbsp buttermilk", pantry=["milk", "white_vinegar"])
    assert len(report.missing) == 1 and report.missing[0][0] == "buttermilk"


def test_analyze_respects_require_tags(sg):
    # buttermilk from milk+vinegar is NOT vegan -> unsolvable under vegan.
    report = analyze_recipe(sg, "1 cup buttermilk", pantry=["milk", "white_vinegar"],
                            require_tags=["vegan"])
    missing = dict(report.missing)
    assert "buttermilk" in missing and not missing["buttermilk"].found


def test_analyze_compound_and_multihop_together(sg):
    # buttermilk via powdered_milk+water -> milk, then milk+vinegar (multi-hop),
    # plus cake_flour via all_purpose_flour+cornstarch (compound) in one recipe.
    recipe = "1 cup buttermilk\n2 cups cake flour"
    pantry = ["powdered_milk", "water", "white_vinegar", "all_purpose_flour", "cornstarch"]
    report = analyze_recipe(sg, recipe, pantry)
    missing = dict(report.missing)
    assert missing["buttermilk"].found and missing["buttermilk"].total_cost == pytest.approx(0.25)
    assert missing["cake_flour"].found and missing["cake_flour"].total_cost == pytest.approx(0.20)
    assert report.solvable and not report.unsolvable
