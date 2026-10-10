# P09-D — Order Book / Spread / Depth / Imbalance

Task: `FIN-P09-WD-001`  
Linear: `HOS-228`  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
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


## Canonical closure evidence

- Implementation PR: `#196` = MERGED
- Final implementation head: `6cf574c9ad7b68e1f08dfef84bbb87f9fddd1b5f`
- Implementation merge SHA: `d2173286d0173e116f625f56cdc31aca64f09855`
- Initial PR Governance: `38050009316` = FAILED at strict Pyright / unused `Sequence` import
- Repair R01: `6cf574c9ad7b68e1f08dfef84bbb87f9fddd1b5f`
- Final PR Governance: `38050053794` = SUCCESS
- Final PR artifact: `sha256:a64e5b77ca2f98a5c37a6148d4de3164031f33e1340939d5660a7dc555a42829`
- Post-merge Governance: `38050120484` = SUCCESS
- Post-merge artifact: `sha256:0efa47ac20972e5af8bf6ee355f084c91f389f8c4ecad40bdc708f7fe457c6c7`
- Post-merge Branch Hygiene: `38050120518` = SUCCESS
- strict typecheck / P09 tests / deterministic P09-D evidence: PASS
- supply-chain and reproducibility controls: PASS

P09-E — Liquidity Heatmap / Capacity becomes `READY_NOT_STARTED`.
