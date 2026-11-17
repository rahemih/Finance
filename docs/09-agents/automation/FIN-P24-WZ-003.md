# FIN-P24-WZ-003 — Online Mission Control API (proposed)

**Status: PR-only / not deployed / no financial execution.**

This stacked change is based on `FIN-P24-WZ-002` agent telemetry. A secure, read-only observer is added to expose GitHub evidence and bounded Demo-only self-reported agent events, with auto-reconnecting SSE and an opt-in Render deployment plan. No orders, trading/Live access or secret exposure.

## Runtime interfaces

- `GET /api/health`: process health, no project-completion claims
- `GET /api/state`: latest GitHub runs/PRs/issues plus chain-validated bounded agent event window
- `GET /api/stream`: SSE snapshot, Github updates, agent events and resync
- `GET /api/github/actions/runs/{id}/jobs` and `/pulls/{id}/files`: fixed-path server-side read-only GitHub proxy
- `POST /api/login`: rate-limited password login, HttpOnly SameSite cookie, HTTPS-only
- `POST /api/events`: service-only Bearer token, 6-field validated envelope, server timestamp, idempotency key, SQLite WAL-compatible transactional journal

On error, show DEGRADED or unknown; never present stale CI as current or infer independent A5/A8/A10 approvals. Hash chain proves local tamper evidence, **not** actual identity or independent agent review.

## Source security

- Runner token and viewer password are not sent to browser source or committed.
- Privileged API write action is limited to inserting validated Demo-only evidence; no remote command or transaction endpoint.
- Public remote mode refuses to start unless HTTPS public origin and strong secrets configured.
- Font CSS references **locally installed** `A Iranian Sans` without shipping a font file or adding a source-license risk.
- App does not run production broker credentials or enable Live trading.

## Deployment plan

`render.mission-control.yaml` creates a paid Starter service with 1 GB persistent disk in Frankfurt. **Planning is safe; do not apply without budget approval**. Set viewer password and exact public HTTPS origin via Render's protected environment settings, not GitHub. Optional GitHub token is read-only. Need post-deploy check `/api/health`, authenticated `/api/state`, `/api/stream`, write rejected without ingest token, and actual Runner event.

## Acceptance

Branch-scoped tests, governance PR reviews, read-only enforcement, deployment readiness, visible browser updates and storage recovery evidence. No final completion or permanent online service until remote deploy is truly active and verified.
