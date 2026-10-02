---
name: personalizer
description: Use when adapting YoungCrowHarness to a new product idea or adopting it in an existing repository, interviewing the owner, auditing existing conventions, or resuming product discovery.
---

# Personalizer

Turn the owner's idea and existing evidence into a project-specific harness and a small, verifiable first feature. Work with the current authorization; onboarding does not automatically authorize implementing the product, installing tools, spending money or publishing.

## Recover before asking

Read project instructions and `vault/index.md`. If onboarding exists, read `vault/product/index.md`, the profile, relevant interview and adoption notes. Check what changed in the repository since the last record. Reuse confirmed answers; distinguish operator statements, observed files/commands, hypotheses and unknowns. Do not load the whole vault.

When discovery uses documents, attachments or URLs, use `ingest-source`. Read `vault/local/index.md` when present and the linked source receipts. Save source IDs/revisions, evidence, pending IDs/reasons, actual capabilities and next action in a local execution note; link it from the local index. Keep shared product notes free of private links and unreviewed source text.

For first use, determine `new` or `existing` from the request and codebase; ask if ambiguous. From the project root:

```bash
python3 scripts/personalize.py init --mode existing --run initial-discovery
```

Use the actual mode and a lowercase execution ID. This command prepares notes; it does not audit or customize the app. For a resumed interview use its ID. The recorded mode persists in `vault/product/onboarding.json`; a conflict requires reconciling the records rather than deleting them to force the command through. `python` may be the host's Python 3 command.

## Interview and audit

Use [the interview guide](references/interview.md) for missing decisions. Ask a small coherent round whose questions have no unresolved prerequisites; one question is enough when a decision branches the rest. Follow the owner's preferred pace. Don't optimize for a fixed count. Save answers, sources, open questions, dependencies and the next question after every round. If asked to pause, save and end; elapsed time is not an answer.

In an existing project, inspect code/dependencies, actual scripts, tests, design references, instructions, skills/MCPs/hooks, docs and memory. Record findings in `vault/product/audit.md`: observed behavior, documented intent, unknowns and conflicts separately. Confirm a command exists and inspect its side effects before running authorized checks. A README claim is not test evidence; local code does not establish production state.

Preserve unanswered questions. If a decision needs measurements or a prototype, propose a bounded probe and record its evidence when authorized. Do not pick a hosting budget, compliance requirement, destructive migration or vendor permission on behalf of an undecided owner.

## Personalize the project

Consolidate confirmed context in `vault/product/profile.md`: problem/audience, scope and exclusions, stack, design reference, constraints, sensitive-data boundaries, environments, budget/pacing, responsibilities, acceptance criteria and real verification commands. Record production as unknown until environment/revision/date/evidence exist.

In `adoption.md`, list what to preserve/adapt/create and why. Apply the authorized changes to `CLAUDE.md`, `AGENTS.md` and relevant guidance as targeted edits. Retain custom rules and design references; resolve contradictions before dependent edits. Reference the canonical profile rather than copying the entire interview into every client. Show the diff and run pertinent checks. Never use setup `--force` as a semantic migration strategy.

For each needed skill/MCP, record purpose, discovered path/server, origin/version if known, required access, approval owner and actual verification. Availability, necessity and authorization are separate fields. Update `vault/capabilities/index.md`; do not activate unrelated tools or fabricate successful installation.

## First feature and handoff

When the next feature has enough context, prepare it:

```bash
python3 scripts/personalize.py feature --slug booking --run first-slice
```

In `vault/features/<slug>/index.md`, define the result, owner, acceptance and dependencies. In `delivery.md`, split it into small end-to-end deliveries. Link canonical decisions and integrations both ways. Use `integration-specialist`/`integrate-from-docs` when vendor work is needed and available.

PM defines outcome/priority; Tech Lead checks architecture/dependencies/slicing; executor implements; reviewer checks the diff and evidence. These are responsibilities, not a claim that autonomous agents exist. Follow the project's one-writer rule and record whether review was independent. Only implement the feature if the user's scope includes that work.

Every implemented delivery updates the README and affected usage docs. Use the available `humanizer` skill for that prose; preserve the product's visual design and existing examples unless behavior changed. If humanizer is unavailable, report that check as pending instead of claiming it ran.

Record actual capabilities, changes, commands/results, review findings and next step in `runs/<id>.md`. Distinguish development, reviewed delivery, authorized publication and observed production; tests alone don't establish the latter. If publication is outside scope or awaits authorization, persist the pending state and end. Recovery/rollback and re-verification belong to a failed authorized deployment.

Close onboarding when the next delivery's required decisions, responsibilities and checks are established and the authorized guide adaptation is recorded. Broader unknowns may remain listed. Mark interview status accurately (paused, blocked, sufficient for next delivery), read back the notes and leave one concrete next action. Graphify/claude-mem synchronization is separate; this skill does not install their adapters.
