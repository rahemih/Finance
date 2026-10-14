# P16-A — Signal Age / Price-Deviation Check

State: CANONICAL_COMPLETE  
Task: `FIN-P16-WA-001`  
Linear: `NEXUS QUANT — Management Control & Reporting Register-1`

## Objective

Provide the first independent fail-closed barrier in P16 immediately before later pre-trade checks.

P16-A accepts only canonical directional P14-H signals (`LONG` / `SHORT`) and verifies:

- signal age against an explicit governed maximum age;
- current price displacement from the canonical signal entry zone against an explicit governed maximum deviation.

## Price deviation

If current price is inside the signal entry zone, deviation is `0 bps`.

If current price is outside the zone, deviation is measured against the nearest entry-zone boundary and rounded upward to whole basis points so the firewall never understates displacement.

## Fail-closed rules

- WAIT / NO_TRADE cannot enter the pre-trade approval path;
- directional geometry must be complete;
- future-dated signals are vetoed;
- current-price scale must match the signal price scale;
- signal age above the explicit threshold is vetoed;
- price deviation above the explicit threshold is vetoed.

Production thresholds: **NONE / explicit governed policy required**.

## Authority boundary

A positive P16-A result is `PRETRADE_A_ELIGIBLE`.

It is **not**:
- `G8_PRETRADE_SAFE`;
- final pre-trade approval;
- an execution order;
- broker/exchange routing permission.

P16-B..P16-H remain later workstreams.

LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #323 = MERGED;
- implementation head = `0403c1ce119df04ec185c1f61842bf6be62a3309`;
- Governance `38562758587` = SUCCESS;
- artifact = `sha256:404e4fb6b350153593a905b8d9cc7209e5534c96c0b01b64efb692023a0ee5a4`;
- implementation merge = `20a3dba64bc1da6647e91e7637fb0eb162337b79`;
- `FIN-P16-WA-001` = CANONICAL_COMPLETE;
- `LOCK-FIN-P16-WA-001-01` = RELEASED;
- P16-B = READY_NOT_STARTED;
- P16-C..P16-H = NOT_STARTED;
- `G8_PRETRADE_SAFE` = NOT_REACHED;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.
