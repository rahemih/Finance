# P12-H — Versioning / Replay

Task: `FIN-P12-WH-001`  
Linear: `HOS-259`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P12-WH-001-01` / ACQUIRED  
Canonical base: `1eace688861d6010ec3be3d3415087edb04e9a03`

## Objective

Make P12 market-memory evidence reproducible by binding its exact graph, policy and data lineage to the canonical P06-G replay snapshot and by verifying deterministic P12 component outputs.

## Version Bundle

The version bundle records:
- P06-G replay snapshot ID;
- P12-A graph snapshot ID;
- exact SHA-256 of P12-A..P12-G policies;
- graph source-dataset versions;
- replay dataset versions;
- graph provenance SHA-256;
- replay as-of time;
- deterministic version ID.

P06-G remains the anti-lookahead owner. Graph evidence whose window extends beyond the replay as-of fails closed.

## Replay Record

P12-H hashes canonical JSON outputs from:
- P12-B conditional correlation;
- P12-C lead/lag;
- P12-D event study;
- P12-E historical analog;
- P12-F seasonality;
- P12-G attribution guardrails.

Identical inputs must produce identical component digests and replay record IDs. Any mismatch fails closed.

## Boundary

P12-H validates market-memory reproducibility only. End-to-end decision replay, incident replay and digital twin remain owned by P19.

## Safety

No probability, signal, risk approval or execution authority is introduced. Production memory-version storage vendor remains NOT_SELECTED. LIVE_TRADING and AUTO_TRADING remain DISABLED.
