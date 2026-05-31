# PantryPath — Design & Background

This document records *why* PantryPath is built the way it is: the formal model,
the cost semantics, the design constraints that must not be "optimized away", and
an honest comparison with prior work. For *how to build, test and contribute*, see
[`../CONTRIBUTING.md`](../CONTRIBUTING.md). For usage, see [`../README.md`](../README.md).

The knowledge base currently ships **310 ingredients · 225 targets · 449 substitution rules**.

---

## 1. The formal model

### 1.1 Why a plain weighted graph is not enough

Modeling "A can be replaced by B" as an edge `A → B` and running Dijkstra only
handles 1→1 substitutions. The signature example — **buttermilk = milk + vinegar** —
is 1→**many** (an AND): you need milk *and* vinegar at the same time. In an ordinary
graph an edge points to a single successor, so it cannot express "needs both B and C".

### 1.2 The correct model: AND/OR directed hypergraph

Each substitution *option* becomes a **rule node**. Its component ingredients (the
AND inputs) feed into the rule node, and the rule node points to the target ingredient:

```
component_1 ─┐
component_2 ─┼──▶ (rule, weight = fidelity cost) ──▶ target
component_3 ─┘     (AND inputs: the rule fires only when ALL are available)
```

- Multiple rules under the same target are **OR** alternatives (the solver picks the cheapest).
- A 1→1 substitution is just a single-element AND (the degenerate case).
- This is exactly a **directed hypergraph**: a hyperedge whose *tail* is a set of
  ingredients and whose *head* is the target ingredient.

In the code, rule nodes are `__rule_N__` with `kind="rule"` in `graph.py`. They are
**part of the model, not stray data** — do not collapse the hypergraph back into a
plain weighted graph.

### 1.3 Solving = shortest B-hyperpath

This is a generalization of Dijkstra:

- `cost[x]` = minimum total fidelity cost of obtaining ingredient `x`, starting from
  the ingredients you already have.
- Pantry ingredients have `cost = 0` and act as multiple source nodes.
- A rule node may fire only when **all** of its tail ingredients are settled; its
  firing cost is `rule weight + Σ (cost of each tail ingredient)`.
- Because all weights are ≥ 0 and Dijkstra settles nodes in non-decreasing cost
  order, the first time a rule becomes "complete" it is at its minimum cost — so
  correctness is provable.

### 1.4 Why a hand-written generalized Dijkstra (not `nx.dijkstra`)

NetworkX's built-in Dijkstra only understands "take the min at a node" (OR
semantics). It does **not** understand "sum over all components at a rule node"
(AND semantics). The generalized Dijkstra in `solver.py` — which counts down
`remaining[r]` per rule and only fires once all components are settled — is
deliberate. Do not replace it with a library call.

### 1.5 Cost model

- Edge weight = **fidelity cost** (loss of taste/texture), suggested range 0–1,
  where smaller is closer to the original.
- Path cost = the sum along the chain (more hops → more drift, which matches
  intuition). Taste fidelity ≈ `(1 − total cost)`.
- A compound step's cost = `rule's own cost + Σ (cost of each component)`.
- Design trade-off: a compound step could use "sum" or "max" semantics. PantryPath
  uses **sum** (standard additive B-hyperpath) because it is simple and explainable.
  Changing this requires updating this document and the tests together.

### 1.6 Algorithm (pseudocode)

```
input: hypergraph G, pantry, target, required tags
cost[*] = +inf;  for p in pantry: cost[p] = 0, push(0, p)
for each rule r: remaining[r] = |components(r)|, accrued[r] = 0
while heap not empty:
    (d, u) = pop-min;  if u already settled: continue;  mark u settled
    if u == target: break
    for each rule r whose tail contains u:        # u → r
        if r violates required tags: skip
        accrued[r] += cost[u];  remaining[r] -= 1
        if remaining[r] == 0:                      # complete, rule can fire
            t = head(r);  cand = weight(r) + accrued[r]
            if cand < cost[t]: cost[t] = cand; source[t] = r; push(cand, t)
backtrack: from target, follow source-rule → its tail ingredients recursively
           into a substitution tree; pantry ingredients are leaves
```

- **Complexity**: O((V + ΣE) log V), where V = number of ingredients and ΣE = the
  sum of all rule tail sizes. For a home-scale knowledge base it returns instantly.
- Multi-hop, compound, and pantry constraints are handled uniformly in one pass.

### 1.7 Data / code separation

Substitution knowledge lives **only** in `pantrypath/data/substitutions.yaml`. Do
not hard-code substitutions into `.py` files. The `tags` field on each ingredient
powers dietary filtering (a rule using an ingredient that lacks a required tag is
filtered out). Contributors extend the knowledge base by editing the YAML alone.

```yaml
ingredients:
  buttermilk:    {tags: [vegetarian], category: dairy}
  milk:          {tags: [vegetarian], category: dairy}
  white_vinegar: {tags: [vegetarian, vegan, gluten_free, dairy_free], category: acid}
substitutions:
  - target: buttermilk
    options:
      - {components: [milk, white_vinegar], cost: 0.15, note: "1 cup milk + 1 tbsp white vinegar, rest 10 min"}
```

---

## 2. Prior work and honest novelty

Modeling ingredient substitution as a graph is **not** new — there are several
academic papers and open-source repositories that do this. PantryPath does not
claim to be "the first graph method". Its honest, defensible novelty is that it
solves the problem with **classic shortest-(hyper)path search** rather than machine
learning, and that it makes **compound (AND) substitutions, pantry-awareness,
explainability, zero models and zero external APIs** first-class.

### 2.1 Academic: graph / knowledge-graph substitution (closest, but ML-based)

| Project | Approach | Relationship to PantryPath |
|---|---|---|
| **GISMo** (Meta AI, *Learning to Substitute Ingredients in Recipes*, 2023; `facebookresearch/gismo`) | A GNN over an ingredient graph, conditioned on recipe context, to rank substitutes for a single ingredient; released the Recipe1MSubs dataset (~70k substitution pairs) | The most direct "graph-based substitution" precedent. But it outputs 1→1 candidates using learned embeddings; it does **not** do multi-hop chains, shortest-path solving, or "milk + vinegar" AND compounds. |
| **FlavorGraph** (Sony AI + Korea University, *Scientific Reports* 2020; `lamypark/FlavorGraph`) | 6,653 ingredient nodes + chemical-compound nodes, edge weights from co-occurrence across a million recipes; metapath2vec embeddings for pairing/substitution | A weighted ingredient graph, but weights are co-occurrence frequency and solving is by vector similarity — **not** path search. |
| **Identifying Ingredient Substitutions Using a KG of Food** (RPI + IBM, Shirai et al., *Frontiers in AI* 2021; FoodKG) | Knowledge graph (FoodOn taxonomy + USDA nutrition) + word2vec, with the **DIISH** heuristic to rank "healthy" substitutes | Overlaps strongly with dietary-tag substitution; its health/diet constraint modeling is worth borrowing. |
| **Exploiting Food Embeddings for Ingredient Substitution** (Pellegrini et al., 2021) | Food2Vec / FoodBERT embeddings + clustering to judge substitutability | Pure embedding approach, no graph path search. |

### 2.2 Commercial APIs (1-hop, black box, online/paid)

- **Spoonacular** `food/ingredients/substitutes`: returns a list of substitutes with
  text notes. One layer only, no chains, not explainable, billed per call.
- **Edamam** and similar.

### 2.3 Hobby projects

Most GitHub projects in this space answer "what can I cook with these ingredients?"
(recipe retrieval) rather than "I'm out of one ingredient — how do I rescue the
dish?" LLM-based one-shot substitution tools also exist but have no graph, no
shortest path, and unstable output.

### 2.4 PantryPath's differentiators

1. **Classic algorithm, not ML**: the problem is reduced to weighted shortest path /
   shortest hyperpath and solved with a generalized Dijkstra — clear, provable, unit-testable.
2. **Compound (AND) substitution is the core**, not an afterthought (requires a
   directed hypergraph; cf. Knuth 1977, Gallo et al. 1993).
3. **Pantry-aware multi-source search**: start from what you already have, stop on hit.
4. **Fully explainable + offline + no external API**: outputs a substitution tree
   with per-step fidelity cost; no network, no paid endpoints, no trained model.
5. **Multi-hop chains**: e.g. powdered milk + water → milk → (+ vinegar) → buttermilk;
   per-hop cost accumulation naturally reflects "each substitution drifts the dish a little".

### 2.5 Evaluation

`pantrypath-eval` computes Precision@k / MRR / Coverage against a bundled
ground-truth set (`pantrypath/data/eval_truth.yaml`). This is a self-evaluation on
the project's own ground truth, not a comparison against an external baseline; a
Spoonacular 1-hop comparison remains possible future work.

---

## References

- GISMo / *Learning to Substitute Ingredients in Recipes* — https://arxiv.org/abs/2302.07960 · https://github.com/facebookresearch/gismo
- FlavorGraph — https://www.nature.com/articles/s41598-020-79422-8 · https://github.com/lamypark/FlavorGraph
- *Identifying Ingredient Substitutions Using a Knowledge Graph of Food* (FoodKG / DIISH) — https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2020.621766/full
- *Exploiting Food Embeddings for Ingredient Substitution* — https://github.com/ChantalMP/Exploiting-Food-Embeddings-for-Ingredient-Substitution
- Spoonacular substitution API — https://spoonacular.com/food-api/docs
- NetworkX shortest paths — https://networkx.org/documentation/stable/reference/algorithms/shortest_paths.html
- Algorithmic background: Knuth (1977) *A Generalization of Dijkstra's Algorithm*; Gallo, Longo, Pallottino, Nguyen (1993) *Directed Hypergraphs and Applications*
