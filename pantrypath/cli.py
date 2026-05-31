"""Command-line interface for PantryPath.

Examples
--------
    python -m pantrypath.cli --need buttermilk --have milk,white_vinegar,flour
    python -m pantrypath.cli --need buttermilk --have powdered_milk,water,white_vinegar
    python -m pantrypath.cli --need egg --have flaxseed,water --require vegan
    python -m pantrypath.cli --need cake_flour,buttermilk --have all_purpose_flour,cornstarch,milk,lemon_juice

    # paste a whole ingredient list, get a substitute chain for each missing item:
    python -m pantrypath.cli recipe --have milk,white_vinegar,sugar --recipe-file cake.txt
    type cake.txt | python -m pantrypath.cli recipe --have milk,white_vinegar
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .graph import default_data_path, load_graph
from .recipe import RecipeReport, analyze_recipe
from .solver import SubstitutionResult, solve, solve_topk

# Packaged default data (works installed or from source). Override with --data.
DEFAULT_DATA = default_data_path()


def _render_tree(node: dict, prefix: str = "", is_last: bool = True) -> list[str]:
    """ASCII tree of the substitution plan."""
    connector = "└─ " if is_last else "├─ "
    label = node["ingredient"]
    if node.get("have"):
        line = f"{prefix}{connector}{label}  ✅ 已有"
    elif node.get("via"):
        via = node["via"]
        line = f"{prefix}{connector}{label}  ⇐ 用 {' + '.join(via['components'])}  (成本 {via['cost']:.2f})"
        if via.get("note"):
            line += f"\n{prefix}{'   ' if is_last else '│  '}      · {via['note']}"
    else:
        line = f"{prefix}{connector}{label}  ❌ 无方案"
    lines = [line]
    children = node.get("children", [])
    child_prefix = prefix + ("   " if is_last else "│  ")
    for i, ch in enumerate(children):
        lines += _render_tree(ch, child_prefix, i == len(children) - 1)
    return lines


def format_result(res: SubstitutionResult) -> str:
    if not res.found:
        return f"❌ 找不到「{res.target}」的替代方案（用现有食材无法还原）。"
    if not res.steps:
        return f"✅ 你已经有「{res.target}」了，无需替代。"
    out = [
        f"🍳 目标食材：{res.target}",
        f"   总还原成本：{res.total_cost:.2f}   ≈ 口味保真度 {res.quality_retained:.0f}%",
        f"   实际使用：{', '.join(res.leaves())}",
        "",
        "替代方案：",
    ]
    out += _render_tree(res.tree)
    return "\n".join(out)


def format_topk(target: str, results: list[SubstitutionResult]) -> str:
    """Render several ranked alternatives for one target, side by side."""
    if not results:
        return f"❌ 找不到「{target}」的替代方案（用现有食材无法还原）。"
    if len(results) == 1 and not results[0].steps:
        return f"✅ 你已经有「{target}」了，无需替代。"
    out = [f"🍳 目标食材：{target} —— {len(results)} 个备选方案（按还原度排序）"]
    for i, res in enumerate(results, 1):
        tag = "最省" if i == 1 else f"备选{i}"
        out.append("")
        out.append(f"【{tag}】成本 {res.total_cost:.2f}  ≈ 保真度 {res.quality_retained:.0f}%"
                   f"  · 用 {', '.join(res.leaves())}")
        out += _render_tree(res.tree)
    return "\n".join(out)


def format_recipe_report(report: RecipeReport) -> str:
    """Human-readable summary of a whole-recipe analysis."""
    out: list[str] = []
    out.append("📋 菜谱解析结果")
    out.append(f"   识别到 {len([p for p in report.parsed if p.ingredient])} 种食材"
               f"（共 {len(report.parsed)} 行）")
    if report.have:
        out.append(f"   ✅ 已有：{', '.join(report.have)}")
    if report.unmatched:
        out.append(f"   ❓ 未识别（不在知识库里，已跳过）：{'; '.join(report.unmatched)}")
    n_missing = len(report.missing)
    n_solved = len(report.solvable)
    out.append(f"   🔍 缺料 {n_missing} 种，其中 {n_solved} 种可替代，{n_missing - n_solved} 种暂无方案")

    if not report.missing:
        out.append("\n🎉 你的食材已覆盖整张配料表，无需替代！")
        return "\n".join(out)

    out.append("\n" + "=" * 56)
    for ing, res in report.missing:
        out.append("")
        out.append(format_result(res))
    return "\n".join(out)


def _read_recipe_text(args) -> str:
    if args.recipe_file:
        return Path(args.recipe_file).read_text(encoding="utf-8")
    if args.recipe_text:
        return args.recipe_text
    # fall back to stdin (supports: type cake.txt | pantrypath recipe ...)
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def _run_recipe(args) -> int:
    sg = load_graph(args.data)
    pantry = [x.strip() for x in args.have.split(",") if x.strip()]
    require = [x.strip() for x in args.require.split(",") if x.strip()]
    text = _read_recipe_text(args)
    if not text.strip():
        print("⚠ 没有配料表输入。用 --recipe-file 指定文件、--recipe-text 直接传文本，或通过管道传入 stdin。")
        return 2
    report = analyze_recipe(sg, text, pantry, require_tags=require)
    print(format_recipe_report(report))
    return 0


def _run_single(args) -> int:
    sg = load_graph(args.data)
    pantry = [x.strip() for x in args.have.split(",") if x.strip()]
    needs = [x.strip() for x in args.need.split(",") if x.strip()]
    require = [x.strip() for x in args.require.split(",") if x.strip()]
    topk = getattr(args, "top_k", 1) or 1

    blocks = []
    for need in needs:
        if topk > 1:
            alts = solve_topk(sg, need, pantry, k=topk, require_tags=require)
            blocks.append(format_topk(need, alts))
        else:
            blocks.append(format_result(solve(sg, need, pantry, require_tags=require)))
    print("\n\n".join(blocks))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="pantrypath",
        description="把缺料救场建模成最短路径：给定你有的食材，找还原度最高的替代链。",
    )
    # Top-level --need/--have keeps the original single-/multi-ingredient mode
    # working unchanged (backward compatible).
    ap.add_argument("--need", help="缺少的食材，逗号分隔（如 buttermilk 或 cake_flour,buttermilk）")
    ap.add_argument("--have", default="", help="你现有的食材，逗号分隔")
    ap.add_argument("--require", default="", help="必须保留的饮食标签，逗号分隔（如 vegan,gluten_free）")
    ap.add_argument("--top-k", type=int, default=1, metavar="N",
                    help="除最省方案外，再给出次优共 N 个并排比较（默认 1=只给最省）")
    ap.add_argument("--data", default=str(DEFAULT_DATA), help="替代规则 YAML 路径")

    sub = ap.add_subparsers(dest="command")
    rp = sub.add_parser("recipe", help="粘贴整段配料表，逐个缺料给出最省替代链")
    rp.add_argument("--have", default="", help="你现有的食材，逗号分隔")
    rp.add_argument("--require", default="", help="必须保留的饮食标签，逗号分隔")
    rp.add_argument("--data", default=str(DEFAULT_DATA), help="替代规则 YAML 路径")
    g = rp.add_mutually_exclusive_group()
    g.add_argument("--recipe-file", help="配料表文本文件路径（每行一种食材）")
    g.add_argument("--recipe-text", help="直接传入配料表文本")
    rp.set_defaults(func=_run_recipe)
    return ap


def main(argv=None) -> int:
    # The output uses emoji + CJK; on a Windows GBK console the default stdout
    # codec raises UnicodeEncodeError. Switch to UTF-8 when possible (no-op on
    # platforms that are already UTF-8). Does not affect captured test output.
    for stream in (sys.stdout, sys.stderr):
        reconfig = getattr(stream, "reconfigure", None)
        if reconfig:
            try:
                reconfig(encoding="utf-8")
            except Exception:
                pass

    ap = build_parser()
    args = ap.parse_args(argv)

    if args.command == "recipe":
        return _run_recipe(args)
    if not args.need:
        ap.error("请用 --need 指定缺料，或使用子命令 `recipe` 解析整段配料表。")
    return _run_single(args)


if __name__ == "__main__":
    raise SystemExit(main())
