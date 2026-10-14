# P16-B — Duplicate / Idempotency Precheck

State: CANONICAL_COMPLETE  
Task: `FIN-P16-WB-001`

## Objective

Reject duplicate or ambiguous pre-trade intents before later firewall checks.

P16-B evaluates:
- exact idempotency-key replay;
- reuse of one key for another intent fingerprint;
- duplicate intent fingerprint submitted under another key.

The replay lookback is an explicit governed input. There is no production default.

## Fail-closed semantics

Within the governed replay window:
- same key + same fingerprint → `DUPLICATE_IDEMPOTENCY_KEY`;
- same key + different fingerprint → `IDEMPOTENCY_KEY_COLLISION`;
- different key + same fingerprint → `DUPLICATE_INTENT_FINGERPRINT`.

Future-dated prior-admission records are invalid and veto the request.

P16-A VETO is non-bypassable.

## Boundary

A positive result is `PRETRADE_B_ELIGIBLE` only.

P16-B does not provide durable storage, distributed locking, final G8 approval, order routing or execution.

P16-C..P16-H remain later workstreams.  
`G8_PRETRADE_SAFE` = NOT_REACHED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #325 = MERGED;
- implementation head = `6e9cca8463f2ac447128e1206add2ced4d04c099`;
- Governance `38567176911` = SUCCESS;
- artifact = `sha256:430c0d88691e1f8d6f47d35a1cbeff2f7363c05261ee642bf11b7e90245b9d9f`;
- implementation merge = `fe36f4d033f3bf5f9ca679c48565250c75248efd`;
- `FIN-P16-WB-001` = CANONICAL_COMPLETE;
- `LOCK-FIN-P16-WB-001-01` = RELEASED;
- P16-C = READY_NOT_STARTED;
- P16-D..P16-H = NOT_STARTED;
- `G8_PRETRADE_SAFE` = NOT_REACHED.
