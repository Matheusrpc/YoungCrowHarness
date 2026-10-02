# Personalizer implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline; request one independent read-only final review.

**Goal:** Deliver a resumable personalizer for new/existing projects and keep README synchronized with a BPMN-style process view.

**Architecture:** Project-local skill shared across clients, stdlib CLI for durable notes, existing vault identity/path validation reused. Agent performs interview, audit and authorized guide adaptation. No autonomous workflow engine.

**Tech stack:** Python 3.11+, Bash, Markdown, Mermaid.

**Spec:** [Personalizer design](../specs/2026-10-02-personalizer-design.md).

## Constraints and review focus

Preserve custom guides, vault and design assets; no secrets or provider installation. Test mode conflict before writes, unsafe paths, existing identity, resumption without duplicate links and delivery state separate from production. Keep controls described as agent procedures where no technical enforcement exists. README PT/EN must match installed features.

## Task 1 — Local workflow

Files: `scripts/personalize.py`, small reusable changes in `scripts/integrations.py`, `tests/test_personalize.py`.

- [x] Run failing tests for `init new`, `init existing`, mode conflict, `feature`, shared UUID, preserved notes, wrong path types and slugs.
- [x] Implement commands using existing check_path/note/slug/project_identity; create exclusive files and append missing links.
- [x] Run tests for both new CLI and integration regression suite.

## Task 2 — Skill and setup

Files: shared skill/reference, two client skill entries, `setup.sh`, `skills-lock.json`, `.gitignore`, setup and native smoke tests.

- [x] Baseline scenario without skill: capture paths and missing resumption contract.
- [x] Add interview/audit/guide-adaptation workflow and reference questions; install through existing selected-client flow.
- [x] Verify native skill discovery and missing-source preflight; preserve old guides.
- [x] Independent skill trial in an isolated existing-project pilot, then fresh-session recovery review.

## Task 3 — Public documentation and closeout

Files: `README.md`, `docs/USAGE.md`, agent guides, report and foundation status.

- [x] Add maintained README requirement; humanize PT/EN prose without changing design assets.
- [x] Add colored Mermaid process with roles, decisions, review loop, authorized production path and persisted handoff; verify rendering.
- [x] Review code, fix material findings with regression tests, run suite and native smoke, update PR #1 with explicit paths.

## Decisions

User approved the scoped personalizer and pilot, and requested README updates plus BPMN-style documentation. Proceed inline on the existing dedicated branch. General vault organization remains lightweight; the dialogue and audit are agent-led, while file creation/preservation are deterministic. External memory adapters and autonomous PM/TL agents stay outside this increment.
