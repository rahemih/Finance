# P16-G — Fail-Closed / Override Governance

State: CANONICAL_COMPLETE  
Task: `FIN-P16-WG-001`

## Objective

Govern override requests without granting override authority to automation.

Core rule:

**P16-G never converts a safety VETO into pre-trade eligibility.**

## Normal path

When P16-F is `PRETRADE_F_ELIGIBLE` and no override is requested:

`PRETRADE_G_ELIGIBLE`

When P16-F is `VETO` and no override is requested:

`VETO`

## Override request path

A valid override request must contain:
- request ID;
- requester identity;
- supported scope;
- reason;
- evidence SHA-256;
- request timestamp;
- expiry.

The request lifetime must be within an explicit governed maximum TTL.

A structurally valid, unexpired request produces:

`WAITING_FOR_APPROVAL`

It does **not** produce `PRETRADE_G_ELIGIBLE`.

If upstream is already VETO, that veto remains blocking while approval is awaited.

Any approved policy/reset action must occur through its owning governed mechanism, change upstream state, and cause the pre-trade chain to be executed again.

## Authority boundary

P16-G has no:
- approval authority;
- circuit-reset authority;
- risk/leverage ceiling authority;
- emergency-policy mutation authority;
- G8 authority;
- execution authority.

This matches Automation Governance, Owner Gates and Change Control.

P16-H remains the final gate.  
`G8_PRETRADE_SAFE` = NOT_REACHED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #336 = MERGED;
- implementation head = `623f9d93265a6d52e79fa4361200b4d9cd816a99`;
- Governance `38736708270` = SUCCESS;
- artifact = `sha256:57d1297420a78f0e89b6aa34d8d5a67a42c2100bd5328fab2963b2b8bf7fc001`;
- implementation merge = `af3d4e27d0fdf00fed0a889b0fed3a24998bfae8`;
- `FIN-P16-WG-001` = CANONICAL_COMPLETE;
- `LOCK-FIN-P16-WG-001-01` = RELEASED;
- P16-H = READY_NOT_STARTED;
- `G8_PRETRADE_SAFE` = NOT_REACHED.
