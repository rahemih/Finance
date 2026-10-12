# P12-E — Historical Analogs

Task: `FIN-P12-WE-001`  
Linear: `HOS-256`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P12-WE-001-01` / ACQUIRED  
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
