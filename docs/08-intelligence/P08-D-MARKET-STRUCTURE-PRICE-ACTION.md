# P08-D — Market Structure & Price Action

Task: `FIN-P08-WD-001`  
Linear: `HOS-215`  
Lock: `LOCK-FIN-P08-WD-001-01`  
State: IMPLEMENTATION_ACTIVE

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
