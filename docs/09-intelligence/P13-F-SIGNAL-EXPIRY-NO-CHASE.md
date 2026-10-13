# P13-F — Signal Expiry / No-Chase

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P13-WF-001`  
Linear: `HOS-266`

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
