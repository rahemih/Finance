# P16-B — Duplicate / Idempotency Precheck

State: IMPLEMENTATION_ACTIVE  
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
