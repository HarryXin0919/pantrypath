# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-06-13

### Fixed
- `--version` now reports the correct release. `__version__` is derived from
  installed package metadata instead of a hardcoded constant that had drifted to
  0.1.1; a new test asserts it matches `pyproject.toml` so they cannot drift again.

## [0.2.0] - 2026-06-13

### Added
- `--version` flag and bilingual (English / 中文) CLI output.
- GitHub Actions CI running the test suite on Python 3.10–3.12 across Ubuntu,
  macOS, and Windows, plus a build + `twine check` job.
- `CONTRIBUTING.md` (setup, test workflow, how to add a substitution rule) and
  `docs/DESIGN.md` (formal model, cost semantics, prior-art comparison).
- English-first README with a curated badge row.

### Fixed
- Hardened spec validation with precise, located error messages for malformed
  specs (missing target/options/components, negative cost, empty/None spec).
- De-duplicate repeated components within an AND rule so the rule can actually
  fire (a rule listing a component twice previously never satisfied its counter).

### Removed
- Internal AI-scaffolding files (`CLAUDE.md`, `HANDOFF_PROMPT.md`, `PLAN.md`);
  their durable content was folded into `docs/DESIGN.md` and `CONTRIBUTING.md`.

## [0.1.1] - 2026-05-31

### Changed
- Literature audit of the substitution knowledge base: high-risk rules (compound
  AND combinations and chemical-transformation pairs) verified against culinary
  references; external-condition / ratio notes added and one bogus rule removed.
  Knowledge base now holds 310 ingredients / 225 targets / 449 rules.

## [0.1.0] - 2026-05-30

### Added
- Initial release: AND/OR hypergraph model + generalized Dijkstra solver, CLI
  (`--need` / `--have`, `recipe` subcommand, `--top-k`), Streamlit web UI,
  evaluation harness (Precision@k / MRR / Coverage), and a YAML knowledge base.
