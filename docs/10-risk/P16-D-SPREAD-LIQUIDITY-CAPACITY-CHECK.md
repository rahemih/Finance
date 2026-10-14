# P16-D — Spread / Liquidity / Capacity Check

State: IMPLEMENTATION_ACTIVE  
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
