# 🥛 PantryPath

> *A tiny, explainable, offline engine that turns "I'm out of X" into the cheapest
> substitution chain — by modeling cooking substitutions as a **shortest-hyperpath** problem.
> No ML, no API.*

[![CI](https://github.com/HarryXin0919/pantrypath/actions/workflows/ci.yml/badge.svg)](https://github.com/HarryXin0919/pantrypath/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
![Tests](https://img.shields.io/badge/tests-40%20passed-success)

缺一味料别弃菜。PantryPath 把"食材替代"建模成**图上的最短路径 / 最短超路径**问题，
根据你**现有**的食材，返回还原度最高（走味最少）的替代链。

```
没有酪乳？  →  牛奶 + 醋   （还原度 85%）
```

## 为什么不一样

GitHub 上的同类工具多是"我有这些料能做什么菜"（菜谱检索），或调 Spoonacular 给一层替代。
学术界（GISMo、FlavorGraph、FoodKG）确实用图，但走的是 **ML 嵌入 / GNN**。PantryPath 的差异：

- 🧮 **经典算法**：归约为加权图最短路径 / **有向超图最短超路径**，用 Dijkstra 求解——干净、可证明、可单测。
- 🧪 **复合替代是核心**：酪乳 = 牛奶 **且** 醋。普通图表达不了"同时要两样"，用 **AND/OR 超图**解决。
- 🎒 **口袋感知**：从你已有的食材多源出发，命中即停。
- 🔗 **多跳链**：奶粉+水 → 牛奶 → (+醋) → 酪乳，逐跳累加走味。
- 🔍 **完全可解释 + 离线**：输出一棵替代树和每步成本，不联网、不要 API、不训练模型。
- 🥗 **饮食标签**：可要求保持 `vegan` / `gluten_free`，破坏标签的替代自动排除。

## 快速上手

```bash
# 从源码安装（暂未发布到 PyPI）
git clone https://github.com/HarryXin0919/pantrypath.git
cd pantrypath
pip install -e .        # 装上后可用 pantrypath 命令；开发加 .[dev]，Web UI 加 .[web]

# 招牌例子
python -m pantrypath.cli --need buttermilk --have milk,white_vinegar,sugar,egg
# 或安装后直接：
pantrypath --need buttermilk --have milk,white_vinegar,sugar,egg
```

输出：

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

更多用法：

```bash
# 多跳：奶粉+水 → 牛奶 → 酪乳
python -m pantrypath.cli --need buttermilk --have powdered_milk,water,white_vinegar
# 纯素鸡蛋
python -m pantrypath.cli --need egg --have flaxseed,water --require vegan
# 一次解决多个缺料
python -m pantrypath.cli --need cake_flour,buttermilk --have all_purpose_flour,cornstarch,milk,lemon_juice
# Top-k：除最省外再给次优方案并排比较
python -m pantrypath.cli --need buttermilk --have milk,white_vinegar,lemon_juice,plain_yogurt,water --top-k 3
```

加 `--top-k 3` 时输出多个备选(按还原度排序):

```
🍳 目标食材：buttermilk —— 3 个备选方案（按还原度排序）
【最省】成本 0.15  ≈ 保真度 85%  · 用 milk, white_vinegar
【备选2】成本 0.15  ≈ 保真度 85%  · 用 milk, lemon_juice
【备选3】成本 0.20  ≈ 保真度 80%  · 用 plain_yogurt, water
```

> Top-k 的语义:保留产出该食材的 **前 k 优规则**(每个规则的原料用各自最省子解填充),
> 给出"方案 A / B / C"并排比较。这**不是**完整的 k-最短超路径枚举(那还会变化子解),
> 属未来工作——README 据实表述,不夸大。

### 📋 菜谱整段解析

粘贴一整段配料表，PantryPath 会逐行识别食材、自动跳过你已有的，再对**每个缺料**各跑一次求解，
汇总每个缺料的最省替代链。识别只用知识库里的食材名做最长匹配，数量/单位/不认识的行会被自动处理。

```bash
# 直接传文本
python -m pantrypath.cli recipe --have all_purpose_flour,milk,white_vinegar,sugar \
    --recipe-text "2 cups all-purpose flour
1 cup buttermilk
1/2 cup sugar
1 large egg
1 tsp vanilla extract"

# 从文件读
python -m pantrypath.cli recipe --have milk,white_vinegar --recipe-file cake.txt
# 从管道读
type cake.txt | python -m pantrypath.cli recipe --have milk,white_vinegar      # Windows
cat  cake.txt | python -m pantrypath.cli recipe --have milk,white_vinegar      # macOS/Linux
```

输出（节选）：

```
📋 菜谱解析结果
   识别到 4 种食材（共 5 行）
   ✅ 已有：all_purpose_flour, sugar
   ❓ 未识别（不在知识库里，已跳过）：1 tsp vanilla extract
   🔍 缺料 2 种，其中 1 种可替代，1 种暂无方案
============================================================

🍳 目标食材：buttermilk
   总还原成本：0.15   ≈ 口味保真度 85%
   ...
❌ 找不到「egg」的替代方案（用现有食材无法还原）。
```

## 工作原理（一句话）

每个替代选项 = 一个**规则节点**，把它的若干"原料食材"（AND）连到"目标食材"；
口袋食材成本为 0，跑**广义 Dijkstra**：规则在其所有原料都定值后触发，成本 = 规则成本 + Σ 原料成本；
回溯得到一棵替代树。完整形式化见 [`docs/DESIGN.md`](./docs/DESIGN.md)。

## 知识库

内置 **310 种食材 · 225 个目标 · 449 条替代规则**（经文献核查校正），覆盖乳制品、面粉谷物、糖与糖浆、油脂、
酸/醋、发酵剂、香料(含 AND 复合调料粉如 `pumpkin_pie_spice = 肉桂+姜+肉豆蔻+丁香`)、增稠剂、
巧克力、调味品等。扩充只改 [`pantrypath/data/substitutions.yaml`](./pantrypath/data/substitutions.yaml)，无需动代码：

```yaml
substitutions:
  - target: buttermilk
    options:
      - {components: [milk, white_vinegar], cost: 0.15, note: "1 杯牛奶 + 1 汤匙白醋，静置 10 分钟"}
```

## 测试

```bash
pytest -q     # 40 passed
```

## 设计与竞品调研

算法形式化、成本模型、设计取舍与相似项目（GISMo / FlavorGraph / FoodKG）的诚实对比见
**[`docs/DESIGN.md`](./docs/DESIGN.md)**。想贡献替代规则或参与开发，见
**[`CONTRIBUTING.md`](./CONTRIBUTING.md)**。

## License

MIT — see [LICENSE](./LICENSE).
