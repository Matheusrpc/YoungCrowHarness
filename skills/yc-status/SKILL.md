---
name: yc-status
description: Use when finding saved YoungCrow missions or consulting their revisions, planning gaps, source freshness, history, saved PBI workspaces or pending projections without changing the project.
---

# Read mission status

Read project instructions. If the user asks which missions exist or has no identifier, run
`python3 -B scripts/missions.py --json list` from the project root. It returns code, UUID,
title, revision and recorded state, including missions whose note projection failed.
It does not validate current sources or blockers; an empty list needs no initialization.
Use a returned code or UUID for the requested detailed status. If selection is ambiguous,
show the summaries and ask which mission the user means. From the project root:

```bash
python3 -B scripts/missions.py --json status M001
```

Replace M001 with the real code or UUID; `python` may be the host's Python 3 command.
This operation is read-only, including before initialization. Do not run personalizer, initialize
storage, import notes, apply defaults or repair projections as part of a consultation.

Report state/revision, planning gaps, `stale_inputs`, event times and projection state. Distinguish
frozen mission configuration from current project defaults. `prepared` means complete planning;
`runtime_available` and `runnable` remain false. Development/QA are not started and production is
unverified. Report client diagnostic receipts separately, with requested/resolved/observed model,
effort, connection, timestamps and limits. Unknown cost or observed model stays unknown.

Report `queue_preview` as the initial backlog: items follow saved priority and list dependency
UUIDs. `first_candidate_id` identifies the first item without dependencies only when current
preparation has no known blockers; otherwise it is null. It does not prove integration,
reserve capacity or authorize dispatch. Keep `next_action` and execution gates unchanged.

```bash
python3 -B scripts/missions.py client runs --mission M001 --json
```

This also reads without initializing, migrating or repairing storage. A successful diagnostic
does not enable mission execution. A `reserved`, `running` or `uncertain` receipt blocks a new
check until resolved. Report the same operation UUID and the evidence needed for reconciliation;
do not issue a fresh UUID, replay the check or reconcile as part of a status request.

For missing or stale evidence, name the next action without performing it. Documents need
`ingest-source`; capability changes need `govern-capabilities`; refinement needs `yc-missao`.
For an explicitly requested repair, continue with `yc-missao`, whose reference covers adoption
and repair. Keep this consultation read-only and report pending/conflict honestly. A read-only
request does not authorize a repair, even when the next action seems obvious.


Mission status includes `workspaces`. To read one saved workspace receipt, use
`python3 -B scripts/missions.py --json workspace status WORKSPACE_UUID`.
This is persisted state, not a fresh Git integrity or cleanliness check. Report its mission/PBI
revisions, pinned base, branch/path and preparing/prepared/releasing/released state separately from
real delivery progress. Do not resume prepare or release as part of status. A pending operation
needs its exact saved request/UUID through `yc-missao` when recovery is requested.
