# P21-F — Broker Reconciliation

Task: `FIN-P21-WF-001`  
Phase: P21 — Position Management  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P21-WF-001-01` / ACTIVE  
Dependency: P21-A through P21-E CANONICAL_COMPLETE / RELEASED; P20-G CANONICAL_COMPLETE

## Objective

Reconcile the exact current canonical P21-A position against an explicit normalized reference/sandbox broker-position observation.

P21-F is position-level reconciliation. It does not replace or repeat P20-G order-level reconciliation.

## Observation contract

No venue is queried. The caller supplies a normalized observation already expressed in canonical fixed-point scales and binds it to the exact current `position_record_id`.

Supported external statuses:
- `OPEN`;
- `NOT_FOUND`.

The observation timestamp must not predate the current canonical record.

## Exact comparison

There is no hidden tolerance. P21-F compares:
- position identity;
- asset and market;
- quantity and price scales;
- side;
- open quantity;
- canonical average-entry floor.

A one-unit fixed-point difference is a mismatch.

## Verdicts

- `MATCHED`;
- `MISSING_EXTERNAL_POSITION`;
- `EXTERNAL_EXPOSURE_CONFLICT`;
- `IDENTITY_MISMATCH`;
- `SIDE_MISMATCH`;
- `QUANTITY_MISMATCH`;
- `ENTRY_PRICE_MISMATCH`;
- `MULTIPLE_MISMATCH`.

For every non-MATCHED verdict:
- `safe_hold_required = true`;
- `new_entry_block_required = true`;
- action = `MANUAL_GOVERNED_RECONCILIATION_REQUIRED`.

No mismatch is auto-repaired or auto-flattened.

## Authority boundary

P21-F performs no real broker/exchange query, uses no credentials/network, places or mutates no external order, mutates no OMS or canonical P21-A state, and grants no Live authority.

P21-G..P21-H = NOT_STARTED.  
P22 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.
