# P09-G — Forex Proxy Coverage Confidence

Task: `FIN-P09-WG-001`  
Linear: `HOS-231`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P09-WG-001-01` / ACQUIRED  
Lead: A2 Data  
Support: A0, A1, A3, A4, A6, A8, A9, A10

## Objective

Make spot-FX proxy confidence auditable without turning incomplete proxy evidence into a fictitious percentage of the global FX market.

## Input boundary

P09-G accepts only P09-A `VolumeObservation` values that:

- are `FOREX_SPOT`;
- use an explicit allowed proxy kind;
- name provider and venue;
- retain provider-specific coverage scope;
- state the proxied concept;
- pass P09-A point-in-time and provenance rules;
- do not claim GLOBAL, CONSOLIDATED or TOTAL_MARKET coverage.

## Confidence components

The assessment carries the source-declared `coverage_confidence_bps` and requires evidence-backed component confidences for:

- provider scope;
- internal completeness within that provider scope;
- freshness.

An independent benchmark-agreement confidence can optionally be supplied. If a future policy requires it, absence fails closed.

Every component has an associated evidence SHA-256 digest.

## Aggregation

P09-G does not use arbitrary weights.

`validated_proxy_coverage_confidence_bps = min(declared, provider_scope, completeness, freshness[, benchmark])`

This conservative minimum means a weak required evidence component cannot be hidden by stronger unrelated components.

## Critical semantic boundary

The result is:

**confidence in the stated provider/proxy coverage evidence**

It is **not**:

- percentage share of global FX turnover;
- consolidated FX market coverage;
- a universal liquidity score;
- trade-success probability.

No `global_market_share_bps` field exists in the contract.

## Safety

- global FX market-share claim: FORBIDDEN without a separate verified denominator contract;
- cross-provider aggregation: FORBIDDEN;
- weighted confidence scoring: FORBIDDEN;
- production FX/order-flow vendor: NOT_SELECTED;
- country assumption: NONE;
- LIVE_TRADING: DISABLED;
- AUTO_TRADING: DISABLED;
- recommendation/probability/Risk/execution authority: FORBIDDEN.
