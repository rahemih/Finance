# P09-G — Forex Proxy Coverage Confidence

Task: `FIN-P09-WG-001`  
Linear: `HOS-231`  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
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


## Canonical closure evidence

- Implementation PR: `#202` = MERGED
- Final implementation head: `eb382f2c4a6aec30f0e7d71ed956720d43bcf05d`
- Implementation merge SHA: `0d753b5363988e5fa9f562bcd80b880c9abe2a97`
- PR Governance: `38051885528` = SUCCESS
- PR artifact: `sha256:43ebd98a94936095778ac6184cb6b78c473070ddfcac043dede33dab46c4ef61`
- Post-merge Governance: `38051957164` = SUCCESS
- Post-merge artifact: `sha256:0b1a4be0837d17c557ee5a0c7dd9f1a2479fc4cac711120645bd0eacb637fcb8`
- Post-merge Branch Hygiene: `38051957104` = SUCCESS
- strict typecheck / P09 tests / deterministic P09-G evidence: PASS
- supply-chain and reproducibility controls: PASS

P09-H — Validation / Performance becomes `READY_NOT_STARTED`.
