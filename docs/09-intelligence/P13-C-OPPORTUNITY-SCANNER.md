# P13-C — Opportunity Scanner

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P13-WC-001`  
Linear: `HOS-263`

## Objective

Convert canonical P13-B timing assessments into a deterministic set of timing-context opportunity candidates without ranking them or granting trade authority.

## Canonical states

- `PREFERRED` / `STANDARD` → `ELIGIBLE_TIMING_CONTEXT`;
- `WEAK` → `OBSERVE_ONLY`;
- `INSUFFICIENT_EVIDENCE` / `CLOSED_CONTEXT` → `INELIGIBLE_CONTEXT`.

Every candidate carries a deterministic SHA-256 identity, asset/strategy/timeframe/regime/session context, P13-B timing class and explicit provenance/dataset lineage.

Output ordering is canonical and stable only. It is **not** opportunity ranking.

## Boundaries

- P13-D owns ranking;
- P13-E owns hard no-trade decisions;
- P13-F owns signal expiry/no-chase;
- P14 owns signal probability;
- no risk approval or execution authority;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.
