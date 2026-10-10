# Interview guide

Inspired by [grill-me](https://www.aihero.dev/skills-grill-me): resolve the next useful decisions from the answers already available, and recognize questions that need a practical probe. This is an original persistent workflow; no upstream skill is installed or required.

Read only the relevant branch. These are prompts to choose from, not a mandatory questionnaire.

| Missing decision | Useful question | Where to record |
|---|---|---|
| Problem and audience | Who needs this, what do they do today, and what result would make a first version useful? | profile.md |
| First scope | Which user action must work end to end first? What can wait? | profile.md and feature index |
| Existing product | Which behavior/data must survive adoption? Where is the current design documented? | audit.md and adoption.md |
| Acceptance | What observable example proves this delivery works? What should happen on failure? | feature/delivery.md |
| Technical constraints | Which dependencies/hosting are already chosen, and which decisions are still open? | profile.md, canonical decision |
| Information and access | What data is handled, where may it be stored, and who authorizes each environment or provider? Do not ask for secret values. | profile.md and capability catalog |
| Capability governance | Which client and capabilities are required for the next delivery? What read/write, network and environment scope is already authorized? Reuse prior answers; use govern-capabilities for changes. | profile.md and local capability microindex |
| Memory selection | Which vault notes should a fresh session find first? Is Markdown sufficient, or is the optional local Graphify runtime requested? Reuse confirmed privacy and client-AI settings. | profile.md and capability catalog |
| Work and cost | Which deadline, budget or operating limit is fixed? Which remains unknown? | profile.md |
| Execution location | First read the private preference using [the execution guide](execution.md). If unconfirmed, will you work locally (default) or open a dedicated host through Remote SSH? Reuse a configured choice and distinguish it from proven runtime readiness. | profile with source/date; authorized change via missions environment configure |
| Quality and operations | Which test/build checks and release/rollback process are verified today? | audit.md and operations index/linked runbook |
| Responsibilities | Who decides scope, resolves technical conflicts, reviews and authorizes publication? A person can hold several roles. | profile.md |
| Agent defaults | For each PM, Tech Lead, developer and QA role, which client, exact model and effort do you want? Reuse confirmed choices; authenticated Claude Code/Codex is the default. An API choice records an environment variable name, never its secret value. | interview; yc-config saves youngcrow/agents.json |
| Mission limits | What are the mission and agent time limits, total agent runs and deployment attempts? Use the approved defaults of 3 active PBIs, 3 parallel agents and 3 correction cycles unless explicitly changed; correction cycles are fixed in this version. What API budget applies if API use was chosen? | interview and yc-config |
| Mission scope and release | Which one to N features belong to this mission, in which PBI order? Manual release is the default; automatic release is an explicit future intent. Who defines DoR/DoD and observable production evidence? | private backlog and yc-missao |

Before asking, search targeted repository evidence for the answer. If code contradicts documentation, record both and test the narrow claim within authorization. Ask for product choices that files cannot settle.

## Persist each round

Before the first note, resolve whether the owner wants reversible trial. If requested, verify the
pre-adoption baseline before writing. For an existing adoption, consult status and reuse its ID;
an installation without a baseline has no verified pre-adoption return. In `adoption.md`, keep
only ID, date, state and next action for this mechanism. Ask for current-preview confirmation
when exiting; an old note records history and does not authorize the current restoration.

Update `vault/product/interviews/<run>.md` with date, question, answer, source, certainty, decision and remaining dependencies. Keep confirmed answers distinct from suggested defaults. Save the exact next question and pause reason. Don't repeat the same question next session unless new evidence contradicts its answer; explain the contradiction when reopening it.

Interview stop criterion: enough verified context to decide and validate the next authorized delivery. Unknown hosting cost may block a hosting choice while allowing an independent local prototype. Do not treat “I don't know” or a paused conversation as consent.

Keep notes concise and linked. Update the canonical profile/decision once; reference it from interviews and features. Never persist credentials, personal customer data or raw sensitive output.
