# P21-F — Broker Reconciliation

Task: `FIN-P21-WF-001`  
Phase: P21 — Position Management  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
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

## Canonical closure evidence

- implementation PR #443 = MERGED;
- implementation head = `2aabccbbe9788ade15eabc75e9c76c619152200f`;
- implementation Governance = `40196553749` / SUCCESS;
- implementation artifact = `12600086746` / `sha256:8900dbe2f8a5e4dea4e4f4ba3ac180bfb99cf3f28887307e19da8a0abacaec9d`;
- deterministic P21-F evidence SHA256 = `d031f7b4eca20492004ac8947a1790c00fc07da81389f7bdf1e7e05a2d984b21`;
- implementation merge SHA = `913e7b1f27b749c9ccc579928d17cdc1133ab049`;
- post-merge Governance = `40196723629` / SUCCESS;
- post-merge artifact = `12600456815` / `sha256:1b7e199e62708a0e3f242bcf1b0eddcf109d46788eeab7a690fee4e44df3e5e0`;
- post-merge Branch Hygiene = `40196723657` / SUCCESS;
- lock = RELEASED.

## Next workstream boundary

P21-G — Restart Recovery = READY_NOT_STARTED.  
P21-H = NOT_STARTED.  
P22 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

P21-F completion certifies deterministic reference/sandbox position-level reconciliation and fail-closed mismatch handling. It does not query or mutate a real venue, repair positions automatically, or authorize Live trading.
