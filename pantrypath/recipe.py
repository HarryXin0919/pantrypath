"""Recipe-block parsing + batch substitution (菜谱整段解析).

Paste a block of ingredient-list text, map each line to a known ingredient,
then for every ingredient you DON'T already have, run the solver once and
aggregate the cheapest substitution chain per missing ingredient.

Design note (respects the project guardrails)
---------------------------------------------
This module contains **no hardcoded substitution knowledge and no ingredient
alias table**. The set of recognizable ingredients comes entirely from the
graph (``sg.ingredients()``, ultimately ``data/substitutions.yaml``). All this
file does is generic text normalization + a longest-match dictionary lookup
against those canonical names, and then delegates to :func:`solver.solve`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from .graph import SubstitutionGraph
from .solver import SubstitutionResult, solve

# Split on anything that is not a latin letter or digit, so canonical names
# ("white_vinegar"), hyphenated text ("all-purpose"), and quantities all break
# into comparable word tokens.
_WORD_SPLIT = re.compile(r"[^a-z0-9]+")


def _words(text: str) -> List[str]:
    return [w for w in _WORD_SPLIT.split(text.lower()) if w]


def _contiguous(hay: List[str], needle: List[str]) -> bool:
    """True if ``needle`` appears as a contiguous run of words inside ``hay``."""
    if not needle:
        return False
    n, m = len(hay), len(needle)
    for i in range(n - m + 1):
        if hay[i : i + m] == needle:
            return True
    return False


def match_line(line: str, known: Sequence[str]) -> Optional[str]:
    """Map one recipe line to a canonical ingredient name, or None.

    Strategy: a known ingredient matches if its words appear as a contiguous
    run in the line (so units/quantities are simply non-matching words). When
    several match, the one with the MOST words wins — e.g. "powdered milk"
    chooses ``powdered_milk`` over the shorter ``milk``.
    """
    words = _words(line)
    if not words:
        return None
    best: Optional[str] = None
    best_len = 0
    for name in known:
        pw = _words(name)
        if len(pw) > best_len and _contiguous(words, pw):
            best, best_len = name, len(pw)
    return best


def _split_lines(text: str) -> List[str]:
    """Split a pasted ingredient block into individual entries.

    Primary format is one ingredient per line. As a convenience, a single line
    with no newlines is also split on commas/semicolons (a common paste form).
    """
    if "\n" not in text and ("," in text or ";" in text):
        raw = re.split(r"[;,]", text)
    else:
        raw = text.splitlines()
    return [s.strip() for s in raw if s.strip()]


@dataclass
class ParsedLine:
    raw: str
    ingredient: Optional[str]  # canonical name, or None if unrecognized


def parse_recipe(text: str, sg: SubstitutionGraph) -> List[ParsedLine]:
    """Parse a recipe ingredient block into per-line matches."""
    known = sg.ingredients()
    return [ParsedLine(raw=line, ingredient=match_line(line, known))
            for line in _split_lines(text)]


@dataclass
class RecipeReport:
    parsed: List[ParsedLine]
    have: List[str]                                  # recipe ingredients already in the pantry
    missing: List[Tuple[str, SubstitutionResult]]    # missing ingredient -> solver result
    unmatched: List[str]                             # lines not mapped to any known ingredient

    @property
    def solvable(self) -> List[Tuple[str, SubstitutionResult]]:
        return [(i, r) for i, r in self.missing if r.found]

    @property
    def unsolvable(self) -> List[Tuple[str, SubstitutionResult]]:
        return [(i, r) for i, r in self.missing if not r.found]


def analyze_recipe(
    sg: SubstitutionGraph,
    text: str,
    pantry: Sequence[str],
    require_tags: Optional[Sequence[str]] = None,
) -> RecipeReport:
    """Parse a recipe block and solve every missing ingredient.

    For each recognized ingredient that is NOT in ``pantry``, run
    :func:`solver.solve` once and collect the result. Ingredients you already
    have are listed separately; unrecognized lines are reported verbatim.
    """
    parsed = parse_recipe(text, sg)
    pantry_set = set(pantry)
    have: List[str] = []
    missing: List[Tuple[str, SubstitutionResult]] = []
    unmatched: List[str] = []
    seen: set = set()

    for pl in parsed:
        if pl.ingredient is None:
            unmatched.append(pl.raw)
            continue
        ing = pl.ingredient
        if ing in seen:
            continue
        seen.add(ing)
        if ing in pantry_set:
            have.append(ing)
        else:
            missing.append((ing, solve(sg, ing, pantry, require_tags=require_tags)))

    return RecipeReport(parsed=parsed, have=have, missing=missing, unmatched=unmatched)
