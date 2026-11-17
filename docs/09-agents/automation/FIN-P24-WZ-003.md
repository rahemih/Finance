# FIN-P24-WZ-003 — Online Mission Control API (proposed)

**Status: DRAFT PR; free Render preview deployed and HTTP health observed, no production acceptance and no financial execution.**

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
- Font CSS references **locally installed** `A Iranian Sans`; the browser also offers `انتخاب فونت Iranian Sans` to load the user-uploaded TTF/OTF/WOFF file once. It stores the binary **only in the user's browser IndexedDB**, then automatically reuses it; no font binary is committed, hosted or sent to any API. This is per-device/per-browser, not synced across devices.
- App does not run production broker credentials or enable Live trading.

## Deployment plan

`render.mission-control.yaml` still describes a *proposed paid* Starter service with persistent disk; do **not** apply that blueprint without distinct budget approval. Separately, a temporary **Render Free preview** is deployed at `https://nq-agent-mission-preview-zeqg.onrender.com` from this PR branch. The health endpoint was observed returning `UP` on 2026-11-17, while private `/api/state` correctly requires viewer authentication (401 without session). The preview may sleep, restart or lose transient SQLite records; free preview is NOT a guaranteed always-on/persistent production service. Set viewer password and exact public HTTPS origin via Render's protected environment settings, not GitHub. Optional GitHub token is read-only. Need post-deploy check `/api/health`, authenticated `/api/state`, `/api/stream`, write rejected without ingest token, and actual Runner event.

## Acceptance

Branch-scoped tests, governance PR reviews, read-only enforcement, deployment readiness, visible browser updates and storage recovery evidence. No final completion or permanent online service until remote deploy is truly active and verified.

## Browser-private Iranian Sans checklist

1. Open the protected dashboard from the Render URL and sign in using the viewer password stored in Render (do not share it in PRs/chat).
2. Click **Aa · انتخاب فونت Iranian Sans** and choose the same font supplied by the owner; it stays in the browser and never leaves the device.
3. The chosen font automatically applies on following visits in that browser; other devices need a separate one-time choice.
4. The UI refreshes through SSE; no manual browser reload is needed. GitHub polling is server-side and freshness/error states remain explicit.
5. Check `tests/automation/test_mission_font_contract.py` and exact PR-head Governance before merge; redeploy free preview only after latest code passes relevant tests.
