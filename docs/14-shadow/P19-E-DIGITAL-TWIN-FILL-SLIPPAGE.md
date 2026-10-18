# P19-E — Digital Twin Fill / Slippage Model

Task: `FIN-P19-WE-001`  
Phase: P19 — Shadow / Replay / Digital Twin  
State: CANONICAL_COMPLETE  
Dependencies: P19-A..P19-D CANONICAL_COMPLETE; P17-B CANONICAL_COMPLETE

## Objective

Measure deterministic modeled fill, slippage, fees, latency and partial-fill behavior for a shadow decision without creating a second execution-realism implementation.

P19-E delegates all fill mechanics to the canonical P17-B `HistoricalExecutionSimulator`.

## Lineage

Every Digital Twin request binds:
- P19-D incident replay root;
- P19-C decision replay session;
- P19-A shadow record;
- asset, decision time, requested quantity and reference price;
- context-quality classification;
- source evidence hash.

Changing incident/decision/shadow lineage changes the request and result identities.

## Context quality

Two context classes are governed:
- `EXPLICIT_HISTORICAL_DEPTH`;
- `DERIVED_REFERENCE_DEPTH`.

The canonical CI reference uses `DERIVED_REFERENCE_DEPTH`: a deterministic close-centered synthetic book derived from the latest P19-B-visible public BTC-USD close.

This reference is useful for deterministic wiring and regression validation only. It is **not broker truth**, **not production depth**, and **cannot certify production fill accuracy**.

## P17-B ownership

P17-B remains the sole owner of:
- latency eligibility;
- visible-depth participation;
- partial-fill behavior;
- VWAP fill price;
- taker fee;
- execution diagnostics.

P19-E aggregates those outputs into a content-addressed Digital Twin result and adds slippage relative to the governed reference price.

## Output

The result records:
- FULL_FILL / PARTIAL_FILL / NO_FILL;
- BUY / SELL side;
- requested, filled and remaining quantity;
- VWAP price;
- adverse slippage bps;
- total fee;
- fill/context/diagnostic identities;
- context quality and production-claim guards.

## Safety

Production fill-accuracy claim: false.  
Broker truth: false.  
Decision authority: false.  
Fill authority: false.  
Execution authority: false.  
Order-routing authority: false.  
Broker/exchange routing: false.  
P20: NOT_STARTED.  
LIVE_TRADING: DISABLED.  
AUTO_TRADING: DISABLED.


## Canonical closure evidence

- Implementation PR: #400 / MERGED.
- Implementation head: `e1e8ff4719002ef8aea77b7205e2b68c0d63db73`.
- PR Governance: `39115046346` / SUCCESS.
- PR artifact: `12131644157` / `sha256:7342827fee43a5c912cdff65d3af27cfd6641df503dc6e450e962fa35f69562c`.
- Merge SHA: `85495db998a5937d269824221fe6d60115b8b594`.
- Post-merge Governance: `39115194869` / SUCCESS.
- Post-merge artifact: `12131792625` / `sha256:5ba0097fb72a3fc2e7f4c418b21c920dc976c70a131b5c744b9dde632c31d51e`.
- Post-merge Branch Hygiene: `39115194680` / SUCCESS.
- Lock: RELEASED.
- Next workstream: P19-F / READY_NOT_STARTED.

The canonical CI Digital Twin remains a deterministic reference model over derived depth. It does not establish production fill accuracy or broker truth.
