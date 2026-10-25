# YoungCrow rules

Four rules for every agent that works in this project, and one rule about proof.

## 1. Measure before you claim

Every deliverable has a test. A report shows the output of the command (`ls`, `sha256sum`, a log, a capture), not an adjective. "It works" without proof does not count.

## 2. Keep secrets out of git

`.env` stays local and never enters git. `.env.example` holds fake values only. A secret never goes in a command-line argument and is never printed.

## 3. Stop when reality differs from the plan

If a version, a permission or a path is not what you expected, stop and report. Do not improvise on top of an assumption that has already failed.

## 4. One writer per checkout

Only one agent session works in a checkout at a time. For parallel work, use `git worktree` with its own directory and its own HEAD. Never run `git checkout -b` in a shared checkout.

## Proof note

Each delivery leaves a short note in `vault/` (start at `vault/index.md`) with the command and the output that prove it. The note starts with the vault frontmatter (`id`, `type`, `title`, `origin`, `updated`, `index`) and is linked from an index. Before you finish, `python3 .youngcrow/scripts/vault.py check` must pass.
