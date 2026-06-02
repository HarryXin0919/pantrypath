"""Spec-validation, dedupe, --version, and bilingual-output tests.

These cover the contributor-facing robustness work: editing substitutions.yaml
should fail with a precise message, not a cryptic KeyError/AttributeError.
"""

import pytest

import pantrypath
from pantrypath.cli import main
from pantrypath.graph import InvalidSpecError, build_graph, load_graph
from pantrypath.solver import solve


# ----------------------------- spec validation -----------------------------
def test_none_spec_rejected():
    with pytest.raises(InvalidSpecError, match="empty or not a mapping"):
        build_graph(None)


def test_empty_dict_spec_is_valid_empty_graph():
    sg = build_graph({})            # no ingredients, no rules — valid, just empty
    assert sg.ingredients() == [] and sg.rules() == []


def test_missing_target_rejected():
    with pytest.raises(InvalidSpecError, match="missing or empty 'target'"):
        build_graph({"substitutions": [{"options": [{"components": ["a"], "cost": 0.1}]}]})


def test_options_must_be_nonempty_list():
    with pytest.raises(InvalidSpecError, match="'options' must be a non-empty list"):
        build_graph({"substitutions": [{"target": "x", "options": []}]})


def test_components_must_be_nonempty_list():
    with pytest.raises(InvalidSpecError, match="'components' must be a non-empty list"):
        build_graph({"substitutions": [{"target": "x", "options": [{"components": [], "cost": 0.1}]}]})


def test_non_numeric_cost_rejected():
    with pytest.raises(InvalidSpecError, match="'cost' must be a number"):
        build_graph({"substitutions": [{"target": "x", "options": [{"components": ["a"], "cost": "cheap"}]}]})


def test_missing_cost_rejected():
    with pytest.raises(InvalidSpecError, match="'cost' must be a number"):
        build_graph({"substitutions": [{"target": "x", "options": [{"components": ["a"]}]}]})


def test_negative_cost_rejected():
    with pytest.raises(InvalidSpecError, match=r"must be >= 0"):
        build_graph({"substitutions": [{"target": "x", "options": [{"components": ["a"], "cost": -1}]}]})


def test_load_graph_missing_file(tmp_path):
    with pytest.raises(InvalidSpecError, match="not found"):
        load_graph(tmp_path / "nope.yaml")


def test_load_graph_empty_file(tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text("", encoding="utf-8")
    with pytest.raises(InvalidSpecError, match="empty"):
        load_graph(p)


# ----------------------------- dedupe (latent bug) -----------------------------
def test_duplicate_components_deduped_and_solvable():
    """A rule that lists the same component twice used to never fire (the AND
    counter expected one settle per *distinct* component). It must dedupe and solve."""
    spec = {"substitutions": [{"target": "x", "options": [{"components": ["a", "a", "b"], "cost": 0.1}]}]}
    sg = build_graph(spec)
    assert any(sg.G.nodes[r]["components"] == ["a", "b"] for r in sg.rules())
    res = solve(sg, "x", ["a", "b"])
    assert res.found and res.total_cost == pytest.approx(0.1)


# ----------------------------- CLI: --version & bilingual -----------------------------
def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "pantrypath" in out and pantrypath.__version__ in out


def test_output_is_bilingual(capsys):
    main(["--need", "buttermilk", "--have", "milk,white_vinegar"])
    out = capsys.readouterr().out
    # both the Chinese label and its English counterpart appear (README promises bilingual)
    assert "目标食材" in out and "target" in out
    assert "已有" in out and "have" in out
