# P19-E — Digital Twin Fill / Slippage Model

Task: `FIN-P19-WE-001`  
Phase: P19 — Shadow / Replay / Digital Twin  
State: IN_PROGRESS  
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
