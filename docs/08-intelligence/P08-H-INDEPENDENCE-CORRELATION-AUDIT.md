# P08-H — Independence / Correlation Audit

Task: `FIN-P08-WH-001`  
Linear: `HOS-223`  
Lock: RELEASED  
State: CANONICAL_COMPLETE

## Objective

Prevent correlated technical transforms from being counted as independent confirmations before P08-I/G6.

The audit uses conservative **correlation clusters** plus deterministic dependence measurements. It does not convert a raw correlation coefficient into an independence verdict with an arbitrary cutoff.

## Canonical cluster policy

Directional technical families are grouped by known construction/lineage overlap:

- `TREND` + `REGIME` → `directional-trend-regime`
- `MOMENTUM` → `return-momentum`
- `MARKET_STRUCTURE` + `PRICE_ACTION` + `BREAKOUT` → `price-structure-breakout`
- `MEAN_REVERSION` → `mean-reversion`
- `VOLATILITY` → `range-volatility-context` and is context-only

A correlation cluster contributes at most one directional confirmation.

This does **not** claim that separate clusters are statistically independent in all markets or regimes. Separate clusters remain under empirical dependence monitoring.

## Direct/structural relationships

The policy explicitly records known relationships:

- REGIME is derived from multi-timeframe TREND, so TREND + REGIME cannot become two independent votes.
- MARKET_STRUCTURE, PRICE_ACTION and BREAKOUT share local price-path/extrema/candle geometry and are conservatively cluster-capped.
- VOLATILITY and BREAKOUT share range-expansion context, but VOLATILITY is non-directional.

Pairs without a registered direct construction dependency are labeled:

`SEPARATE_CLUSTER_EMPIRICAL_MONITORING_REQUIRED`

rather than `INDEPENDENT`.

## Numeric dependence measurement

P08-H provides deterministic Pearson and Spearman measurements.

Rules:

- numeric dependence is evidence only;
- no universal Pearson/Spearman threshold is hard-coded;
- zero-variance series are reported `UNDEFINED_ZERO_VARIANCE`;
- sample count is recorded;
- production fusion threshold ownership remains P14;
- numeric dependence threshold status remains `TO_BE_CALIBRATED_BY_GOVERNED_EMPIRICAL_EVIDENCE`.

## Fail-closed registry

Every P08 family has an expected canonical `independence_group`.

The audit fails closed if:

- an unknown family appears;
- a family emits a different `independence_group`;
- a context-only family emits directional evidence;
- canonical family policy files drift away from the P08-H registry.

This converts the earlier provisional cross-family statuses into an auditable, conservative cluster model without overstating empirical independence.

## Confirmation counting

Raw supporting family count is not the independent-confirmation count.

For example:

- TREND + REGIME = 2 supporting families, 1 independent cluster;
- MARKET_STRUCTURE + PRICE_ACTION + BREAKOUT = 3 supporting families, 1 independent cluster.

Multiple timeframes of the same Trend method were already collapsed by P08-G and remain related evidence.

## Boundary

P08-H does not:

- choose the minimum number of confirmations required for a production signal;
- choose fusion weights;
- calibrate probability;
- pass G6;
- certify profitability;
- approve Risk;
- send broker/exchange orders.

P08-I owns the technical validation gate. P14 owns fusion thresholds and calibrated probability.

## Safety

- Live Trading: DISABLED
- Auto Trading: DISABLED
- Direct trade/order output: FORBIDDEN
- Country assumption: NONE
- Network/credentials: NONE REQUIRED


## Canonical closure evidence

- Implementation PR: `#186` = MERGED
- Final implementation head: `a2d23b354b17a48a26f6abe448a28da8f846cc51`
- Implementation merge SHA: `62651b2fb351d67545e5d7037d3fb97c9f72aea7`
- PR Governance: `38044760144` = SUCCESS
- PR artifact: `sha256:6f994629520a41e435a2fd4865616185497e43ea25454993c94ec39c712512a5`
- Post-merge Governance: `38044866029` = SUCCESS
- Post-merge artifact: `sha256:4de59f90922b3c000af83f046a7c11540eebdacd0eb6446aa6eef4be879a7c23`
- Post-merge Branch Hygiene: `38044866002` = SUCCESS
- Strict Pyright: PASS after bounded R01 typing repair
- P08 technical-intelligence tests: PASS
- deterministic P08-H audit evidence twice: PASS
- canonical family-policy independence groups match registry: PASS
- cluster cap = one independent vote per known correlation cluster
- numeric Pearson/Spearman remains MEASURED_NOT_THRESHOLD_CLASSIFIED
- production fusion threshold owner remains P14

P08-I — Technical Validation Gate is READY_NOT_STARTED. AR-1 remains READY_NOT_STARTED under separate cross-cutting ownership.
