# P19-A — Shadow Decisioning

Task: `FIN-P19-WA-001`  
Phase: P19 — Shadow / Replay / Digital Twin  
State: CANONICAL_COMPLETE  
Owner P19 authorization: GRANTED / CONSUMED

## Objective

Record exactly what the governed NEXUS QUANT decision stack **would** decide in SHADOW mode while preserving canonical analytical, risk, firewall, strategy and model lineage and granting zero order-routing or execution authority.

## Canonical inputs

P19-A binds:
- P14-H analytical signal identity/action/probability/geometry;
- P15-I independent risk-validation identity, PASS/VETO state and risk scale;
- P16-H G8 pre-trade firewall identity/state;
- P17 Strategy Registry record identity;
- P17 Model Registry record identity;
- content-addressed provenance for every same-run upstream evidence artifact.

P18 must already be CANONICAL_COMPLETE before P19-A is admissible.

## Dispositions

- `SHADOW_WOULD_TRADE` — directional LONG/SHORT with risk PASS, non-zero governed risk scale and firewall PASS.
- `SHADOW_WAIT` — analytical WAIT.
- `SHADOW_NO_TRADE` — analytical NO_TRADE.
- `SHADOW_BLOCKED_RISK` — risk validation is not PASS or risk scale is zero.
- `SHADOW_BLOCKED_FIREWALL` — final G8 firewall is not PASS.

These are observations only. They are never broker/exchange commands.

## Determinism and replay readiness

Every input has a canonical `input_id`. Every record hashes policy identity, exact upstream lineage and the previous shadow-record identity. The ledger snapshot hashes the ordered record chain. Duplicate input, non-monotonic event time and future information fail closed.

This record chain is the upstream baseline for P19-B Data Replay and P19-C Decision Replay.

## Safety boundary

- environment = SHADOW;
- authority ceiling = SHADOW_ONLY;
- execution authority = false;
- order-routing authority = false;
- broker/exchange routing = false;
- external order submission = false;
- automatic Live promotion = false;
- P20 is not started;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.

P19-A does not claim fill realism, Digital Twin accuracy, live-vs-paper drift validation or G10. Those belong to later P19 workstreams.


## Canonical closure evidence

- Implementation PR: #391 / MERGED.
- Implementation head: `626607a77812da5790714c6aef9981f3fdba24f7`.
- PR Governance: `39045419135` / SUCCESS.
- PR artifact: `12105482008` / `sha256:675bae216666d58e5c662a494ba2bfbd06bc9d3dd2523bfaca1bd4c37d06d474`.
- Merge SHA: `28b650a01a19323506a5fdd69fa8a1ec912f11b5`.
- Post-merge Governance: `39045586525` / SUCCESS.
- Post-merge artifact: `12105956192` / `sha256:8d9a90ba5e5ce75cf4ff4fef26c09f1ce3d657456f48f8a1629e8abd4234a559`.
- Post-merge Branch Hygiene: `39045586461` / SUCCESS.
- Lock: RELEASED.
- Next workstream: P19-B / READY_NOT_STARTED.
