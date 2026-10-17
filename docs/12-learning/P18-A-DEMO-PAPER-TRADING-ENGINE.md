# P18-A — Demo / Paper Trading Engine

State: IN_PROGRESS  
Task: `FIN-P18-WA-001`  
Phase: P18 — Continuous Demo Learning

## Objective

Provide the deterministic Demo / Paper execution core for the permanent learning loop without creating any broker/exchange routing or live-trading authority.

## Inputs and identity

P18-A consumes point-in-time market observations plus immutable strategy/model identities. Each Demo session binds:

- session identity;
- Strategy Registry identity/version;
- Model Registry identity/version;
- initial paper capital and base currency;
- deterministic strategy and simulator checkpoint identities.

Market observations carry explicit event time, availability time, canonical asset identity, price scale and evidence SHA-256.

## Deterministic engine

The engine enforces:

- strictly increasing event sequence;
- non-decreasing event time;
- no future information availability;
- stable per-asset price scale;
- unique decision and fill identities;
- no unknown fills;
- no overfills or opposite-direction fills;
- no overlapping unresolved decision for the same asset;
- deterministic multi-asset cash/position/equity accounting;
- content-addressed state and step-record identities;
- deterministic state snapshot/restore when strategy and simulator checkpoints match.

## Authority boundary

P18-A is **Demo/Paper only**.

It does not:

- connect to a broker or exchange;
- create a production order;
- grant execution authority;
- perform training or retraining;
- select Champion/Challenger;
- authorize promotion;
- start P19.

Automatic live promotion is forbidden. `LIVE_TRADING` and `AUTO_TRADING` remain `DISABLED`.

## Downstream contract

P18-A emits auditable Demo decision/fill/state records. P18-B owns the Decision / Outcome Journal and will consume these records after P18-A canonical closure.

## Validation

The governed test/evidence package covers deterministic replay, snapshot/restore identity, future-information rejection, duplicate sequence rejection, unknown fill rejection, overfill rejection, price-scale drift rejection and safety-authority boundaries.
