# P11-F — Event Horizon / Decay

Task: `FIN-P11-WF-001`  
Linear: `HOS-247`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P11-WF-001-01` / ACQUIRED  
Canonical base: `23d211a5f8e0b6e77e76d2fdafb994c98d98cefd`

## Objective

Add deterministic event horizon and time-decay metadata after P11-E reliability/rumor controls.

## Rules

- `observed_at` is the point-in-time freshness clock;
- base horizon is defined by P11-D importance;
- topic rules provide deterministic minimum horizons;
- P11-E reliability adjusts the usable horizon with integer basis-point multipliers;
- decay is emitted as integer basis points from 10000 to 0;
- state is FRESH / DECAYING / EXPIRED / BLOCKED;
- BLOCKED or QUARANTINED content has zero horizon/decay authority;
- content identity and time ordering fail closed;
- canonical tests are offline;
- production news vendor remains NOT_SELECTED;
- no signal probability, trade timing recommendation, risk or execution authority is introduced;
- LIVE_TRADING and AUTO_TRADING remain DISABLED.
