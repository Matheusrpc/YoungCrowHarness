# Integration vault implementation plan

> **For agentic workers:** Use superpowers:executing-plans for inline implementation; a read-only reviewer checks the final change.

**Goal:** Install a navigable integration vault and a documentation-driven specialist in Claude Code and Codex.

**Architecture:** Versioned Markdown is canonical. A Python standard-library command creates notes and links without replacing knowledge, and exports revision-addressed records for optional memory tools. Native client entries load one shared skill. No background service or automatic vendor installation.

**Tech Stack:** Bash, Python 3.11+, Markdown, YAML frontmatter, TOML.

**Spec:** [Integration knowledge](../specs/2026-10-01-integration-knowledge-design.md).

## Global constraints

- Preserve existing consumer notes even with `--force`; one writer per checkout.
- Keep credentials out of notes and exports; do not change the stained-glass design assets.
- Installed clients receive project-scoped specialist/skill discovery files.
- Saving/exporting a note never means Graphify or claude-mem synchronized it.
- Provider adapters remain optional and require verified installed capabilities; no fabricated API or success.

## Review focus

1. Existing vault indices: append a missing navigation link without replacing custom prose.
2. Invalid slugs, symlinks, junctions and wrong path types: reject before writes.
3. Repeated setup including force: preserve knowledge and avoid duplicate links.
4. Cross-project identity and revisions: stable within a project, distinct in independent projects; changed note changes hash.
5. Unavailable sources/memory: record blockers and unknown production status, never invent successful sync.

## Task 1 — Vault and setup

Files: `scripts/integrations.py`, `vault/{index.md,integrations/index.md,capabilities/index.md}`, `setup.sh`, `tests/test_integrations.py`, `tests/test_setup.py`.

- [x] Add failing tests for `python scripts/integrations.py init --provider example --service payments --run first` in a temporary project; repeat and compare bytes, inspect index links and records.
- [x] Add validation tests for traversal, wrong path types and linked parents; preflight must precede any notes.
- [x] Implement `init` using pathlib, exclusive creation and explicit links; UUID project identity in `vault/project.json`; deterministic note IDs scoped by that identity.
- [x] Implement `export --provider example --service payments`: JSON on stdout only, source-relative paths and SHA-256 revisions, state `pending`; no transmission. Test project isolation and changes.
- [x] Install common files and client-specific entries; test both single-client modes and preservation with force.
- [x] Run `python -m unittest discover -s tests -v` and Bash syntax check.

## Task 2 — Specialist, recovery and guide

Files: `skills/integrate-from-docs/{SKILL.md,references/memory.md}`, `.claude/{agents/integration-specialist.md,skills/integrate-from-docs/SKILL.md}`, `.codex/agents/integration-specialist.toml`, `.agents/skills/integrate-from-docs/SKILL.md`, `tests/smoke_clients.py`, `docs/USAGE.md`, `README.md`, specification and report.

- [x] Baseline scenario: unavailable official source, SDK/API mismatch, stale production claim, missing memory tools. Record actual behavior.
- [x] Write shared skill: vault paths, official source verification, version conflicts, authorized implementation/test, explicit development/production states, capabilities used, separate memory status.
- [x] Test a fresh evaluator using the installed skill; verify concrete artifacts and another session's recovery.
- [x] Check native loaders where available; document unavailable checks explicitly.
- [x] Update PT/EN usage with fresh setup, migration, invocation, init/export, recovery and optional memory limitations. Update status from planned to implemented where proven.
- [x] Request independent read-only code review, fix material findings, run relevant checks, commit explicit paths and update draft PR #1.

## Execution notes

- User authorized execution of the documented design. Existing dedicated branch is reused.
- Baseline: safe handling of unreachable docs, but ad hoc `docs/integrations/` and a single index; no shared note IDs, capability provenance or projection revision contract. The skill supplies those missing conventions.
- Scope: implements the working local core and optional memory handoff. Provider-specific automatic synchronization is not claimed; I04 remains dependent on selecting and validating adapter versions as required by the approved foundation.

- Final review: two Important findings (junctions on Python 3.11 and missing links in a custom service index); both reproduced RED, corrected, then GREEN in vault tests. Native Windows setup junction regression passed too. No deferred minors.
- Recovery: independent reviewer reconstructed the fixture outcome using only vault notes. Native loaders recognized both specialist entries and skills.
