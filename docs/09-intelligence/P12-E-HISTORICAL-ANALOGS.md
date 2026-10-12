# P12-E — Historical Analogs

Task: `FIN-P12-WE-001`  
Linear: `HOS-256`  
State: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P12-WE-001-01` / RELEASED  
Canonical base: `1614a47ce81f92cf5cb09e9af46a4ee4a815937a`

## Objective

Retrieve deterministic historical market-memory states that resemble a current state while preventing future-outcome leakage and probability overstatement.

## Contract

- versioned feature-state with timestamp, regime, provenance and source dataset versions;
- signed-bps feature ontology: TREND / MOMENTUM / VOLATILITY / LIQUIDITY / ORDER_FLOW / MACRO / NEWS / CAPITAL_FLOW;
- candidate must be strictly earlier than the query state;
- exact regime match is required;
- minimum shared-feature coverage is required;
- similarity is normalized integer basis points with explicit coverage and uncertainty;
- top-K ranking is deterministic and input-order independent;
- no future outcome is consumed by matching.

## Safety

Similarity is descriptive historical-memory evidence. It is not empirical probability, forecast certainty, risk approval or execution authority. LIVE_TRADING and AUTO_TRADING remain DISABLED.


## Canonical closure evidence
- implementation PR #254 = MERGED
- final implementation head `bf2ad0f03283206c4a25151c7fe88de9f940a882`
- implementation Governance `38220874496` = SUCCESS
- implementation artifact `sha256:2b7b6d7a74f2af503c39a770e0f84a4c0db3d0dd4eb779b7759afac8a58cf39e`
- implementation merge SHA `e6a3550ca05363dd15ccba79a4ceffa7ca2d535b`
- post-merge Governance `38221033638` = SUCCESS
- post-merge Branch Hygiene `38221033679` = SUCCESS
- P12-F = READY_NOT_STARTED
