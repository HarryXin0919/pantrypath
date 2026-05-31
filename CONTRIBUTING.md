# Contributing to PantryPath

Thanks for your interest in improving PantryPath! This guide covers setup, the
test workflow, and how to extend the substitution knowledge base.

For the design rationale (why a hypergraph, why a hand-written solver, the cost
model, prior work), see [`docs/DESIGN.md`](docs/DESIGN.md).

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"            # editable install with dev extras
# optional: the Streamlit web UI
pip install -e ".[web]"
```

## Running the tests

```bash
pytest -q                          # expect 40 passed
```

Every behavioral change should be test-first: add or update a test, then
implement, and keep `pytest` green before moving on.

## Running it locally

```bash
# CLI
python -m pantrypath.cli --need buttermilk --have milk,white_vinegar
pantrypath --need egg --have flaxseed,water --require vegan   # console script after install

# recipe-block parsing
python -m pantrypath.cli recipe --have milk,white_vinegar --recipe-file cake.txt

# evaluation
pantrypath-eval
```

## Adding a substitution rule

All substitution knowledge lives in **`pantrypath/data/substitutions.yaml`** —
never hard-code substitutions into the Python source. To add one:

1. Make sure every ingredient you reference is defined under `ingredients:` (with
   its `tags` and `category`). Add it if missing.
2. Add an `options` entry under the relevant `target`, listing the `components`
   (the AND inputs), a `cost` in the range 0–1 (smaller = closer to the original),
   and a short `note` with quantities/conditions.

   ```yaml
   substitutions:
     - target: buttermilk
       options:
         - {components: [milk, white_vinegar], cost: 0.15, note: "1 cup milk + 1 tbsp white vinegar, rest 10 min"}
   ```

3. Add a test for any important new path (see `tests/test_solver.py` for the
   pattern), and update the counts in `tests/test_data_counts.py` plus the
   knowledge-base numbers in `README.md` and `docs/DESIGN.md` in the same commit
   (the anti-drift test enforces this).
4. Run `pytest -q` and confirm it is green.

## Conventions

- Code comments and docs may mix English and Chinese (matching the existing style).
- Keep the cost semantics additive (a compound step's cost = rule cost + Σ component
  costs). Changing this requires updating `docs/DESIGN.md` and the tests together.

## Known quirk

In some sandboxes `pytest` triggers a `RecursionError` while cleaning up the temp
directory on exit. That is an environment tmp-cleanup issue, **not** a test failure;
work around it with `pytest --basetemp=/tmp/pp -p no:cacheprovider`.
