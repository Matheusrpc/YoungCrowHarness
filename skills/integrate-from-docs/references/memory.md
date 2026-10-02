# Memory handoff

The vault is canonical. Use [retrieve-memory](../../retrieve-memory/SKILL.md) for local selected-note retrieval. Optional Graphify 0.9.73 has explicit setup and validation through `scripts/memory.py`; it does not consume the integration export below. The remaining sections cover manual handoffs to separately configured providers. Automatic synchronization and a claude-mem adapter remain unimplemented.

## Recover

Search the project's provider/service ID and relevant execution using available memory tools. Follow returned paths into the vault. Compare the current note's SHA-256 or commit with the stored revision; stale results are historical pointers, not current facts. If a result lacks project identity, provenance or a resolvable source, do not use it as this project's state. Navigate Markdown indices when a tool is unavailable.

## Prepare

1. Save and read back sanitized notes. Export only the selected integration:

   ```bash
   python3 scripts/integrations.py export --provider example --service payments
   ```

   The JSON contains `project_id`, stable note `id`, vault-relative `path`, SHA-256 `revision`, content and observation time. It is a **YoungCrow envelope**, not a Graphify or claude-mem import payload. It starts as `pending`; exporting performs no transmission. Review content before sending it anywhere; the exporter is not a secret scanner.

2. Discover the actual installed provider tools and read the documentation matching their version. Do not guess tools, flags or endpoints. Optional upstreams:
   - [Graphify](https://github.com/Graphify-Labs/graphify): use `scripts/memory.py index --provider graphify --note PATH` for the selected vault notes, then `query` and open the evidence. This adapter builds explicit Markdown links locally; the current client interprets results. Follow `retrieve-memory` for setup, invalidation and limits.
   - [claude-mem](https://docs.claude-mem.ai/usage/search-tools.md): use available project-scoped search/observation tools. Check its [export/import contract](https://docs.claude-mem.ai/usage/export-import.md) before importing; do not send YoungCrow JSON directly as a vendor import.

## Synchronize only when supported

For capability history, follow `vault/local/capabilities/index.md` when present. Record the capability ID, reviewed input digest, actual authorization reference and current client proof in the integration run. Link the capability and integration both ways locally. Keep private review bundles out of public notes; neither a bundle hash nor a synchronized memory grants permission.

For every projected note include project identity, ID, path, revision and observation time. Summaries/relations should reference feature, vendor, version, decisions, execution, code, actual capabilities, tests and release where the vault supplies evidence. Label inferred relations.

Look up `(project_id, note_id, revision)` before writing. Prefer the installed adapter's verified idempotent upsert; if it cannot avoid duplicate retries or preserve project scope/provenance, leave the handoff pending instead of improvising. A stale revision requires a supported replacement/invalidation operation, including deletion propagation. If these are unsupported, record that limitation and keep the vault as the retrieval path.

After writing, query the destination and validate identity, revision, reference and content. Record provider version, receipt/query evidence and separate states (`verified`, `pending`, `failed`, `unsupported`) in the run. The recorded state applies to the exact exported revision; later edits make that snapshot historical. Do not recursively export sync receipts to make a permanently moving target.

No tool, inaccessible source or failed write: retain the vault, record the specific pending work, and stop dependent projection steps. Never mark both providers synchronized because one succeeded. If sensitive material was captured, sanitize every affected destination using its supported controls and handle any exposed credential; do not reproduce it in logs.

`vault/project.json` belongs to the product repository and should be versioned with its vault. Clones/worktrees of that product keep the same identity. A new independent product must initialize a fresh vault; copying an existing project's knowledge and identity requires an explicit migration decision.
