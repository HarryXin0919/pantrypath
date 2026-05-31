# PantryPath — 项目规划与竞品调研

> 当你缺少某种食材时，把"救场替代"建模成图上的**最短路径 / 最短超路径**问题，
> 返回还原度最高的替代链（例：没有酪乳 → 牛奶 + 醋）。

本文件包含两部分：**(A) 相似项目调研与新颖性诚实评估**，**(B) 详细实现规划**。
仓库里已附带一个可运行的 Python + NetworkX 原型（见最后一节）。

---

## A. 相似项目调研

### A.1 调研结论（先说重点）

把"食材替代"建成图，在**学术界并不是新鲜事**——已有多篇论文和开源仓库这么做。
你 pitch 里"GitHub 上没人把替代建模成可做路径搜索的加权图"这句话，需要修正成更站得住脚的版本：

- ❌ 过度宣称："第一个用图来做食材替代的项目"——不成立，下面列的 GISMo / FlavorGraph / FoodKG 都是图。
- ✅ 站得住脚的新颖点（见 A.3）：**用经典最短路径 / 最短超路径**（而非机器学习嵌入/GNN）来求解，
  并且**显式支持复合替代（AND，牛奶+醋）、口袋约束（pantry-aware）、可解释、零模型、零外部 API**。

### A.2 现有项目分类

**① 学术界：图 / 知识图谱做替代（与你最接近，但用的是 ML 嵌入而非路径搜索）**

| 项目 | 做法 | 与 PantryPath 的关系 |
|---|---|---|
| **GISMo**（Meta AI，*Learning to Substitute Ingredients in Recipes*, 2023；`facebookresearch/gismo`） | 在食材图上跑 **GNN**，结合菜谱上下文给单个食材排替代候选；发布了 Recipe1MSubs 数据集（7 万对替代） | 最直接的"graph-based substitution"先例。**但它输出 1→1 候选、用学习嵌入，不做多跳链、不做最短路径、不处理"牛奶+醋"这种 AND 复合** |
| **FlavorGraph**（Sony AI + 高丽大学，*Scientific Reports* 2020；`lamypark/FlavorGraph`） | 6,653 食材节点 + 化学分子节点，边权来自百万菜谱共现；用 metapath2vec 学嵌入做配对/替代 | 是"加权食材图"，但权重是共现频率、求解靠向量相似度，**不是路径搜索** |
| **Identifying Ingredient Substitutions Using a KG of Food**（RPI + IBM，Shirai 等，*Frontiers in AI* 2021；FoodKG / `solashirai`） | 知识图谱（FoodOn 分类 + USDA 营养）+ word2vec，提出 **DIISH** 启发式给"健康"替代排序 | 与你的"进阶：饮食标签替代"高度重合，**值得直接借鉴它的健康/饮食约束建模** |
| **Exploiting Food Embeddings for Ingredient Substitution**（Pellegrini 等，2021；`ChantalMP/...`） | Food2Vec / FoodBERT 嵌入 + 聚类判断可替代性 | 纯嵌入路线，无图路径 |
| **MISKG**（`kanak8278/MISKG`） | 多模态食材替代知识图谱，面向个性化饮食 | 数据集可参考 |
| **healthy-food-subs**（`MaastrichtU-IDS`） | 知识图谱嵌入做"更健康"替代推荐 | 数据/思路参考 |

**② 商业 API：直接给替代（1 跳、黑盒、要联网/付费）**

- **Spoonacular**：`food/ingredients/substitutes` 接口，按名字返回一串替代 + 文字说明。**只给一层、不给链、不可解释、按调用计费。**
- **Edamam** 等类似。

**③ GitHub 业余项目：绝大多数是"我有这些料能做什么菜"（≠ 替代）**

- `zaclark369/Pantry`、`louis-young/ingredient-recipe-finder`、`Eduardo-J-Morales/Ingredient-Based-Recipes-Finder`、SuperCook 等——**做的是菜谱检索/推荐**，和"缺一味料怎么救场"是不同问题。
- `samedelstein/ingredient_substitute_gpt`——用 LLM 直接问替代，无图、无最短路径、结果不稳定。

### A.3 PantryPath 真正的差异化（建议据此重写 README 卖点）

1. **经典算法而非 ML**：把问题归约为**加权图最短路径 / 有向超图最短超路径**，用 Dijkstra/BFS 求解。
   学术界几乎都在用嵌入/GNN/LLM，几乎没人把它当成一道干净的**图论教科书问题**来做——这正是本科项目最好的切入点（可讲清、可证明、可单测）。
2. **复合替代（AND）是核心而非附属**：酪乳 = 牛奶 **且** 醋。普通加权图表达不了"同时需要两样"，
   必须用 **AND/OR 图 / 有向超图**，求解变成**最短超路径**（Knuth 1977；Gallo et al. 1993）。这是真正有含金量、又少见于业余项目的部分。
3. **口袋感知（pantry-aware）多源搜索**：从"你已有的食材"集合出发做多源搜索，命中即停。
4. **完全可解释 + 离线 + 零依赖外部 API**：输出一棵"替代树"和每步的还原度成本，谁都能看懂；不联网、不调付费接口、不需要训练模型。
5. **多跳链路**：奶粉+水→牛奶→（+醋）→酪乳。逐跳累加成本天然反映"每替换一次，菜就走味一点"。

> 一句话定位（可放 GitHub 简介）：
> *"A tiny, explainable, offline engine that turns 'I'm out of X' into the cheapest substitution chain, by modeling cooking substitutions as a shortest-hyperpath problem — no ML, no API."*

---

## B. 实现规划

### B.1 核心形式化（项目的灵魂）

**为什么普通图不够。** 把"A 可替代为 B"画成边 `A→B`、跑 Dijkstra，只能处理 1→1。
但招牌例子"酪乳 = 牛奶 + 醋"是 1→**多**（AND）：你必须**同时**有牛奶和醋。普通图里一条边只能指向一个后继，表达不了"需要 B 且 C"。

**正确模型：AND/OR 图（有向超图）。** 把每个"替代选项"变成一个**规则节点**：

```
component_1 ─┐
component_2 ─┼──▶ (rule, weight = 还原度成本) ──▶ target
component_3 ─┘     （AND 输入：全部到位规则才能触发）
```

- 同一 target 下的多个规则之间是 **OR**（求解器自动选最省的）。
- 1→1 替代 = 单元素 AND（退化情形）。
- 这正是**有向超图**：一条超边的"尾"是一组食材，"头"是目标食材。

**求解 = 最短超路径（shortest B-hyperpath，可加权重）。** 这是 Dijkstra 的推广：

- `cost[x]` = 从"你已有的食材"出发、得到食材 x 的最小总还原度成本。
- 口袋（pantry）里的食材 `cost = 0`，是多个源点。
- 一个规则节点只有当它**所有**尾食材都已定值（settled）时才能触发，触发成本 = `规则自身成本 + Σ 各尾食材成本`。
- 因为所有权重 ≥ 0、Dijkstra 按成本非降顺序定值，所以一个规则第一次"集齐"时就是它的最小成本——正确性可证。

**成本模型。** 边权 = **还原度成本**（口味/口感损失），建议 0~1，越小越接近原味。
路径成本 = 沿途各步求和（多跳越多、走味越多，符合直觉）。`口味保真度 ≈ (1 − 总成本)`。
（设计取舍：复合步用"求和"还是"取最大"可讨论；原型用求和=标准可加性 B-超路径，简单且可解释。）

### B.2 数据模型（`data/substitutions.yaml`）

```yaml
ingredients:
  buttermilk: {tags: [vegetarian], category: dairy}
  milk:       {tags: [vegetarian], category: dairy}
  white_vinegar: {tags: [vegetarian, vegan, gluten_free, dairy_free], category: acid}
substitutions:
  - target: buttermilk
    options:
      - {components: [milk, white_vinegar], cost: 0.15, note: "1 杯牛奶 + 1 汤匙白醋，静置 10 分钟"}
      - {components: [plain_yogurt, water], cost: 0.20, note: "..."}
```

- `tags` 支撑"进阶：保持纯素/无麸质"——某规则若用到缺少所需标签的食材，则被过滤。
- 数据与代码解耦：贡献者只改 YAML 即可扩充知识库。

### B.3 算法（广义 Dijkstra / 最短超路径）

```
输入: 超图 G, 口袋 pantry, 目标 target, 需保留标签 require
cost[*] = +∞;  for p in pantry: cost[p] = 0, 入堆(0, p)
对每条规则 r: remaining[r] = |components(r)|, accrued[r] = 0
while 堆非空:
    (d, u) = 弹出最小;  若 u 已定值 continue;  标记 u 定值
    若 u == target: break
    for 每条以 u 为尾的规则 r:               # u → r
        若 r 违反 require: 跳过
        accrued[r] += cost[u];  remaining[r] -= 1
        if remaining[r] == 0:                # 集齐，规则可触发
            t = head(r);  cand = weight(r) + accrued[r]
            if cand < cost[t]: cost[t] = cand; 记录 t 的来源规则 = r; 入堆(cand, t)
回溯: 从 target 沿"来源规则→其尾食材"递归展开成一棵替代树，遇口袋食材为叶
```

- **复杂度**：O((V + ΣE) log V)，V=食材数，ΣE=所有规则的尾大小之和。对家用知识库规模（几千节点）瞬时返回。
- **多跳/复合/口袋约束**统一在一个算法里，无需特判。
- **进阶**：Top-k 备选方案 → k-最短超路径或对每个 target 收集前 k 优规则；菜谱整段输入 → 解析出配料表后对每个缺料各跑一次。

### B.4 技术栈

- **Python 3.10+**（你已选定）。
- **NetworkX** 存图：1→1 的 MVP 可直接用 `nx.multi_source_dijkstra`；复合（AND）部分用上面的自定义松弛
  （NetworkX 内置 Dijkstra 只懂节点处取 min 的 OR 语义，不懂规则节点处求和的 AND 语义——这点本身就是很好的"为什么要自己写"的讲解素材）。
- **PyYAML** 读数据。**pytest** 测试。
- **前端（Phase 3）**：**Streamlit** 最省事（粘贴菜谱 + 勾选已有食材 + 展示替代树）；想做简历项目可换 FastAPI + React。
- 可视化超图：`networkx` + `matplotlib`/`pyvis` 导出关系图，README 里放一张很加分。

### B.5 仓库结构

```
pantrypath/
├── README.md                # 项目门面 + 快速上手
├── PLAN.md                  # 本文件：规划 + 竞品调研
├── requirements.txt
├── data/
│   └── substitutions.yaml   # 替代知识库（贡献者主要改这里）
├── pantrypath/
│   ├── __init__.py
│   ├── graph.py             # YAML → NetworkX 超图（规则节点编码）
│   ├── solver.py            # 广义 Dijkstra / 最短超路径 + 回溯
│   └── cli.py               # 命令行界面
└── tests/
    └── test_solver.py       # 9 个单测（已全过）
```

### B.6 路线图（建议三阶段，难度递增、随时可交付）

**Phase 1 — MVP（约 1 周）**
- 普通加权图 + `multi_source_dijkstra`，仅 1→1 替代与多跳链。
- CLI：`--need` / `--have`，输出最省替代与成本。
- 20~30 条种子数据 + 单测。
- 交付点：已经能用、能讲清最短路径思想。

**Phase 2 — 复合替代（核心亮点，约 1~2 周）**
- 升级为 AND/OR 超图 + 最短超路径，跑通"酪乳=牛奶+醋"。
- 输出"替代树"而非单路径；多跳 + 复合混合。
- 交付点：项目真正的差异化与含金量所在。✅（原型已实现到这里）

**Phase 3 — 进阶（按兴趣选做）**
- 饮食标签约束（纯素/无麸质）：过滤或惩罚破坏标签的规则。✅（原型已含基础版）
- 菜谱整段粘贴 → 解析配料 → 批量找缺料替代。
- Top-k 备选 + 比较视图；Streamlit Web UI；超图可视化。
- 真实数据扩充（见 B.7）。

### B.7 数据来源策略（决定项目可信度）

1. **手工种子**：从权威烘焙/烹饪替代指南整理一批高置信规则（带用量与还原度评分）。
2. **众包挖掘**：从 Food.com / 菜谱评论里用模式 `"substitute A for B"` 抽取替代对（Shirai 等论文与 Recipe1MSubs 都这么做，可直接复用其数据集）。
3. **交叉校验**：用 Spoonacular 替代接口做对照/补全（仅离线构建知识库时用，运行期不依赖）。
4. 成本（还原度）初值可人工标注，后续可用共现/评价情感做弱监督微调。

### B.8 评估方法（让项目"可量化"，论文/简历都用得上）

- 收集一份 ground-truth 替代对（来自替代指南 + 用户评论）。
- 指标：**Precision@k / MRR**（你的最省方案是否命中真实可行替代）、覆盖率、平均链长。
- 基线对比：Spoonacular 1 跳结果 vs. PantryPath 多跳/复合；嵌入相似度（FlavorGraph 风格）vs. 最短路径。
- 消融：去掉复合（AND）后能解决的缺料比例下降多少 → 量化你核心亮点的价值。

### B.9 风险与难点

- **数据质量 > 算法**：替代是否"好"很主观，还原度成本要靠数据/标注，别只堆算法。
- **复合步成本的语义**（求和 vs 取最大 vs 加权）需想清楚并在 README 说明。
- **用量与单位**：真正可用需处理"1 杯=？"换算；MVP 可先只给文字提示（原型即如此）。
- **新颖性表述**：务必按 A.3 诚实表述，别声称"首个图方法"，会被懂行的人当场证伪。

### B.10 简历 / 答辩卖点

- 把生活问题干净地**归约为图论问题**，并识别出普通最短路径不够、需要**超图最短超路径**——展示算法成熟度。
- 自己实现广义 Dijkstra 并能讲清正确性，而不是调库黑箱。
- 有测试、有评估、有可解释输出、可离线运行。

---

## C. 附带原型（已可运行）

仓库内已实现到 **Phase 2 + 部分 Phase 3**，并通过 9 个单测：

```bash
pip install -r requirements.txt

# 招牌例子：酪乳 = 牛奶 + 醋
python -m pantrypath.cli --need buttermilk --have milk,white_vinegar,sugar,egg

# 多跳链：奶粉+水 → 牛奶 → (+醋) → 酪乳
python -m pantrypath.cli --need buttermilk --have powdered_milk,water,white_vinegar

# 饮食标签：纯素鸡蛋
python -m pantrypath.cli --need egg --have flaxseed,water --require vegan

# 一次解决多个缺料
python -m pantrypath.cli --need cake_flour,buttermilk --have all_purpose_flour,cornstarch,milk,lemon_juice

pytest -q   # 9 passed
```

实测输出（酪乳）：

```
🍳 目标食材：buttermilk
   总还原成本：0.15   ≈ 口味保真度 85%
   实际使用：milk, white_vinegar
替代方案：
└─ buttermilk  ⇐ 用 milk + white_vinegar  (成本 0.15)
         · 1 杯牛奶 + 1 汤匙白醋，静置 10 分钟
   ├─ milk  ✅ 已有
   └─ white_vinegar  ✅ 已有
```

---

### 主要参考来源

- GISMo / *Learning to Substitute Ingredients in Recipes* — https://arxiv.org/abs/2302.07960 · https://github.com/facebookresearch/gismo
- FlavorGraph — https://www.nature.com/articles/s41598-020-79422-8 · https://github.com/lamypark/FlavorGraph
- *Identifying Ingredient Substitutions Using a Knowledge Graph of Food*（FoodKG / DIISH）— https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2020.621766/full
- *Exploiting Food Embeddings for Ingredient Substitution* — https://github.com/ChantalMP/Exploiting-Food-Embeddings-for-Ingredient-Substitution
- MISKG — https://github.com/kanak8278/MISKG ; healthy-food-subs — https://github.com/MaastrichtU-IDS/healthy-food-subs
- Spoonacular 替代接口 — https://spoonacular.com/food-api/docs
- NetworkX 最短路径 — https://networkx.org/documentation/stable/reference/algorithms/shortest_paths.html
- 算法背景：Knuth (1977) *A Generalization of Dijkstra's Algorithm*；Gallo, Longo, Pallottino, Nguyen (1993) *Directed Hypergraphs and Applications*
