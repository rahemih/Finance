# P09-D — Order Book / Spread / Depth / Imbalance

Task: `FIN-P09-WD-001`  
Linear: `HOS-228`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P09-WD-001-01` / ACQUIRED  
Lead: A3 Market Intelligence  
Support: A0, A1, A2, A4, A6, A8, A9, A10

## Objective

Establish deterministic point-in-time Order Book analytics for spread, comparable top-N depth and normalized depth imbalance while retaining provider scope and trusted provenance.

## Snapshot boundary

Each snapshot carries:

- symbol and market class;
- provider, venue and source kind;
- coverage scope;
- event time, as-of time and sequence;
- trusted dataset version and quality evidence digest;
- ordered bid and ask levels.

Level prices and sizes must be positive.

## Canonical ordering

- bids: strictly descending price, unique levels;
- asks: strictly ascending price, unique levels;
- at least one level per side;
- best bid must be strictly below best ask.

Locked or crossed books fail closed in the P09-D reference contract.

## Spread

`mid = (best_bid + best_ask) / 2`

`spread = best_ask - best_bid`

`spread_bps = round_half_even(spread / mid * 10000)`

These are descriptive book-state measures.

## Depth

For requested comparable depth `N`, at least `N` levels must exist on both sides.

`bid_depth = sum(size of first N bids)`

`ask_depth = sum(size of first N asks)`

## Imbalance

`imbalance_bps = round_half_even((bid_depth - ask_depth) / (bid_depth + ask_depth) * 10000)`

Range is bounded to `[-10000, 10000]`.

Positive values mean more displayed bid depth in the measured provider book; negative values mean more displayed ask depth. This is not a probability of future price direction.

## Forex boundary

Spot-FX books are accepted only from governed broker/ECN book sources. They remain provider-scoped. Claims of GLOBAL, CONSOLIDATED or TOTAL_MARKET spot-FX depth are forbidden.

## Safety

- production order-flow vendor: NOT_SELECTED;
- no slippage/market-impact or execution capacity model in P09-D;
- country assumption: NONE;
- LIVE_TRADING: DISABLED;
- AUTO_TRADING: DISABLED;
- direct trade/order/recommendation/probability authority: FORBIDDEN.
