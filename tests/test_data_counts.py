"""Guard against doc/data drift.

The README and CLAUDE.md advertise concrete counts (ingredients / targets /
rules). This test recomputes them from the shipped YAML and asserts the docs
still match — so the published numbers can never silently drift again.

If you legitimately change the knowledge base, update EXPECTED below AND the
numbers in README.md / CLAUDE.md in the same commit (the test will remind you).
"""

from pathlib import Path

import yaml

from pantrypath.graph import default_data_path

# Authoritative expected counts. Keep in sync with README.md / CLAUDE.md.
EXPECTED_INGREDIENTS = 310
EXPECTED_TARGETS = 225
EXPECTED_RULES = 449

ROOT = Path(__file__).resolve().parent.parent


def _counts():
    spec = yaml.safe_load(default_data_path().read_text(encoding="utf-8"))
    ings = spec["ingredients"]
    subs = spec["substitutions"]
    return len(ings), len(subs), sum(len(s["options"]) for s in subs)


def test_data_counts_match_expected():
    ings, targets, rules = _counts()
    assert ings == EXPECTED_INGREDIENTS, f"ingredients drifted: {ings} != {EXPECTED_INGREDIENTS}"
    assert targets == EXPECTED_TARGETS, f"targets drifted: {targets} != {EXPECTED_TARGETS}"
    assert rules == EXPECTED_RULES, f"rules drifted: {rules} != {EXPECTED_RULES}"


def test_no_duplicate_target_blocks():
    spec = yaml.safe_load(default_data_path().read_text(encoding="utf-8"))
    targets = [s["target"] for s in spec["substitutions"]]
    dups = sorted({t for t in targets if targets.count(t) > 1})
    assert not dups, f"duplicate target blocks (YAML last-wins would drop rules): {dups}"


def test_docs_cite_the_real_numbers():
    # README + docs/DESIGN.md must contain the true counts (cheap anti-drift check).
    ings, targets, rules = _counts()
    for doc in ("README.md", "docs/DESIGN.md"):
        text = (ROOT / doc).read_text(encoding="utf-8")
        assert str(ings) in text, f"{doc} missing ingredient count {ings}"
        assert str(targets) in text, f"{doc} missing target count {targets}"
        assert str(rules) in text, f"{doc} missing rule count {rules}"
