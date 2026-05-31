# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions CI running the test suite on Python 3.10–3.12.
- `CONTRIBUTING.md` (setup, test workflow, how to add a substitution rule) and
  `docs/DESIGN.md` (formal model, cost semantics, prior-art comparison).
- English-first README with a curated badge row.

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
