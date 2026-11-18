# FIN-P24 — Free ChatGPT Direct Engineering Mode

**Decision: 2026-11-18. Owner selected NO separately billed model API, NO Copilot CLI, and NO new paid services.**

## What does the work

- An existing, enabled hourly ChatGPT automation titled **NEXUS QUANT Autonomous Builder** owns engineering coordination. It works directly via already-connected GitHub and Linear apps. No OPENAI_API_KEY or COPILOT_GITHUB_TOKEN is needed for its instruction-driven work. The ChatGPT automation is not the same process as this web server.
- Each automation run verifies the current protected `main` SHA, actual CI, open PRs/issues, task contracts and independent gates. It selects one small eligible work package, directly writes code/tests/docs via connected tools if available, opens a branch/PR and records real GitHub/Linear evidence. It never marks an unverified merge or test as complete.
- Standard GitHub Actions runners are used for repository tests on this **public** repository. See GitHub's current usage/billing documentation; do not select paid larger runners or introduce new billed services.
- Existing free Render Mission Control displays bounded read-only GitHub evidence and SSE events. No new inference service or external paid provider is deployed. Render Free may sleep or lose ephemeral state.

## What the button does and does NOT do

The public dashboard button is explicitly **«بررسی فوری وضعیت پروژه»**. It starts a bounded, real, read-only GitHub audit through `POST /api/start` and shows the status, current `main` SHA, verified CI, next candidate work and blocking evidence. This route uses the existing free dashboard's GitHub connection: it is **not** an inference-provider API, and requires no user-supplied model API key.

This click **does not trigger ChatGPT immediately**. ChatGPT's independent automation continues according to its hourly schedule, even if no one clicks. The work's actual progress is visible from authentic commits, PRs and Actions; the dashboard must never simulate A0–A10 processes or report zero-delay activity from a non-existent runtime.

An entirely API-free live dashboard is not technically possible: its existing web backend still makes read-only GitHub data requests and provides HTTP/SSE endpoints. The owner's no-API constraint is implemented as **no external paid/inference API, no manually generated API key, and no new paid provider**. The GitHub/Linear connections and existing free read-only web backend are infrastructure interfaces.

## Removed superseded provider path

- OpenAI Responses API builder Draft PR #539 closed **without merge**.
- GitHub Copilot CLI Draft PR #537 already closed **without merge**.
- Owner-only paid-model `/api/launch` / `/api/launcher` routes, `launch.js`, and dedicated deploy-key code removed from the dashboard preview PR #535. No OPENAI_API_KEY, NQ_OWNER_START_TOKEN, or NQ_GITHUB_DISPATCH_TOKEN is needed for the chosen mode.
- Live/Auto trading, deposit/withdrawal, leverage or account-change permissions remain disabled.

## Safe operating instructions

1. Verify that the existing hourly ChatGPT scheduled task is **enabled**, retaining repo access and existing safeguards.
2. Inspect current GitHub PRs and CI on each hourly run; avoid duplicates and follow-up on independent security/reviewer gates.
3. Make directly authored, small, independently reviewable changes without an external model provider; include deterministic regression tests.
4. Record exact commit hashes, CI outcomes, bug evidence, reviewer state and blockers in GitHub and Linear.
5. Never self-authorize independent A5/A8/A10 checks or bypass protected main merge; seek owner action only when a real independent gate blocks progress.
6. Never claim whole-project completion until P00–P24, WEB-P0, safety, data quality, demo and GitHub–Linear parity have all passed a fresh final audit.

## Verification checklist

- `P24 Mission Control API Verification`: read-only audit works and paid model launch endpoints now return 404.
- `P24 Agent Trace Telemetry Validation`: no fake event, schema and hash chain intact.
- `Governance Verify`: valid exact head and no safety bypass.
- External read-only preview smoke: homepage loads; current GitHub evidence is shown or `DEGRADED` when unavailable. Direct browser click not certified unless an actual browser interaction is observed.
- ChatGPT automation enabled/last run verified. Separate successful direct ChatGPT code authoring and GitHub CI evidence is required to claim engineering progress.

This arrangement is **periodic, not guaranteed uninterrupted 24/7 autonomous coding**. No new cost is authorized and no specific completion time is promised.
