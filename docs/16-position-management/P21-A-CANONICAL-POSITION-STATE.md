# P21-A — Canonical Position State

Task: `FIN-P21-WA-001`  
Phase: P21 — Position Management  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
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


## Canonical closure evidence

- implementation PR #432 = MERGED;
- implementation head = `0c90764e4f754564f142380b46e3d115539eee9d`;
- implementation Governance = `40101908747` / SUCCESS;
- implementation artifact = `12562498846` / `sha256:0240896ed1fe4cf367e03419e4dc14e3d3151640d36a8a9a61d656d38c9090c7`;
- deterministic evidence SHA256 = `f1c821e6c6deaf1f25516a2856cc4e51b43aaa89aa143d87f2c1137efa544754`;
- canonical snapshot ID = `ad3e0d00faff882ecb5b70c6da633544408b2ddcd059fc535c12e2e7788e37e7`;
- implementation merge SHA = `946639c5749c2e4dc00c498628cfba4d77f9d2ee`;
- implementation post-merge Governance = `40102104074` / SUCCESS;
- implementation post-merge Branch Hygiene = `40102104134` / SUCCESS;
- Current State reconciliation PR #433 = MERGED;
- reconciliation merge SHA = `c525e067493a5ccb822010b1d01ad591fc623e1d`;
- reconciliation Governance = `40102204861` / SUCCESS;
- reconciliation post-merge Governance = `40102364025` / SUCCESS;
- reconciliation post-merge Branch Hygiene = `40102364122` / SUCCESS;
- lock = RELEASED.

## Next workstream boundary

P21-B — TP / SL = READY_NOT_STARTED.

P21-C..P21-H = NOT_STARTED.  
P22 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

P21-A completion certifies deterministic canonical position-state derivation from reference execution evidence only. It does not authorize broker access, order submission, TP/SL automation, Live execution, production readiness or profitability claims.
