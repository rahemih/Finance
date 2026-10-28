# P24-WO — Offline Preproduction Fault / Kill-Switch Reference Lab

Task Contract: `FIN-P24-WO-001`  
Status: **VALIDATION_PENDING** / branch `test/FIN-P24-WO-001-offline-preproduction-lab`  
Base main: `e1e7ac817ec3d0d9d055ef947f6c5189bf4d7aac`  
Claim: `SYNTHETIC_REHEARSAL_ONLY` / NOT P24-B  
Related: GitHub issue #491, separate PR #492 (`FIN-P24-WR-001`), canonical P20-I reference simulator.

## Why a separate supplementary task?
Owner requested to develop the complete **offline technical part** of P24 while legal, demo-account, credential, broker certification and first-Live Owner approvals are deferred. The frozen P24 sequence remains Manual Live → Semi-Auto → Micro-Capital → Canary → Controlled Auto → Emergency Drills → Monitoring → G13. No P24-B..I stage can be claimed complete from synthetic tests; this is an independent support workstream.

PR #492 owns existing offline venue contract, `CURRENT-STATE.md`, `TASK-CATALOG.md` and `governance.yml`. P24-WO **touches none of these files**: all WO files have a new unique path. There is no shared-writer collision; no canonical stage/state change is made. Because the WR lock and independent review remain pending, WO is **not to be merged or canonically closed without coordinated independent A5/A8/A10 review**.

## Actual implementation
- `config/production/p24-offline-lab-policy.json`: immutable SYNTHETIC-only, network DISABLED, credential NONE, external orders false, market allowlist FOREX/CRYPTO, no monetary Live budget.
- `packages/production/offline_preproduction_lab.py`: hash-chained events, duplicate/out-of-order ID refusal, tick freshness and gap checks, disconnect, unknown ACK, partial fill mismatch, explicit A5 veto, margin warning, independent kill scope STRATEGY/ASSET/MARKET/BROKER/GLOBAL; stop states latch, RESET_REQUEST cannot silently recover.
- `tests/p24/test_offline_preproduction_lab.py`: **40 authored unit/negative tests** incl user input type forgery, network/credential/Live denial, policy tampering, XSS escaping and evidence reproducibility.
- `scripts/ci/p24wo_evidence.py`: reuse exact P20-I policy reference identity, simulate **16 reference scenario tapes**, generate canonical report JSON, scenario CSV and static HTML dashboard. Hashes repeat byte-for-byte by design. All report metrics explicitly say **0 real broker demo events**, **real P&L not measured**.
- `.github/workflows/p24-offline-lab.yml`: isolated CI runs suite and two exact evidence replays and uploads machine-checkable + human-readable artifacts. The existing required Governance workflow still runs on PR and is not modified.

## Strict no-overclaim semantics
- This is **not** real FIBO/cTrader/MetaTrader broker execution validation, market-data verification, performance of a strategy, or an actual deployed Kill Switch.
- A synthetic offline emergency halt is not `PRE_LIVE_KILL_SWITCH_VALIDATED` and cannot satisfy any PRE_FIRST_LIVE marker by itself.
- No websocket, OAuth, network, exchange API, MT5 terminal, real account, credentials, broker orders, real money or risky platform action.
- Do not claim PASS until CI result at this branch head. Do not claim CANONICAL_COMPLETE until approved review, merge, postmerge Governance and record reconciliation.

## Closing checklist (to complete after verified GitHub run)
- [ ] Branch HEAD and required Governance SHA EXACTLY verified
- [ ] Strict Pyright zero errors, all 40 offline tests PASS
- [ ] 16 synthetic scenario tapes replayed; JSON/HTML/CSV byte-identical twice
- [ ] Independent A5, A8, A10 read-only review recorded with signed conclusion, no impersonation
- [ ] Merge sequencing with outstanding PR #492 and its lock safe
- [ ] Postmerge CI / artifact IDs recorded
- [ ] Lock release and final Current-State / Task-Catalog/ Linear reconciliation on a governed closure PR

## Immutable production boundary
`P24-A = CANONICAL_COMPLETE`; `P24-B = BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES`; `P24-C..P24-I = NOT_STARTED`; `PRE_FIRST_LIVE = 0/9`; `FIRST_LIVE_OWNER_GATE = NOT_GRANTED`; `P24_EXIT = 0/3`; `G13 = NOT_STARTED`; `LIVE_TRADING = DISABLED`; `AUTO_TRADING = DISABLED`.

The user may later attach a legitimate Demo MT5 or cTrader account under a separate authorised task; the lab is not an excuse to place actual orders.
