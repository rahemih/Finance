# P20-I — Broker / Exchange Simulation + G11

Task: `FIN-P20-WI-001`  
Phase: P20 — Execution & Order Management  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
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


## Canonical closure evidence

- implementation PR #427 = MERGED;
- implementation head = `1b7671295677490644da8b19878e57e82428699d`;
- implementation Governance = `40088637944` / SUCCESS;
- implementation artifact = `12558048192` / `sha256:ad89d2c43d6a11fd3a6fc24edc47e9fe6de0997fedf5454f6a2e6415f4303c2f`;
- implementation G11 evidence SHA256 = `46e5ec038f20be4d6faf5d617ab09a1480491dec15a35936cf6af41ea6b1c669`;
- merge SHA = `038da4cc1b491b8968972f8bdb1c32ced8c82421`;
- post-merge Governance = `40088788172` / SUCCESS;
- post-merge artifact = `12557703089` / `sha256:71e03a9c1db0f9507e2058e771e876e827c410f0d91e4ea363604698086075e2`;
- post-merge G11 evidence SHA256 = `46e5ec038f20be4d6faf5d617ab09a1480491dec15a35936cf6af41ea6b1c669`;
- post-merge Branch Hygiene = `40088788168` / SUCCESS;
- G11 = PASS;
- G11 gate ID = `8f7c529945c86ef64b55107d16c5969814b23e5ba27daaf4258d7cf56f1738ad`;
- lock = RELEASED.

The first P20-I validation attempt correctly failed closed on the P20-H degraded fill-band defect. That defect was fixed under `FIN-P20-WH-001-R01` / PR #428 and canonically closed by PR #429 before P20-I was rerun. No hard quality threshold or G11 requirement was relaxed.

## Phase boundary after G11

G11 PASS is limited to `REFERENCE_SIMULATION_EXECUTION_VALIDATION`.

It does not certify production broker/exchange behavior or Live execution. P21 remains `NOT_STARTED / OWNER_PHASE_AUTHORIZATION_REQUIRED`; LIVE_TRADING and AUTO_TRADING remain DISABLED.
