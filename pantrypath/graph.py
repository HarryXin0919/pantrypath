"""Build the substitution (hyper)graph.

A substitution can need MORE THAN ONE ingredient at once
(buttermilk = milk + vinegar). A plain weighted digraph cannot express
"you need BOTH milk AND vinegar", so we use the classic AND/OR-graph trick:
encode every substitution OPTION as an intermediate "rule node".

    component_1 ─┐
    component_2 ─┼──▶ (rule node, weight=cost) ──▶ target
    component_3 ─┘        (AND inputs)

* ingredient node -> rule node : the rule consumes that ingredient (AND).
* rule node       -> target    : firing the rule produces the target.

We store this as a normal ``networkx.DiGraph`` so we get all of NetworkX's
tooling for free, but the AND-semantics live in the solver, not in
``nx.dijkstra`` (whose built-in version only understands OR/min at a node).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Dict, List

import networkx as nx
import yaml


@dataclass
class SubstitutionGraph:
    """Wrapper around a NetworkX DiGraph plus ingredient metadata."""

    G: nx.DiGraph
    tags: Dict[str, set] = field(default_factory=dict)  # ingredient -> {dietary tags}

    # -- convenience accessors ------------------------------------------------
    def ingredients(self) -> List[str]:
        return [n for n, d in self.G.nodes(data=True) if d.get("kind") == "ingredient"]

    def rules(self) -> List[str]:
        return [n for n, d in self.G.nodes(data=True) if d.get("kind") == "rule"]

    def has(self, ingredient: str) -> bool:
        return self.G.has_node(ingredient) and self.G.nodes[ingredient].get("kind") == "ingredient"

    def tags_of(self, ingredient: str) -> set:
        return self.tags.get(ingredient, set())


def _ensure_ingredient(G: nx.DiGraph, name: str) -> None:
    if not G.has_node(name):
        G.add_node(name, kind="ingredient")


class InvalidSpecError(ValueError):
    """Raised when a substitutions spec (YAML/dict) is malformed.

    The message always points at the offending entry so contributors editing
    ``substitutions.yaml`` get an actionable error instead of a raw KeyError.
    """


def _check(cond: bool, msg: str) -> None:
    if not cond:
        raise InvalidSpecError(msg)


def build_graph(spec: dict) -> SubstitutionGraph:
    """Build a SubstitutionGraph from a parsed YAML/dict spec.

    Validates the spec and raises :class:`InvalidSpecError` with a precise,
    contributor-friendly message on any malformed entry (the data is meant to
    be hand-edited, so a clear error beats a cryptic ``KeyError``).
    """
    _check(isinstance(spec, dict),
           "substitution spec is empty or not a mapping "
           "(expected top-level 'ingredients' and/or 'substitutions')")
    G = nx.DiGraph()
    tags: Dict[str, set] = {}

    # 1) ingredient nodes + dietary tags
    ingredients = spec.get("ingredients") or {}
    _check(isinstance(ingredients, dict), "'ingredients' must be a mapping of name -> metadata")
    for name, meta in ingredients.items():
        _ensure_ingredient(G, name)
        meta = meta or {}
        _check(isinstance(meta, dict), f"ingredient {name!r}: metadata must be a mapping")
        tags[name] = set(meta.get("tags", []) or [])
        G.nodes[name].update(category=meta.get("category"))

    # 2) substitution rules -> rule nodes
    subs = spec.get("substitutions") or []
    _check(isinstance(subs, list), "'substitutions' must be a list")
    rule_id = 0
    for i, entry in enumerate(subs):
        _check(isinstance(entry, dict),
               f"substitutions[{i}]: each entry must be a mapping with 'target' and 'options'")
        target = entry.get("target")
        _check(isinstance(target, str) and target.strip(),
               f"substitutions[{i}]: missing or empty 'target'")
        where = f"substitution for {target!r}"
        options = entry.get("options")
        _check(isinstance(options, list) and options, f"{where}: 'options' must be a non-empty list")
        _ensure_ingredient(G, target)
        for j, opt in enumerate(options):
            _check(isinstance(opt, dict), f"{where} option[{j}]: must be a mapping")
            raw_comps = opt.get("components")
            _check(isinstance(raw_comps, list) and raw_comps,
                   f"{where} option[{j}]: 'components' must be a non-empty list")
            _check(all(isinstance(c, str) and c.strip() for c in raw_comps),
                   f"{where} option[{j}]: every component must be a non-empty string")
            # Dedupe (preserve order): a rule listing the same component twice
            # would otherwise never fire — the AND-counter expects exactly one
            # settle per distinct component (one collapsed edge in the DiGraph).
            components = list(dict.fromkeys(raw_comps))
            try:
                cost = float(opt["cost"])
            except (KeyError, TypeError, ValueError):
                raise InvalidSpecError(f"{where} option[{j}]: 'cost' must be a number") from None
            _check(cost >= 0,
                   f"{where} option[{j}]: 'cost' must be >= 0 "
                   "(the solver is Dijkstra, which needs non-negative weights)")
            note = opt.get("note", "") or ""
            rnode = f"__rule_{rule_id}__"
            rule_id += 1
            G.add_node(
                rnode,
                kind="rule",
                cost=cost,
                note=note,
                target=target,
                components=components,
            )
            for c in components:
                _ensure_ingredient(G, c)
                G.add_edge(c, rnode)          # component feeds the rule (AND input)
            G.add_edge(rnode, target)         # rule produces the target

    # any ingredient referenced but missing tags defaults to empty set
    for n in list(G.nodes):
        if G.nodes[n].get("kind") == "ingredient":
            tags.setdefault(n, set())

    return SubstitutionGraph(G=G, tags=tags)


def load_graph(path: str | Path) -> SubstitutionGraph:
    """Load a substitution graph from a YAML file (clear errors on bad input)."""
    path = Path(path)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            spec = yaml.safe_load(fh)
    except FileNotFoundError:
        raise InvalidSpecError(f"substitutions file not found: {path}") from None
    except yaml.YAMLError as e:
        raise InvalidSpecError(f"{path}: not valid YAML — {e}") from None
    if spec is None:
        raise InvalidSpecError(f"{path}: file is empty")
    return build_graph(spec)


# The default knowledge base ships INSIDE the package (pantrypath/data/), so it
# resolves correctly whether running from the source tree or an installed wheel
# (the old sibling-dir relative path only worked in-tree).
DEFAULT_DATA_RESOURCE = "substitutions.yaml"


def default_data_path() -> Path:
    """Filesystem path to the packaged default substitutions.yaml."""
    return Path(str(resources.files("pantrypath") / "data" / DEFAULT_DATA_RESOURCE))


def load_default_graph() -> SubstitutionGraph:
    """Load the substitution graph from the packaged default data."""
    res = resources.files("pantrypath") / "data" / DEFAULT_DATA_RESOURCE
    spec = yaml.safe_load(res.read_text(encoding="utf-8"))
    return build_graph(spec)
