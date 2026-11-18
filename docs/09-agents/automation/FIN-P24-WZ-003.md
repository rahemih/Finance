# FIN-P24-WZ-003 — Online Mission Control API (proposed)

**Status: DRAFT PR; free Render preview deployed and HTTP health observed, no production acceptance and no financial execution.**

This stacked change is based on `FIN-P24-WZ-002` agent telemetry. A secure, read-only observer is added to expose GitHub evidence and bounded Demo-only self-reported agent events, with auto-reconnecting SSE and an opt-in Render deployment plan. No orders, trading/Live access or secret exposure.

## Runtime interfaces

- `GET /api/health`: process health, no project-completion claims
- `GET /api/state`: latest GitHub runs/PRs/issues plus chain-validated bounded agent event window
- `GET /api/stream`: SSE snapshot, Github updates, agent events and resync
- `GET /api/github/actions/runs/{id}/jobs` and `/pulls/{id}/files`: fixed-path server-side read-only GitHub proxy
- No viewer login endpoint: the Demo-only dashboard and strictly allowlisted GET paths are **public and read-only**.
- `POST /api/events`: service-only Bearer token, 6-field validated envelope, server timestamp, idempotency key, SQLite WAL-compatible transactional journal

On error, show DEGRADED or unknown; never present stale CI as current or infer independent A5/A8/A10 approvals. Hash chain proves local tamper evidence, **not** actual identity or independent agent review.

## Source security

- Runner ingestion token is not sent to browser source or committed. No viewer password or session cookie is required.
- Privileged API write action is limited to inserting validated Demo-only evidence; no remote command or transaction endpoint.
- Public remote mode refuses to start without an HTTPS public origin. `POST /api/events` still requires a strong private runner Bearer token. Never expose broker keys or sensitive data in publicly visible event messages.
- Font CSS references **locally installed** `A Iranian Sans`; the browser also offers `انتخاب فونت Iranian Sans` to load the user-uploaded TTF/OTF/WOFF file once. It stores the binary **only in the user's browser IndexedDB**, then automatically reuses it; no font binary is committed, hosted or sent to any API. This is per-device/per-browser, not synced across devices.
- App does not run production broker credentials or enable Live trading.

## Deployment plan

`render.mission-control.yaml` still describes a *proposed paid* Starter service with persistent disk; do **not** apply that blueprint without distinct budget approval. Separately, a temporary **Render Free preview** is deployed at `https://nq-agent-mission-preview-zeqg.onrender.com` from this PR branch. The health endpoint was observed returning `UP` on 2026-11-17; after public-view changes deploy, `/api/state`, `/api/stream`, and the fixed-path GitHub read-only proxy will be accessible without a viewer password. The preview may sleep, restart or lose transient SQLite records; free preview is NOT a guaranteed always-on/persistent production service. Set exact public HTTPS origin and the private Runner ingestion token via Render's protected environment settings, not GitHub. Optional GitHub token is read-only. Need post-deploy check `/api/health`, public read-only `/api/state`, `/api/stream`, write rejected without ingest token, and actual Runner event.

## Acceptance

Branch-scoped tests, governance PR reviews, read-only enforcement, deployment readiness, visible browser updates and storage recovery evidence. No final completion or permanent online service until remote deploy is truly active and verified.

## Browser-private Iranian Sans checklist

1. Open the public read-only dashboard from the Render URL; no login is required.
2. Click **Aa · انتخاب فونت Iranian Sans** and choose the same font supplied by the owner; it stays in the browser and never leaves the device.
3. The chosen font automatically applies on following visits in that browser; other devices need a separate one-time choice.
4. The UI refreshes through SSE; no manual browser reload is needed. GitHub polling is server-side and freshness/error states remain explicit.
5. Check `tests/automation/test_mission_font_contract.py` and exact PR-head Governance before merge; redeploy free preview only after latest code passes relevant tests.

## Public observation threat model (2026-11-18)

The owner explicitly chose no viewer login. Anyone who knows the preview URL can view public GitHub metadata and a bounded event journal. The HTTP API forwards only a narrow, allowlisted set of GitHub fields; no arbitrary GitHub API JSON is relayed to the browser. **Do not ingest secrets, credentials, account identifiers, personal data, or private code into this public event stream.** Self-reported agent IDs are not authenticated reviewer identities. Ingestion still rejects missing/wrong Bearer tokens, and no mutating/trading endpoint is exposed. Read-only views must be tested separately from write authorization. A real private operations center will need authentication again if telemetry ever becomes sensitive.
