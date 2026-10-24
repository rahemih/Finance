# P20-I — Broker / Exchange Simulation + G11

Task: `FIN-P20-WI-001`  
Phase: P20 — Execution & Order Management  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P20-WI-001-01`  
Dependency: P20-A..P20-H CANONICAL_COMPLETE

## Objective

Validate the complete P20 execution-control chain with deterministic reference broker/exchange simulation and produce the G11 execution-validation gate.

G11 in P20-I is explicitly scoped to:

`REFERENCE_SIMULATION_EXECUTION_VALIDATION`

It is not production broker certification and is not Live execution validation.

## Required simulation matrix

For both CRYPTO and FOREX:
- ACK + complete fill;
- reject;
- partial fill + cancel;
- pre-dispatch timeout with safe retry;
- post-dispatch crash ambiguity with reconciliation hold;
- exact duplicate replay;
- reconciliation mismatch with fail-closed control.

Every required market/scenario pair must be present and must resolve to its deterministic expected control outcome.

## Gate inputs

G11 requires:
- P20-A..P20-H manifests = CANONICAL_COMPLETE;
- safety posture on every dependency: network DISABLED, Live authority false, Live/Auto disabled;
- complete deterministic scenario matrix;
- P20-H quality band = WITHIN_REFERENCE_BUDGET;
- P20-H authority remains reference-only with G11 still false at input.

## Gate semantics

A PASS means the deterministic reference/simulation execution controls are validated across P20-A..P20-H.

A PASS does **not** mean:
- a production broker/exchange was selected or certified;
- real venue latency/slippage was observed;
- credentials/KYC/funding exist;
- external orders may be sent;
- Live execution is validated or authorized;
- profitability is established.

## Safety boundary

- production broker selection = NOT_SELECTED;
- production broker certification = false;
- real venue query = false;
- credentials/account/KYC/funding = NONE;
- network mode = DISABLED;
- external order submission/mutation = false;
- automatic OMS mutation = false;
- Live execution validated = false;
- Live execution authority = false;
- automatic Live promotion = false;
- P21 = NOT_STARTED;
- LIVE_TRADING/AUTO_TRADING = DISABLED.
