# P08-H — Independence / Correlation Audit

Task: `FIN-P08-WH-001`  
Linear: `HOS-223`  
Lock: `LOCK-FIN-P08-WH-001-01`  
State: IMPLEMENTATION_ACTIVE

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
