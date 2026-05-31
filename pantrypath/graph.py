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


def build_graph(spec: dict) -> SubstitutionGraph:
    """Build a SubstitutionGraph from a parsed YAML/dict spec."""
    G = nx.DiGraph()
    tags: Dict[str, set] = {}

    # 1) ingredient nodes + dietary tags
    for name, meta in (spec.get("ingredients") or {}).items():
        _ensure_ingredient(G, name)
        meta = meta or {}
        tags[name] = set(meta.get("tags", []))
        G.nodes[name].update(category=meta.get("category"))

    # 2) substitution rules -> rule nodes
    rule_id = 0
    for entry in spec.get("substitutions") or []:
        target = entry["target"]
        _ensure_ingredient(G, target)
        for opt in entry["options"]:
            components = list(opt["components"])
            cost = float(opt["cost"])
            note = opt.get("note", "")
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
    """Load a substitution graph from a YAML file."""
    with open(path, "r", encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
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
