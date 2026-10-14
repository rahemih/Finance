# P15-B — Position Sizing

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P15-WB-001`  
Linear: `NEXUS QUANT — Management Control & Reporting Register-1`

## Objective

Convert an already-governed P15-A risk-capacity allowance into a deterministic **candidate quantity** using explicit equity, stop geometry and instrument parameters.

## Formula

For the linear price-loss model:

`risk_amount = account_equity × risk_budget_bps / 10000`

`per_unit_stop_loss = abs(entry_price - stop_price) × contract_multiplier`

`raw_quantity = risk_amount / per_unit_stop_loss`

The result is floored to the explicit `quantity_step`. The resulting planned stop loss may never exceed the risk amount.

## Fail-closed rules

- upstream status must equal `POLICY_CAPACITY_ELIGIBLE`;
- LONG requires stop below entry;
- SHORT requires stop above entry;
- equity, prices, multiplier and quantity step must be finite and positive;
- risk budget must be explicit and within 1..10000 bps;
- a quantity that floors to zero is vetoed.

## Authority boundary

`SIZE_CANDIDATE` is not trade approval.

P15-B does not:
- approve leverage or margin;
- enforce asset/strategy limits;
- perform portfolio/correlation checks;
- create broker/exchange orders;
- bypass P16.

Production numeric defaults: **NONE**.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.
