"""Evaluate PantryPath against ground-truth substitutions (PLAN §B.8).

Given a set of hand-checked cases (target + pantry + accepted component sets),
run the solver's top-k alternatives and measure how well its ranking matches
what a cook would accept:

* **Precision@k** — fraction of cases whose accepted substitute appears within
  the engine's top-k alternatives.
* **MRR** (mean reciprocal rank) — average of ``1/rank`` of the first accepted
  alternative (0 if none in top-k). Rewards putting the right answer first.
* **Coverage** — fraction of cases the engine solves at all (any alternative).

The point is an honest, reproducible number — not a leaderboard claim.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import List, Optional, Sequence

import yaml

from .graph import SubstitutionGraph, load_default_graph
from .solver import solve_topk

DEFAULT_TRUTH_RESOURCE = "eval_truth.yaml"


@dataclass
class CaseResult:
    target: str
    solved: bool
    hit_rank: Optional[int]    # 1-based rank of first accepted alt, or None
    returned: List[List[str]]  # leaf-sets the engine returned, in order


@dataclass
class EvalReport:
    k: int
    n: int
    precision_at_k: float
    mrr: float
    coverage: float
    cases: List[CaseResult]


def load_truth(path: Optional[str | Path] = None) -> List[dict]:
    """Load ground-truth cases (packaged default, or an explicit YAML path)."""
    if path is None:
        res = resources.files("pantrypath") / "data" / DEFAULT_TRUTH_RESOURCE
        spec = yaml.safe_load(res.read_text(encoding="utf-8"))
    else:
        spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return spec.get("cases", []) or []


def evaluate(sg: SubstitutionGraph, cases: Sequence[dict], k: int = 3) -> EvalReport:
    """Run top-k for every case and score Precision@k, MRR, coverage."""
    results: List[CaseResult] = []
    hits = 0
    rr_sum = 0.0
    solved_count = 0

    for case in cases:
        target = case["target"]
        pantry = case.get("pantry", [])
        accept = [frozenset(a) for a in case.get("accept", [])]

        alts = solve_topk(sg, target, pantry, k=k)
        returned = [sorted(a.leaves()) for a in alts]
        solved = len(alts) > 0
        if solved:
            solved_count += 1

        hit_rank: Optional[int] = None
        for rank, alt in enumerate(alts, start=1):
            if frozenset(alt.leaves()) in accept:
                hit_rank = rank
                break

        if hit_rank is not None:
            hits += 1
            rr_sum += 1.0 / hit_rank

        results.append(CaseResult(target=target, solved=solved,
                                  hit_rank=hit_rank, returned=returned))

    n = len(cases)
    return EvalReport(
        k=k,
        n=n,
        precision_at_k=(hits / n) if n else 0.0,
        mrr=(rr_sum / n) if n else 0.0,
        coverage=(solved_count / n) if n else 0.0,
        cases=results,
    )


def format_report(rep: EvalReport) -> str:
    lines = [
        "PantryPath 评估报告 (ground-truth)",
        f"  用例数 n = {rep.n}   k = {rep.k}",
        f"  Precision@{rep.k} = {rep.precision_at_k:.3f}",
        f"  MRR          = {rep.mrr:.3f}",
        f"  Coverage     = {rep.coverage:.3f}",
        "",
        "逐用例:",
    ]
    for c in rep.cases:
        rank = "—" if c.hit_rank is None else f"#{c.hit_rank}"
        mark = "✅" if c.hit_rank else ("⚠ 解出但不在 accept" if c.solved else "❌ 无解")
        lines.append(f"  {mark}  {c.target:<22} 命中rank={rank}")
    return "\n".join(lines)


def main(argv=None) -> int:
    import argparse

    for stream in (sys.stdout, sys.stderr):
        rc = getattr(stream, "reconfigure", None)
        if rc:
            try:
                rc(encoding="utf-8")
            except Exception:
                pass

    ap = argparse.ArgumentParser(
        prog="pantrypath-eval",
        description="用 ground-truth 评估替代质量 (Precision@k / MRR / Coverage)")
    ap.add_argument("-k", type=int, default=3, help="top-k (默认 3)")
    ap.add_argument("--truth", default=None, help="ground-truth YAML 路径（默认用打包内置）")
    args = ap.parse_args(argv)

    sg = load_default_graph()
    cases = load_truth(args.truth)
    rep = evaluate(sg, cases, k=args.k)
    print(format_report(rep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
