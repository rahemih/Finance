# FIN-P24-WZ-004 — Owner Start / Resume Evidence Audit

**Status: DRAFT, read-only bounded resume. NOT an autonomous coding runner or financial trading capability.**

## Intended outcome
On the Demo-only Mission Control, the public Start button triggers one genuine fixed-target GitHub audit in a background thread. It streams real status and journal events by SSE, checks current rahemih/Finance main SHA, open PRs/issues, exact-main Governance CI, and suggests the next canonical work item.

No mock agent animation. **AUDIT_COMPLETE never means PROJECT_COMPLETE**, and no authority to mutate GitHub, execute shell commands, handle keys, trade, or bypass A5/A8/A10 is conferred.

## API contracts
- GET /api/control: read-only current run status.
- POST /api/start: only JSON {"action":"resume_audit"}; read-only fixed-target audit, finite rate cap, 202/429/errors.
- GET /api/state and /api/stream: audit state with GitHub and trace; SSE control event.
- POST /api/events: existing Bearer token required, Demo-only event schema.

Start enforces same-origin browser action when remote, fixed JSON payload, one in-flight worker, and a 300-second cooldown. Transient read errors retry at most three times. Permission/rate-limit errors and missing evidence fail closed. The cooldown is in process only, not a distributed auth boundary.

## Sources and execution
- mission_control_runtime.py: deterministic A0/A9 diagnostic worker, four allowlisted read-only GitHub endpoints, current SHA, backlog candidate.
- mission_control_server.py: start/status endpoints and validated journal/SSE bridge.
- control.js + dashboard: honest live run ID, step, retries, blocker and GitHub evidence link.
- Dockerfile.mission-control: ships worker with no new dependencies.
- Tests: test_mission_control_runtime.py and test_mission_control_start_http.py; no financial connection.

A0/A9 here are runtime diagnostic labels. This does not instantiate independent PydanticAI A0–A10 specialists or provide independent security/financial risk approval. Trace identity remains explicitly unverified.

## Why full auto-code is not publicly enabled
The public viewer no longer authenticates users. Allowing its Start button to invoke GitHub writes, model-driven shell commands, broker tools, expensive jobs or arbitrary agent spawning would let anyone on the internet do so. A real coding runner requires authenticated owner control, scoped GitHub App/Action authority, provisioned governed model runtime and budget, persistent checkpoint, and independent A5/A8/A10 gates before it can safely make changes. A future authenticated engine may create scoped branches/PRs and run tests after those prerequisites are satisfied; this release does not claim such operations.

## Continuity, failure and security
Canonical GitHub state is the source of truth. Render Free may sleep/restart and has no guaranteed persistent journal; interrupted audit resumes from freshly fetched main/PR/issue evidence, never by assuming an incomplete mutation succeeded. GitHub API access can be limited without a read-only NQ_GITHUB_TOKEN configured in protected Render settings. Never expose secrets/account data in public events. No Live/Auto trading.

## DoD
Exact-head tests and Governance successful; public Start and /api/control live smoke tested; all mutating and cross-origin calls rejected, finite retry verified, no false project completion. Draft PR still requires the repository's independent gate and protected merge before canonical closure.
