---
name: yc-personalizer
description: Use when starting or resuming YoungCrow onboarding for a new product or existing repository, including agent choices and preparation of a mission with one or more features.
---

# Personalize before mission preparation

Use [the shared personalizer](../personalizer/SKILL.md) for discovery, adoption, audit and guide
adaptation. Follow its recovery/interview workflow before preparing delivery records. Read selected
profile, interview and local index notes; reuse confirmed answers. Preserve the current design system,
instructions, UUIDs and human knowledge. Reading an old approval does not authorize unrelated work.

Before the first write, establish trial versus normal adoption. A requested trial requires its
verified baseline before notes. When already confirmed, reuse mode and adoption ID without another
setup or confirmation. New and existing repositories follow their recorded onboarding mode;
an existing product also needs evidence of conventions, code/tests, integrations and unknowns.
Setup preserves old vault indexes. During authorized adaptation, link newly installed sections from
their declared indexes, appending only missing links and preserving human text. Run the installed
`python3 -B scripts/vault.py check --json` before handoff and reconcile navigation issues.

Ask the next useful unanswered question. Save answers, sources, uncertainty and next action in the
existing interview/profile, preserving private-source boundaries. Use `ingest-source` for supplied
documents and `govern-capabilities` for skill/MCP changes. Neither onboarding nor a catalog enables
tools or grants vendor access automatically.

Follow [the installed execution guide](../personalizer/references/execution.md): read the local
preference before asking about a runner, record source/date, and configure only an authorized
change with its current digest. Reuse client/model/effort answers. Remote SSH is operator access;
the preference neither connects to a host nor verifies an execution profile.

When mission preparation is requested, continue with [yc-config](../yc-config/SKILL.md) for missing
client/model/effort choices and limits. Keep choices project-wide unless explicitly overridden for
a mission. Do not guess models or ask for secrets. Reuse approved defaults and existing answers.

Then use [yc-missao](../yc-missao/SKILL.md) for epics/features/PBIs, DoR/DoD, dependencies and the
selection of one to N features. Preserve legacy feature notes; use the mission's private structured
backlog for new notes. This path takes the place of creating a separate legacy first-feature record.
PM and Tech Lead work as roles in the current session; automatic agents and deployment remain unavailable.

Hand off profile/interview paths, confirmed choices, unresolved gaps, selected notes and the next
command. Update README/usage guidance when an authorized project adaptation is implemented, using
humanizer and the existing visual design. Configuration, planning, development and verified production
remain distinct in the record. Use `yc-status` for a subsequent read-only consultation.
