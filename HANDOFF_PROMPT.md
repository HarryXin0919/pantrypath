# Claude Code 起始提示词（复制下面整段粘给 Claude Code）

> 用法：在解压后的 `pantrypath/` 目录里启动 Claude Code，然后把下面"提示词正文"
> 整段粘贴进去即可。它会先让 Claude Code 读上下文、跑通测试，再开始干活。

---

## 提示词正文（复制这一段）

```
你正在接手一个名为 PantryPath 的现有 Python 项目。请严格按下面步骤来。

【第一步：建立上下文，先别写代码】
1. 读 CLAUDE.md（项目上下文 + 设计护栏，最重要）。
2. 读 PLAN.md（完整规划与竞品调研，权威文档）。
3. 读 pantrypath/graph.py、pantrypath/solver.py、tests/test_solver.py，
   确认你理解"为什么用有向超图 + 自写的广义 Dijkstra，而不是普通图 + nx.dijkstra"。
4. 建虚拟环境并安装：python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
5. 跑 pytest -q，确认 9 passed。把测试结果回报给我。

完成第一步后停下，用 3~5 句话向我复述：这个项目的核心模型是什么、
哪些地方是"有意为之、不要重构掉"的（见 CLAUDE.md 的设计护栏）。等我确认后再继续。

【第二步：按路线图推进（等我确认后再做）】
默认先做这一项（除非我另行指定）：
  ➤ 菜谱整段解析：新增能力——粘贴一段配料表文本，解析出食材列表，
    对每个"我没有的食材"各跑一次 solver，汇总输出每个缺料的最省替代链。
    放在 pantrypath/recipe.py，并加 CLI 子命令或参数；补充对应测试。

【硬性约束（违反就是改坏了）】
- 不要把超图退化成普通加权图，不要用 nx.dijkstra 替换 solver.py 里的广义 Dijkstra
  （原因见 CLAUDE.md）。复合替代"酪乳=牛奶 AND 醋"必须继续工作。
- 替代知识只放 data/substitutions.yaml，不要硬编码进 .py。
- 任何行为改动遵循：先写/改测试 → 实现 → 确保 pytest 全绿 → 再继续。
- README 里关于新颖性的表述要诚实（不是"首个图方法"，详见 PLAN.md §A）。

【完成定义】
- 新功能有测试覆盖，pytest 全绿。
- README/CLAUDE.md 同步更新（用法、状态）。
- 给我一句话变更摘要 + 如何手动验证的命令。
```

---

## 备选任务（想让 Claude Code 做别的，把"第二步"替换成下面任一段）

- **Top-k 备选方案**：除最省方案外，额外给出 2~3 个次优替代链并排比较
  （k-最短超路径，或每个 target 保留前 k 优规则）；更新 CLI 与测试。
- **Streamlit Web UI**：新增 `app.py`，粘贴菜谱 + 勾选已有食材 + 可视化渲染替代树。
- **数据扩充**：把 `data/substitutions.yaml` 扩到 100+ 条高质量替代（手工种子，标注 cost 与饮食标签），并补关键路径测试。
- **评估脚本**：新增 `eval/`，用 ground-truth 替代对计算 Precision@k / MRR，对比 Spoonacular 1 跳基线。
- **打包修复**：把 `cli.py` 的 `DEFAULT_DATA` 改用 `importlib.resources` 读取包内数据，使 `pip install` 后的 wheel 也能正常找到数据文件。

## 给 Harry 的两点提醒

- Claude Code 默认会读取仓库根目录的 `CLAUDE.md`，所以即使你忘了粘提示词，它也能拿到上下文——但粘上面那段能让它按正确顺序"先理解再动手"。
- 如果用 git：先 `git init && git add -A && git commit -m "init: PantryPath prototype"`，再交给 Claude Code，方便你 review 它的每次改动（diff）。
