# P09-F — Funding / OI / Liquidation / Crowding

Task: `FIN-P09-WF-001`  
Linear: `HOS-230`  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
Lead: A3 Market Intelligence  
Support: A0, A1, A2, A4, A6, A8, A9, A10

## Objective

Create provider-scoped, point-in-time derivatives evidence for funding, Open Interest and long/short liquidations, then combine it into a complete **crowding evidence vector** without inventing an unvalidated trading score.

## Observation taxonomy

- `FUNDING_RATE`
- `OPEN_INTEREST`
- `LONG_LIQUIDATION`
- `SHORT_LIQUIDATION`

Every observation carries symbol, derivatives market class, provider, venue, explicit value unit, event/as-of time, sequence, coverage scope and trusted provenance.

## Funding

Funding rate uses the explicit unit `DECIMAL_RATE` and requires `funding_interval_seconds`.

The interval is part of the observation semantics; rates with different intervals must not be silently treated as equivalent.

Funding is currently allowed only for governed `CRYPTO_DERIVATIVE` observations in this reference contract.

## Open Interest

Open Interest must be non-negative and carries a provider-defined explicit unit, for example contracts or notional.

P09-F does not silently convert between OI units.

## Liquidations

Long and short liquidation values must be non-negative.

For crowding evidence, long and short liquidation observations must use the same unit.

If total liquidation activity is positive:

`liquidation_imbalance_bps = (long_liquidation - short_liquidation) / total_liquidation * 10000`

The value is bounded to `[-10000, 10000]`.

If total liquidation is zero, imbalance is **unavailable/null**, not zero-direction evidence.

## Crowding evidence vector

A complete vector requires exactly one of each metric kind and requires the same:

- symbol;
- market class;
- provider;
- venue;
- coverage scope;
- as-of time.

The output retains Funding, OI, liquidation totals and liquidation imbalance as evidence components.

P09-F intentionally does **not** emit:

- crowding score;
- crowded/uncrowded label;
- trade direction;
- success probability;
- liquidation forecast.

Those would require empirical validation and belong no earlier than P09-H and later signal/risk phases.

## Market scope

Reference metrics are derivatives-only. Spot FX is not assigned synthetic Funding, OI or liquidation observations.

Cross-provider aggregation is forbidden in P09-F.

## Safety

- production derivatives/order-flow vendor: NOT_SELECTED;
- country assumption: NONE;
- LIVE_TRADING: DISABLED;
- AUTO_TRADING: DISABLED;
- recommendation/probability/Risk/execution authority: FORBIDDEN.


## Canonical closure evidence

- Implementation PR: `#200` = MERGED
- Final implementation head: `b8727d3515ea4d876beb78ab765487ec3c2fedfb`
- Implementation merge SHA: `a3d1d1e64061503bd5b9db2ba0eb30159547459d`
- PR Governance: `38051316245` = SUCCESS
- PR artifact: `sha256:5d7813bb88ca03687a56461dcea2f352d4d73c737693c0cb2c9d6bebb388bd43`
- Post-merge Governance: `38051391835` = SUCCESS
- Post-merge artifact: `sha256:4bcca8f987bd9f1f57f09055623edbfefbeafeee849c3fa9ebfaa0a249a792b9`
- Post-merge Branch Hygiene: `38051391827` = SUCCESS
- strict typecheck / P09 tests / deterministic P09-F evidence: PASS
- supply-chain and reproducibility controls: PASS

P09-G — Forex Proxy Coverage Confidence becomes `READY_NOT_STARTED`.
