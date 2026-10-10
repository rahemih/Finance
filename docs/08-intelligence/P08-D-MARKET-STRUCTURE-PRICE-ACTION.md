# P08-D — Market Structure & Price Action

Task: `FIN-P08-WD-001`  
Linear: `HOS-215`  
Lock: RELEASED  
State: CANONICAL_COMPLETE

## Objective

Implement deterministic, point-in-time Market Structure and Price Action family evidence on the canonical P08 technical-intelligence foundation.

## Market Structure

The reference model detects swing highs and lows only after the governed number of right-side confirmation bars are already known. This prevents an unconfirmed right-edge pivot from being treated as historical fact.

Two confirmed swing highs and two confirmed swing lows classify:

- higher high + higher low = bullish structure;
- lower high + lower low = bearish structure;
- mixed or insufficient confirmed swings = neutral.

Break-of-structure is retained as correlated context inside the same `swing-structure` family. It is not a second independent vote.

## Price Action

The completed latest candle is evaluated using:

- body-to-range ratio;
- directional close location within the candle range.

These correlated candle transforms emit one PRICE_ACTION evidence object under `candle-price-action`.

## Independence boundary

MARKET_STRUCTURE and PRICE_ACTION use separate provisional independence groups, but **cross-family independence is not certified in P08-D**. Its status remains `PROVISIONAL_PENDING_P08_H` until the formal P08-H correlation/independence audit.

## Score semantics

Strength and confidence are deterministic technical-evidence scores, not empirical win probability, signal probability, trade recommendation or risk approval.

## Safety

- Direct trade/order output: FORBIDDEN
- Live Trading: DISABLED
- Auto Trading: DISABLED
- Country assumption: NONE
- Network/credentials required: NO

## Boundary

P08-E and later workstreams remain out of scope. G6 is not evaluated here.


## Canonical closure evidence

- Implementation PR: `#174` = MERGED
- Final implementation head: `6f5245b1de88f54f8e61bce485732bfa03b3ad3f`
- Implementation merge SHA: `02716ef27cc848613bac096ef7e7442d9bd4bab1`
- PR Governance: `38039440572` = SUCCESS
- PR artifact: `sha256:cdd554a837221dc581c5c3ba679610447f7e39a0c38417e8683cfc2db1521b88`
- Post-merge Governance: `38039518925` = SUCCESS
- Post-merge artifact: `sha256:f4b29a8b94da967d627149863b9a7a1f6e199bf629947a219aff90c57789fca8`
- Post-merge Branch Hygiene: `38039518953` = SUCCESS
- Strict Pyright: PASS
- P08 technical-intelligence tests: PASS
- Deterministic P08-D evidence: PASS
- Cross-family independence status remains `PROVISIONAL_PENDING_P08_H`

P08-E — Volatility & Mean Reversion is READY_NOT_STARTED. G6 remains NOT_EVALUATED.
