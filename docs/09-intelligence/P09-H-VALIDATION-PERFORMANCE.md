# P09-H — Validation / Performance

Task: `FIN-P09-WH-001`  
Linear: `HOS-232`  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
Lead: A9 Operations / Validation  
Support: A0, A1, A2, A3, A4, A6, A8, A10

## Objective

Certify that the P09-A through P09-G engineering and safety contracts are internally consistent, canonical and reproducible, and establish a measured **offline CI regression budget** for the P09 test suite.

P09-H does not certify strategy profitability, trade success, signal quality, execution quality, production market-data latency or production capacity.

## Integrated validation

The deterministic evaluator consumes exactly seven canonical machine-readable prerequisite documents:

- P09-A — Volume / Proxy Ontology
- P09-B — Trade Flow / Delta / CVD
- P09-C — Volume Profile
- P09-D — Order Book / Spread / Depth / Imbalance
- P09-E — Liquidity Heatmap / Displayed Capacity
- P09-F — Funding / OI / Liquidation / Crowding
- P09-G — Forex Proxy Coverage Confidence

Every prerequisite must be `CANONICAL_COMPLETE`, have lock `RELEASED`, retain canonical implementation/post-merge evidence and preserve the common safety boundary:

- country assumption = NONE;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED;
- direct trade output = forbidden.

The evaluator also re-checks the workstream-specific anti-overstatement invariants so a later documentation/config drift cannot silently weaken P09.

## Performance semantics

P09-H measures the wall-clock duration of the complete offline `tests/p09` unittest suite on GitHub CI.

Policy:

- budget: 60 seconds;
- network: not required;
- semantics: `CI_REGRESSION_BUDGET_NOT_PRODUCTION_SLO`;
- measured evidence is not byte-compared because runner timing/platform details are intentionally empirical;
- deterministic integrated validation evidence is byte-compared across two runs.

Passing this budget means only that the governed P09 reference/test suite has not regressed beyond the CI budget. It does not certify provider latency, streaming throughput, production host capacity, execution latency, slippage or market impact.

## Phase-closure boundary

A deterministic P09-H PASS during the implementation PR is necessary but not sufficient to declare P09 canonical.

P09 becomes `CANONICAL_COMPLETE` only after:

1. implementation PR Governance PASS;
2. implementation merge;
3. post-merge Governance + Branch Hygiene PASS;
4. closure reconciliation PR merge;
5. closure post-merge verification;
6. HOS-232 Done and lock RELEASED.

After successful P09 closure, P10 remains:

`OWNER_PHASE_AUTHORIZATION_REQUIRED`

P09-H does not authorize P10 execution.

## Safety

- profitability certification: NO;
- trade-success probability certification: NO;
- production execution certification: NO;
- production provider performance certification: NO;
- country assumption: NONE;
- LIVE_TRADING: DISABLED;
- AUTO_TRADING: DISABLED.


## Canonical implementation evidence

- Implementation PR: `#204` = MERGED
- Initial PR Governance: `38053001612` = FAILED at strict Pyright type narrowing
- Repair R01: `df8d170517c7da61ec8a5d40fd1be1cfa01dbf91`
- Final PR Governance: `38053077862` = SUCCESS
- Final PR artifact: `sha256:8326773f5a6842bb85dbfa3e8dc484909c91c538682401bcb6eefe2223858806`
- Implementation merge SHA: `146cb7442ce1d78d824f13220533c75c771d6821`
- Post-merge Governance: `38053926128` = SUCCESS
- Post-merge artifact: `sha256:4bf178523f667c9e46627c599442be16675d990fe62c65272bd684edbda46542`
- Post-merge Branch Hygiene: `38053926101` = SUCCESS
- deterministic integrated P09-H validation: PASS
- measured offline CI regression-performance budget: PASS
- supply-chain and reproducibility controls: PASS

## Phase closure

P09-A through P09-H are `CANONICAL_COMPLETE`.

P09 is `CANONICAL_COMPLETE`.

P10 remains `NOT_STARTED / OWNER_PHASE_AUTHORIZATION_REQUIRED`; this closure does not authorize P10.
