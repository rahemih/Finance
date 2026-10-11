# P11-F — Event Horizon / Decay

Task: `FIN-P11-WF-001`  
Linear: `HOS-247`  
State: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P11-WF-001-01` / RELEASED  
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


## Canonical closure evidence
- PR #232 merged as `b2521cffea9fc758275f4d7590e2b997ef05422a`
- Owner approval head `7a6e538186649cb28f4d6627cd48c27032f58278`
- approved artifact `sha256:f82698de0fa992b5a2520e30689e2cbbc41828e7c554e3bffb7bd5c36f95c133`
- implementation Governance `38126526154` = SUCCESS
- post-merge Governance `38127123794` = SUCCESS
- post-merge Branch Hygiene `38127123793` = SUCCESS
- P11-G = READY_NOT_STARTED
