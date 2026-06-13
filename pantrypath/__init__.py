"""PantryPath: model cooking substitutions as a shortest-path / shortest-hyperpath problem."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("pantrypath")
except PackageNotFoundError:
    __version__ = "0.2.0"

from .graph import (
    SubstitutionGraph, load_graph, load_default_graph, default_data_path, InvalidSpecError,
)
from .solver import solve, solve_topk, SubstitutionResult

__all__ = [
    "SubstitutionGraph", "load_graph", "load_default_graph", "default_data_path",
    "InvalidSpecError", "solve", "solve_topk", "SubstitutionResult",
]
