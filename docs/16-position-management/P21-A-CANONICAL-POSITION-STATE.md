# P21-A — Canonical Position State

Task: `FIN-P21-WA-001`  
Phase: P21 — Position Management  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P21-WA-001-01`  
Dependency: P20 CANONICAL_COMPLETE / G11_EXECUTION_VALIDATED PASS

## Objective

Establish a deterministic canonical position-state representation for Crypto and Forex from explicit execution evidence.

P21-A owns state representation and derivation only. It does not decide when to place TP/SL, partially close, move to break-even, trail, or trigger an emergency exit.

## Canonical state

Each position carries:
- position / portfolio / strategy / asset identity;
- market = CRYPTO or FOREX;
- side = LONG or SHORT;
- fixed-point quantity and price scales;
- upstream risk-validation and pre-trade-firewall identity;
- exact OMS-record and reconciliation-report lineage for every accepted fill.

States:
- `OPEN`;
- `PARTIALLY_CLOSED`;
- `CLOSED`.

Fill events:
- `OPEN_FILL`;
- `ADD_FILL`;
- `REDUCE_FILL`.

Scale-in is allowed only before the first reduction. A closed position cannot be reopened under the same position identity.

## Fail-closed invariants

The engine rejects:
- unknown positions;
- invalid market/side taxonomy;
- malformed risk/firewall/OMS/reconciliation hashes;
- a first event other than sequence-1 OPEN_FILL;
- sequence gaps;
- event-time regression;
- duplicate OMS fill lineage;
- over-close;
- scale-in after reduction;
- reopen after CLOSED.

## Cost-basis representation

P21-A stores exact integer state:
- total opened quantity;
- total closed quantity;
- currently open quantity;
- accumulated entry price × quantity product;
- average-entry floor and exact remainder.

No floating-point accounting is used.

## Authority boundary

P21-A:
- performs no broker/exchange query;
- uses no credentials;
- performs no network I/O;
- submits or mutates no external order;
- performs no automatic OMS mutation;
- grants no Live execution authority.

TP/SL and all exit decisioning remain owned by later P21 workstreams.

`LIVE_TRADING = DISABLED`  
`AUTO_TRADING = DISABLED`

P22 remains NOT_STARTED.
