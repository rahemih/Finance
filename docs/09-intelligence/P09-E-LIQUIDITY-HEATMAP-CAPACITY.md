# P09-E — Liquidity Heatmap / Capacity

Task: `FIN-P09-WE-001`  
Linear: `HOS-229`  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
Lead: A4 Quant  
Support: A0, A1, A2, A3, A6, A8, A9, A10

## Objective

Build deterministic point-in-time liquidity heatmaps from governed P09-D order books and report **displayed provider-book capacity** without implying executable quantity, fill probability or market impact.

## Distance bands

The midpoint is inherited from the validated best bid/ask:

`mid = (best_bid + best_ask) / 2`

For bids:

`distance_bps = (mid - bid_price) / mid * 10000`

For asks:

`distance_bps = (ask_price - mid) / mid * 10000`

Policy bands are strictly increasing positive thresholds. A level is assigned to the first threshold greater than or equal to its distance. This makes non-cumulative cells mutually exclusive.

Reference thresholds: 100 / 250 / 500 / 1000 bps.

## Heatmap cells

For each side and distance band the reference implementation records:

- displayed size;
- displayed price-times-size notional;
- cumulative displayed size through the band;
- cumulative displayed notional through the band;
- total cumulative displayed notional;
- bid/ask cumulative capacity share in integer basis points.

Displayed notional means `price × provider-displayed size`; it does not assert a universal currency or executable value beyond the source contract.

Levels outside the maximum configured distance are retained separately as outside-band displayed size/notional rather than silently dropped.

## Capacity semantics

"Capacity" in P09-E means only **displayed capacity visible in the specific provider/venue snapshot at the snapshot as-of time**.

It does **not** mean:

- guaranteed fillable quantity;
- hidden liquidity;
- future liquidity;
- slippage estimate;
- market-impact estimate;
- cross-provider consolidated liquidity.

## Forex boundary

Spot-FX liquidity inherits the P09-D source restriction: only broker/ECN/provider-scoped books are accepted. GLOBAL, CONSOLIDATED or TOTAL_MARKET spot-FX liquidity claims remain forbidden.

## Fail-closed rules

- invalid P09-D order book;
- empty/non-increasing/non-positive band policy;
- policy exceeding maximum band count;
- no displayed liquidity inside the maximum band when required;
- any policy enabling hidden-liquidity inference, fillability claims, slippage/impact claims, cross-provider aggregation, global FX liquidity or direct trade output.

## Safety

- production order-flow vendor: NOT_SELECTED;
- country assumption: NONE;
- LIVE_TRADING: DISABLED;
- AUTO_TRADING: DISABLED;
- recommendation/probability/Risk/execution authority: FORBIDDEN.


## Canonical closure evidence

- Implementation PR: `#198` = MERGED
- Final implementation head: `fec27e89e65267697d19655f75e1baa5810d9933`
- Implementation merge SHA: `6cb8549cbfae68877d7e28ada824a8df93a2c351`
- PR Governance: `38050757349` = SUCCESS
- PR artifact: `sha256:dfdc23d78ee0cfb3400a70057fadbbf1797f2b6df9dc444ba16b2a2ac0a93931`
- Post-merge Governance: `38050829203` = SUCCESS
- Post-merge artifact: `sha256:a58a01576d7f7407a46a8500bdd5ad611fcf8bf80b1a7cfa6d06cb7b3a292ce2`
- Post-merge Branch Hygiene: `38050829122` = SUCCESS
- strict typecheck / P09 tests / deterministic P09-E evidence: PASS
- supply-chain and reproducibility controls: PASS

P09-F — Funding / OI / Liquidation / Crowding becomes `READY_NOT_STARTED`.
