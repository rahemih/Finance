# P08-E — Volatility & Mean Reversion

Task: `FIN-P08-WE-001`  
Linear: `HOS-216`  
Lock: RELEASED  
State: CANONICAL_COMPLETE

## Objective

Implement deterministic point-in-time Volatility context and Mean Reversion directional evidence on the canonical P08 technical-intelligence foundation.

## Volatility

The reference model compares normalized candle range over a short window with the governed baseline window.

VOLATILITY is deliberately emitted with `direction = 0`. Volatility expansion or compression is market context, not bullish/bearish price direction. Therefore it cannot inflate directional confirmation counts.

Correlated range-volatility transforms belong to the single `range-volatility` independence group.

## Mean Reversion

The reference model computes:

1. rolling arithmetic mean of close prices;
2. mean absolute deviation (MAD);
3. latest price deviation from the mean expressed in MAD basis points.

A sufficiently high above-mean extreme emits bearish mean-reversion direction; a sufficiently low below-mean extreme emits bullish mean-reversion direction; otherwise the family is neutral.

Correlated deviation/mean transforms belong to `price-deviation-mean-reversion`.

## Independence boundary

VOLATILITY and MEAN_REVERSION use separate provisional groups, but cross-family independence remains `PROVISIONAL_PENDING_P08_H` until the formal P08-H audit.

## Score semantics

Strength and confidence are deterministic technical-evidence scores, not empirical win probability, signal probability, trade recommendation or risk approval.

## Safety

- Direct trade/order output: FORBIDDEN
- Live Trading: DISABLED
- Auto Trading: DISABLED
- Country assumption: NONE
- Network/credentials required: NO

## Boundary

P08-F and later workstreams remain out of scope. G6 is not evaluated here.


## Canonical closure evidence

- Implementation PR: `#176` = MERGED
- Final implementation head: `a3d64bce941fd56b54e97c1897920085e0a8b42d`
- Implementation merge SHA: `e772201368555bb87bf08966e0fa637ba363c371`
- PR Governance: `38040208295` = SUCCESS
- PR artifact: `sha256:85ec6501fedd2361b9ca277182cd0733c5a5fc239695102f2a4a941fb3a49d07`
- Post-merge Governance: `38040279995` = SUCCESS
- Post-merge artifact: `sha256:49726f19401d060694b2fff6a187075577d50546a14d650ec45253a8138192c2`
- Post-merge Branch Hygiene: `38040279969` = SUCCESS
- Strict Pyright: PASS
- P08 technical-intelligence tests: PASS
- Deterministic P08-E evidence: PASS
- Volatility direction remains context-neutral zero only
- Cross-family independence remains PROVISIONAL_PENDING_P08_H

P08-F — Breakout / Expansion is READY_NOT_STARTED. G6 remains NOT_EVALUATED.
