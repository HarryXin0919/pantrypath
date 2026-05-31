# CLAUDE.md — PantryPath 项目上下文（给 Claude Code 读）

> 本文件供 Claude Code 在每次会话开始时自动读取。先读完本文件，再读
> `PLAN.md`（完整规划 + 竞品调研）与 `README.md`（对外卖点）。

## 一句话定位

PantryPath 把"缺料救场"建模成**有向超图上的最短超路径**问题：给定你现有的食材，
返回还原度最高（走味最少）的替代链。例：没有酪乳 → 牛奶 + 醋。
**经典算法（Dijkstra），不用 ML，不调外部 API，可离线、可解释。**

## ⚠️ 设计护栏（改代码前必读，别"顺手优化"掉核心）

1. **不要把超图退化成普通加权图。** 招牌例子"酪乳 = 牛奶 **AND** 醋"是 1→多。
   普通图一条边只能指向一个后继，表达不了"同时需要两样"。我们用 **AND/OR 图**：
   每个替代选项 = 一个**规则节点（`__rule_N__`, kind="rule"）**，它的若干原料食材（AND）
   连进规则，规则再连到目标食材。`graph.py` 里的规则节点**不是脏数据，是模型本身**。
2. **不要直接用 `nx.dijkstra` 求解。** NetworkX 内置 Dijkstra 只懂"节点处取 min"的 OR 语义，
   不懂"规则节点处对所有原料求和"的 AND 语义。`solver.py` 里的广义 Dijkstra
   （按 `remaining[r]` 计数、集齐才触发）是**有意为之**，请勿替换为库函数。
3. **成本 = 还原度损失，沿链求和**（0≈原味，越大越走味）；复合步成本 =
   `规则自身 cost + Σ 各原料 cost`。若要改成"取最大"等其它语义，必须同步更新 `PLAN.md` 与测试。
4. **数据与代码解耦**：替代知识只放 `pantrypath/data/substitutions.yaml`，不要硬编码进 `.py`。
5. **诚实的新颖性表述**：项目卖点是"用经典最短路径 / 超路径 + 复合替代 + 口袋感知 + 离线可解释"，
   **不是**"首个用图做替代"。学术界已有 GISMo / FlavorGraph / FoodKG（均用 ML 嵌入/GNN）。
   改 README 时别写成"第一个图方法"，会被证伪（详见 PLAN.md §A）。

## 仓库结构

```
pantrypath/
├── CLAUDE.md                # 本文件
├── HANDOFF_PROMPT.md        # 给 Claude Code 的起始提示词
├── PLAN.md                  # 完整规划 + 竞品调研（权威文档）
├── README.md                # 对外门面
├── pyproject.toml           # 可安装包 + 控制台脚本 + pytest 配置
├── requirements.txt
├── pantrypath/
│   ├── data/                # 打包进 wheel 的数据（importlib.resources 读取）
│   │   ├── substitutions.yaml  # 替代知识库（贡献者主要改这里）
│   │   └── eval_truth.yaml     # 评估用 ground-truth
│   ├── graph.py             # YAML → NetworkX 超图（规则节点编码）；load_default_graph()
│   ├── solver.py            # 广义 Dijkstra / 最短超路径 + 回溯成树；solve() 与 solve_topk()
│   ├── recipe.py            # 菜谱整段解析 → 逐个缺料批量求解
│   ├── eval.py              # 评估 Precision@k / MRR / Coverage
│   └── cli.py               # 命令行界面（含 `recipe` 子命令、`--top-k`）
├── app.py                  # Streamlit Web UI（粘贴菜谱 + 勾选已有 + 渲染替代树）
└── tests/                   # 40 个单测，全过
    ├── test_solver.py       #   solver / graph
    ├── test_recipe.py       #   菜谱解析 + 批量求解
    ├── test_topk.py         #   Top-k 备选方案
    ├── test_eval.py         #   评估 Precision@k / MRR / Coverage
    ├── test_app.py          #   Streamlit Web UI 无头冒烟（streamlit 缺失则跳过）
    ├── test_data_counts.py  #   数据计数防漂移（docs 与 YAML 一致）
    └── test_cli.py          #   CLI（向后兼容 + recipe + --top-k）
```

## 环境 / 运行 / 测试

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"        # 或 pip install -r requirements.txt

# 跑测试（先确认绿）
pytest -q                      # 期望 40 passed

# 跑 CLI
python -m pantrypath.cli --need buttermilk --have milk,white_vinegar
pantrypath --need egg --have flaxseed,water --require vegan   # 安装后可用控制台脚本

# 菜谱整段解析（粘贴配料表，逐个缺料给替代链）
python -m pantrypath.cli recipe --have milk,white_vinegar --recipe-file cake.txt
```

## 当前状态

- ✅ Phase 1（多源 Dijkstra、1→1、多跳链）
- ✅ Phase 2（AND/OR 超图、复合替代、替代树输出）—— 核心亮点已实现
- ✅ Phase 3 部分（`require_tags` 饮食标签过滤）
- ✅ Phase 3：**菜谱整段解析**（`recipe.py` + `cli recipe` 子命令；逐个缺料批量求解）
- ✅ Phase 3：**Top-k 备选方案**（`solve_topk()` + `--top-k`；前 k 优规则并排比较）
- ✅ Phase 3：**数据扩充到 100+ 条**（当前 310 食材 / 225 目标 / 448 规则，两轮多代理起草+对抗式核验；覆盖烘焙/乳制品 + 坚果种子/生鲜香料/亚洲全球调料/蛋白豆类/调味品/饮品，含 AND 复合调料粉）
- ✅ **文献核查**：对高风险(复合 AND + 化学转化)规则用真实烹饪文献(King Arthur / Serious Eats / ATK / Harold McGee / BBC Good Food)核验 — 50 valid / 33 补全外部条件 / 13 改正 / 2 删除；外部条件已写进 note(如小苏打需配酸、淀粉需冷水调浆、明胶↔琼脂非 1:1、可可→巧克力需加脂、亚麻籽蛋仅作粘合、鲜:干香草约 3:1)
- ✅ Phase 3：**Streamlit Web UI**（`app.py`；`pip install -e ".[web]"` 后 `streamlit run app.py`）
- ✅ Phase 3：**评估脚本**（`eval.py` + `pantrypath-eval`；**在项目自带 ground-truth 上自评** Precision@3=1.00 / MRR=1.00 / Coverage=1.00，非与外部基线对比）
- ✅ 打包修复：数据已移入包内 `pantrypath/data/`，用 `importlib.resources` 读取，安装为 wheel 后仍可用（控制台脚本任意目录可跑）
- ✅ Phase 3 全部完成

## 下一步路线图（按优先级，详见 PLAN.md §B.6）

1. ~~**菜谱整段解析**：粘贴一段配料表 → 抽出食材 → 对每个缺料各跑一次 solver。~~ ✅ 已完成（`recipe.py` + `cli recipe`）
2. ~~**Top-k 备选方案**：除最省方案外，给出次优 2~3 个并排比较。~~ ✅ 已完成（`solve_topk()`，保留前 k 优规则；非完整 k-最短超路径，见函数 docstring）
3. ~~**Streamlit Web UI**：粘贴菜谱 + 勾选已有食材 + 渲染替代树（`app.py`）。~~ ✅ 已完成（`app.py`，`streamlit run app.py`；含 AppTest 无头测试）
4. ~~**数据扩充到 100+ 条**：手工种子 + 挖掘。~~ ✅ 已完成（310 食材 / 225 目标 / 448 规则；两轮多代理起草 + 对抗式核验 + 文献核查 + 人工去噪，后续可继续从 Food.com 评论 / Recipe1MSubs 扩充）。
5. ~~**评估脚本**：用 ground-truth 替代对算 Precision@k / MRR。~~ ✅ 已完成（`eval.py` + `pantrypath-eval`；当前 P@3=1.00 / MRR=1.00 / Coverage=1.00，对 Spoonacular 基线对比仍可后补）。
6. ~~**打包数据文件**：`importlib.resources` 读取包内数据。~~ ✅ 已完成（数据移入 `pantrypath/data/`，`graph.load_default_graph()` 用 `importlib.resources`；wheel 已验证含数据，控制台脚本任意目录可跑）。

## 约定

- 代码注释与文档可中英混排（沿用现有风格）。
- 任何行为改动都要：先改/加测试，再实现，保证 `pytest` 绿后再继续。
- 新增替代规则：在 `pantrypath/data/substitutions.yaml` 加 `target` + `options`，并为关键路径补一条测试。

## 已知小坑

- 在某些沙箱里 `pytest` 退出时清理临时目录会触发 `RecursionError`（是环境的 tmp 清理问题，**不是测试失败**）。
  可用 `pytest --basetemp=/tmp/pp -p no:cacheprovider` 规避；本机正常环境无此问题。
