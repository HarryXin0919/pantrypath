"""PantryPath — Streamlit Web UI.

Paste a recipe ingredient list, tick what you already have, and see the cheapest
substitution chain (as a tree) for every missing ingredient.

Run:
    pip install -e ".[web]"
    streamlit run app.py

This is a thin presentation layer over the same engine the CLI uses
(`pantrypath.recipe.analyze_recipe` + `pantrypath.solver`). No logic lives here.
"""

from __future__ import annotations

import streamlit as st

from pantrypath import load_default_graph
from pantrypath.graph import SubstitutionGraph
from pantrypath.recipe import analyze_recipe
from pantrypath.solver import SubstitutionResult, solve, solve_topk

TAG_CHOICES = ["vegan", "vegetarian", "gluten_free", "dairy_free"]


@st.cache_resource
def get_graph() -> SubstitutionGraph:
    return load_default_graph()


def render_tree(node: dict, depth: int = 0) -> None:
    pad = " " * depth   # em-space indent (Markdown collapses ASCII spaces)
    ing = node["ingredient"]
    if node.get("have"):
        st.markdown(f"{pad}• **{ing}** ✅ 已有")
    elif node.get("via"):
        via = node["via"]
        comps = " + ".join(via["components"])
        st.markdown(f"{pad}• **{ing}** ⇐ 用 {comps} · 成本 {via['cost']:.2f}")
        if via.get("note"):
            st.caption(f"{pad} {via['note']}")
    else:
        st.markdown(f"{pad}• **{ing}** ❌ 无方案")
    for ch in node.get("children", []):
        render_tree(ch, depth + 1)


def render_result(res: SubstitutionResult, sg: SubstitutionGraph, pantry, require, k: int) -> None:
    if not res.found:
        st.error(f"找不到「{res.target}」的替代方案（用现有食材无法还原）。")
        return
    st.success(f"总还原成本 {res.total_cost:.2f} ≈ 口味保真度 {res.quality_retained:.0f}%"
               f" · 实际使用：{', '.join(res.leaves())}")
    render_tree(res.tree)
    if k > 1:
        alts = solve_topk(sg, res.target, pantry, k=k, require_tags=require)
        if len(alts) > 1:
            with st.expander(f"查看 {len(alts)} 个备选方案"):
                for i, alt in enumerate(alts, 1):
                    tag = "最省" if i == 1 else f"备选 {i}"
                    st.markdown(f"**【{tag}】** 成本 {alt.total_cost:.2f} · 用 {', '.join(alt.leaves())}")


def main() -> None:
    st.set_page_config(page_title="PantryPath 寻味替代", page_icon="🥛", layout="centered")
    st.title("🥛 PantryPath")
    st.caption("缺一味料别弃菜 —— 把替代建成最短超路径，给你还原度最高的替代链。无 ML、无 API、离线可解释。")

    sg = get_graph()
    all_ingredients = sorted(sg.ingredients())

    with st.sidebar:
        st.header("我现有的食材")
        pantry = st.multiselect("从知识库里勾选你已有的食材", all_ingredients,
                                help="只列出知识库里认识的食材")
        require = st.multiselect("必须保留的饮食标签", TAG_CHOICES,
                                 help="例如选 vegan，会自动排除破坏该标签的替代")
        k = st.slider("每个缺料给几个备选方案", 1, 5, 1)

    tab_recipe, tab_single = st.tabs(["📋 整段菜谱", "🔍 单个食材"])

    with tab_recipe:
        st.write("粘贴一段配料表（每行一种食材），逐个缺料给出替代链：")
        text = st.text_area("配料表", height=180,
                            placeholder="2 cups all-purpose flour\n1 cup buttermilk\n1 large egg")
        if st.button("分析整段菜谱", type="primary"):
            if not text.strip():
                st.warning("请先粘贴配料表。")
            else:
                report = analyze_recipe(sg, text, pantry, require_tags=require)
                c1, c2, c3 = st.columns(3)
                c1.metric("已有", len(report.have))
                c2.metric("缺料", len(report.missing))
                c3.metric("可替代", len(report.solvable))
                if report.have:
                    st.info("✅ 已有：" + ", ".join(report.have))
                if report.unmatched:
                    st.warning("❓ 未识别（不在知识库，已跳过）：" + "; ".join(report.unmatched))
                for ing, res in report.missing:
                    st.subheader(f"🍳 {ing}")
                    render_result(res, sg, pantry, require, k)

    with tab_single:
        need = st.selectbox("我缺的食材", [""] + all_ingredients)
        if st.button("查找替代", type="primary") and need:
            res = solve(sg, need, pantry, require_tags=require)
            render_result(res, sg, pantry, require, k)

    st.divider()
    st.caption(f"知识库：{len(all_ingredients)} 种食材 · {len(sg.rules())} 条替代规则。"
               " 扩充只需改 pantrypath/data/substitutions.yaml。")


if __name__ == "__main__":
    main()
