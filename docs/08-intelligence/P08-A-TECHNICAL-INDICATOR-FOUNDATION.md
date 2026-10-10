# P08-A — Technical Feature / Indicator Foundation

Task: `FIN-P08-WA-001`  
Linear: `HOS-211`  
Lock: RELEASED  
State: CANONICAL_COMPLETE

## Objective

Establish the deterministic, provider-neutral technical-intelligence foundation used by all later P08 evidence families.

## Contract

P08-A introduces:

- point-in-time trusted OHLCV bars with explicit dataset and data-quality lineage;
- content-addressed indicator definitions;
- required `family` and `independence_group` metadata;
- a common `TechnicalEvidence` object carrying direction, strength, confidence, freshness, timeframe and invalidation metadata;
- deterministic reference SMA and rate-of-change primitives;
- confirmation counting that deduplicates correlated transforms by independence group.

## Independence rule

Two transforms that describe the same underlying market property do not become two independent confirmations merely because their formulas differ. Every later P08 model must declare an independence group and P08-H will perform the formal correlation/independence audit.

## Point-in-time rule

No technical primitive may consume a bar whose event time is after the governed as-of time. Bar windows must be strictly time-ordered and use a single symbol/timeframe.

## Safety boundary

Technical evidence is not a trade instruction. The P08-A contract contains no order, quantity, leverage, broker or exchange authority. Later signal, risk, liquidity, event, execution and portfolio gates remain mandatory.

- Live Trading: DISABLED
- Auto Trading: DISABLED
- Country assumption: NONE
- Production technical-intelligence vendor: NOT_SELECTED
- Network/credentials required by reference implementation: NO

## Workstream boundary

P08-A does not implement trend, momentum, structure/price-action, volatility/mean-reversion, breakout, multi-timeframe/regime models, the independence audit or G6. Those remain P08-B through P08-I.


## Canonical closure evidence

- Implementation PR: `#168` = MERGED
- Final implementation head: `ec72a1d036c73ff76b19599e6edbc75ef801d639`
- Implementation merge SHA: `4c5376b0c689d1ab2ac4424693bb8ca207a0e46b`
- PR Governance: `38034664318` = SUCCESS
- PR artifact: `sha256:ca84b61cf63602141dec2b896b66e03da8846e2573ce3b7419d29e26cd29e452`
- Post-merge Governance: `38034980053` = SUCCESS
- Post-merge artifact: `sha256:96fc0508547e88c06de2db2b21ba0692ca0197d7b0186205d4b9245ac5bc4f5d`
- Post-merge Branch Hygiene: `38034980040` = SUCCESS
- Strict Pyright: PASS
- P08-A tests: 14/14 PASS
- Deterministic P08-A evidence: PASS

P08-B — Trend Family is READY_NOT_STARTED. G6 remains NOT_EVALUATED.
