# P16-D — Spread / Liquidity / Capacity Check

State: CANONICAL_COMPLETE  
Task: `FIN-P16-WD-001`

## Objective

Revalidate execution-time market microstructure before later pre-trade checks using canonical P09-D order-book metrics and P09-E displayed-liquidity heatmap.

## Rules

- P16-C VETO is non-bypassable;
- order-book metrics and heatmap must refer to the same source snapshot;
- spread must remain within an explicit governed maximum;
- the policy names an explicit liquidity distance band;
- LONG uses cumulative displayed ask notional;
- SHORT uses cumulative displayed bid notional;
- requested notional / displayed capacity is rounded upward to basis points;
- capacity utilization must remain within an explicit governed maximum.

## Liquidity boundary

This is **displayed capacity only**.

P16-D does not infer hidden liquidity and makes no fillability, fill-probability, slippage or market-impact claim.

## Authority boundary

A positive result is `PRETRADE_D_ELIGIBLE` only.

P16-E..P16-H remain later workstreams.  
`G8_PRETRADE_SAFE` = NOT_REACHED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #329 = MERGED;
- implementation head = `507014aa90e18c3b59d3119d8363f2e95729de4c`;
- Governance `38569884213` = SUCCESS;
- artifact = `sha256:0af93022fc3b85ea442dd4c1a0cdc4bfbeaf57f7a2eb11bf02c6ea4b868351e1`;
- implementation merge = `240cb5a71011a9def64a44e54749a8aee7269472`;
- `FIN-P16-WD-001` = CANONICAL_COMPLETE;
- `LOCK-FIN-P16-WD-001-01` = RELEASED;
- P16-E = READY_NOT_STARTED;
- P16-F..P16-H = NOT_STARTED;
- `G8_PRETRADE_SAFE` = NOT_REACHED.
