"""The solver: cheapest substitution chain from a pantry to a missing ingredient.

This is a generalized Dijkstra (a.k.a. the shortest B-hyperpath with an
additive weighting function, Knuth 1977 / Gallo et al. 1993):

* ``cost[x]`` = cheapest total "restoration cost" to obtain ingredient ``x``
  starting from what you already have.
* Pantry ingredients cost 0 (they are the sources).
* A rule node fires only once ALL of its component ingredients are settled;
  its cost is ``rule.cost + sum(cost[c] for c in components)``.  Because all
  weights are >= 0 and Dijkstra settles nodes in non-decreasing order, the
  first time a rule's components are all settled gives its minimum cost.
* We stop when the target is settled and rebuild the substitution TREE
  (a path for 1->1 chains, a tree when a step needs several ingredients).
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set

from .graph import SubstitutionGraph


@dataclass
class Step:
    """One substitution in the final plan."""

    target: str                 # what we needed
    components: List[str]       # what we use instead (AND)
    cost: float                 # this step's own restoration cost
    note: str = ""


@dataclass
class SubstitutionResult:
    target: str
    found: bool
    total_cost: float = math.inf
    steps: List[Step] = field(default_factory=list)   # leaf-first order
    tree: Optional[dict] = None                        # nested {ingredient, have, via, children}

    @property
    def quality_retained(self) -> float:
        """A friendly 0-100% score (1 - total loss, floored at 0)."""
        return max(0.0, 1.0 - self.total_cost) * 100.0

    def leaves(self) -> List[str]:
        """The pantry ingredients actually consumed by the plan."""
        out: List[str] = []

        def walk(node):
            if node is None:
                return
            if node.get("have"):
                out.append(node["ingredient"])
            for ch in node.get("children", []):
                walk(ch)

        walk(self.tree)
        return out


def _tag_filter_ok(sg: SubstitutionGraph, components: Sequence[str], require: Set[str]) -> bool:
    """A rule is allowed only if every component still carries the required tags."""
    if not require:
        return True
    return all(require.issubset(sg.tags_of(c)) for c in components)


def _run_dijkstra(
    sg: SubstitutionGraph,
    pantry_set: Set[str],
    require: Set[str],
    stop_at: Optional[str] = None,
):
    """Generalized Dijkstra / shortest B-hyperpath over the AND/OR graph.

    Runs to completion (or until ``stop_at`` is settled) and returns
    ``(cost, chosen_rule)``: the cheapest cost to obtain every reachable
    ingredient and, for each, the rule node used to obtain it (None for pantry
    sources). This is the project's core algorithm — a rule fires only once ALL
    its components are settled, with cost ``rule.cost + Σ component costs``;
    we deliberately do NOT use ``nx.dijkstra`` (it only knows OR/min at a node).
    """
    G = sg.G
    INF = math.inf
    cost: Dict[str, float] = {n: INF for n in G.nodes if G.nodes[n].get("kind") == "ingredient"}
    chosen_rule: Dict[str, Optional[str]] = {}
    remaining: Dict[str, int] = {}
    accrued: Dict[str, float] = {}

    for r in sg.rules():
        remaining[r] = len(G.nodes[r]["components"])
        accrued[r] = 0.0

    pq: List[tuple] = []
    for p in pantry_set:
        if G.has_node(p) and _tag_filter_ok(sg, [p], require):
            cost[p] = 0.0
            chosen_rule[p] = None
            heapq.heappush(pq, (0.0, p))

    settled: Set[str] = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in settled or d > cost.get(u, INF):
            continue
        settled.add(u)
        if stop_at is not None and u == stop_at:
            break
        for r in G.successors(u):                    # u -> rule edges
            if G.nodes[r].get("kind") != "rule":
                continue
            if not _tag_filter_ok(sg, G.nodes[r]["components"], require):
                continue
            accrued[r] += cost[u]
            remaining[r] -= 1
            if remaining[r] == 0:                     # all components ready -> rule can fire
                t = G.nodes[r]["target"]
                cand = G.nodes[r]["cost"] + accrued[r]
                if cand < cost.get(t, INF):
                    cost[t] = cand
                    chosen_rule[t] = r
                    heapq.heappush(pq, (cand, t))

    return cost, chosen_rule


def _build_tree(
    sg: SubstitutionGraph,
    ingredient: str,
    chosen_rule: Dict[str, Optional[str]],
    pantry_set: Set[str],
    steps: List[Step],
    override_rule: Optional[str] = None,
) -> dict:
    """Reconstruct a substitution tree; ``override_rule`` forces the top step."""
    G = sg.G
    if override_rule is None and ingredient in pantry_set and chosen_rule.get(ingredient) is None:
        return {"ingredient": ingredient, "have": True, "via": None, "children": []}
    r = override_rule if override_rule is not None else chosen_rule.get(ingredient)
    if r is None:  # safety: shouldn't happen for a found target
        return {"ingredient": ingredient, "have": False, "via": None, "children": []}
    comps = G.nodes[r]["components"]
    children = [_build_tree(sg, c, chosen_rule, pantry_set, steps) for c in comps]
    node = {
        "ingredient": ingredient,
        "have": False,
        "via": {"cost": G.nodes[r]["cost"], "note": G.nodes[r]["note"], "components": comps},
        "children": children,
    }
    steps.append(Step(target=ingredient, components=list(comps),
                      cost=G.nodes[r]["cost"], note=G.nodes[r]["note"]))
    return node


def solve(
    sg: SubstitutionGraph,
    target: str,
    pantry: Sequence[str],
    require_tags: Optional[Sequence[str]] = None,
) -> SubstitutionResult:
    """Find the cheapest way to obtain ``target`` from ``pantry``.

    Args:
        sg: the substitution graph.
        target: the ingredient the recipe needs but you lack.
        pantry: ingredients you already have.
        require_tags: dietary tags the whole solution must preserve
            (e.g. {"vegan"}); rules using a component lacking the tag are skipped.
    """
    G = sg.G
    pantry_set = set(pantry)
    require = set(require_tags or [])

    if not G.has_node(target):
        return SubstitutionResult(target=target, found=False)

    # Already have it (and it satisfies the diet) -> trivial, cost 0.
    if target in pantry_set and _tag_filter_ok(sg, [target], require):
        tree = {"ingredient": target, "have": True, "via": None, "children": []}
        return SubstitutionResult(target=target, found=True, total_cost=0.0, steps=[], tree=tree)

    cost, chosen_rule = _run_dijkstra(sg, pantry_set, require, stop_at=target)

    if cost.get(target, math.inf) == math.inf:
        return SubstitutionResult(target=target, found=False)

    steps: List[Step] = []
    tree = _build_tree(sg, target, chosen_rule, pantry_set, steps)
    return SubstitutionResult(
        target=target,
        found=True,
        total_cost=cost[target],
        steps=steps,            # leaf-first: deepest sub-substitution first
        tree=tree,
    )


def solve_topk(
    sg: SubstitutionGraph,
    target: str,
    pantry: Sequence[str],
    k: int = 3,
    require_tags: Optional[Sequence[str]] = None,
) -> List[SubstitutionResult]:
    """Return up to ``k`` distinct alternatives for ``target``, cheapest first.

    Strategy (the simpler, honest Top-k from PLAN.md §B.6): keep the **k best
    RULES that produce the target**, where each rule's components are filled by
    their globally cheapest sub-solutions. This gives side-by-side "plan A / B /
    C" comparisons (e.g. buttermilk via milk+vinegar 0.15, via yogurt+water
    0.20). It is NOT a full k-shortest-hyperpath enumeration (which would also
    vary the sub-solutions); that remains future work, and we keep the claim
    accordingly modest.
    """
    G = sg.G
    pantry_set = set(pantry)
    require = set(require_tags or [])

    if not G.has_node(target) or k <= 0:
        return []

    # Trivial: already have it.
    if target in pantry_set and _tag_filter_ok(sg, [target], require):
        tree = {"ingredient": target, "have": True, "via": None, "children": []}
        return [SubstitutionResult(target=target, found=True, total_cost=0.0, steps=[], tree=tree)]

    cost, chosen_rule = _run_dijkstra(sg, pantry_set, require)

    # Candidate rules = every rule producing `target` whose components are all
    # obtainable (finite cost) and which respects the dietary tags.
    candidates: List[tuple] = []  # (total_cost, rule_node)
    for r in sg.rules():
        if G.nodes[r]["target"] != target:
            continue
        comps = G.nodes[r]["components"]
        if not _tag_filter_ok(sg, comps, require):
            continue
        if any(cost.get(c, math.inf) == math.inf for c in comps):
            continue
        total = G.nodes[r]["cost"] + sum(cost[c] for c in comps)
        candidates.append((total, r))

    candidates.sort(key=lambda x: x[0])

    results: List[SubstitutionResult] = []
    seen_leafsets: Set[frozenset] = set()
    for total, r in candidates:
        steps: List[Step] = []
        tree = _build_tree(sg, target, chosen_rule, pantry_set, steps, override_rule=r)
        res = SubstitutionResult(target=target, found=True, total_cost=total, steps=steps, tree=tree)
        key = frozenset(res.leaves())
        if key in seen_leafsets:      # dedupe alternatives that use the same ingredients
            continue
        seen_leafsets.add(key)
        results.append(res)
        if len(results) >= k:
            break
    return results
