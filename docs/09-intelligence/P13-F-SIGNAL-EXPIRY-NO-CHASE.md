# P13-F — Signal Expiry / No-Chase

State: CANONICAL_COMPLETE  
Task: `FIN-P13-WF-001`  
Linear: `HOS-266`  
Lock: `LOCK-FIN-P13-WF-001-01` / RELEASED

## Objective

Fail closed when a timing/opportunity candidate is stale, explicitly expired, displaced beyond its candidate-specific chase limit, or already blocked by P13-E.

## Canonical model

Inputs are explicit:

- `observed_at_ns`;
- `expires_at_ns`;
- `as_of_ns`;
- unsigned `price_displacement_bps`;
- candidate/strategy-specific `maximum_chase_bps`.

States:

- `ACTIVE`;
- `EXPIRED`;
- `NO_CHASE`;
- `BLOCKED_BY_NO_TRADE`.

P13-F does **not** invent a universal TTL or universal chase threshold. Calibration remains strategy/research-owned and is passed explicitly through governed context.

P13-E `NO_TRADE` is non-bypassable and takes precedence over expiry/no-chase classification.

## Boundaries

- P13-G owns scenarios;
- P13-H owns timing/ranking validation;
- P14 owns probability;
- P15 owns portfolio risk/sizing;
- P16 owns independent risk approval;
- P20 owns execution.

## Safety

- no probability;
- no risk/sizing authority;
- no execution authority;
- canonical tests are offline;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #276 = MERGED
- implementation head `fe010b36ef9769a9d6f21e8dd8ee6a0aa69b270e`
- implementation Governance `38376810071` = SUCCESS
- implementation artifact `sha256:e468e6f79e64854cc189f135a7551e2528d4ceb2640c84b544d9413d48a6bec6`
- implementation merge SHA `3031ff9082efaad75005fd3a5aa1717bd8180abd`
- post-merge Governance `38377012542` = SUCCESS
- Branch Hygiene `38377012711` = SUCCESS
- implementation branch = DELETED
- P13-G = READY_NOT_STARTED
