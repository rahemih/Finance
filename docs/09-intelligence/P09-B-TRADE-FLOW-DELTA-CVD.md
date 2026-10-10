# P09-B — Trades / Buy-Sell Flow / Delta / CVD

Task: `FIN-P09-WB-001`  
Linear: `HOS-226`  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
Lead: A3 Market Intelligence  
Support: A0, A1, A2, A4, A6, A8, A9, A10

## Objective

Build a deterministic, provider-neutral trade-flow layer from actual trade prints while keeping inferred aggressor side, provider coverage, Delta and CVD claims explicit and bounded.

## Non-negotiable semantic boundary

A quote update or tick-volume observation is not a trade print. P09-B does not fabricate buyer/seller flow from quote-only feeds.

Spot-FX flow is accepted only when a broker or ECN provides trade prints. Such flow remains provider-scoped and must never be labeled global, consolidated or total-market spot-FX flow.

## Trade sources

- `VENUE_TRADE_PRINTS`: identified centralized venue prints; allowed for Crypto/Futures.
- `BROKER_TRADE_PRINTS`: broker-observed prints; allowed for provider-scoped spot FX.
- `ECN_TRADE_PRINTS`: ECN-observed prints; allowed for provider-scoped spot FX.

`TICK_VOLUME_PROXY`, quote updates and other activity proxies are not valid trade source kinds.

## Aggressor classification provenance

Every classified print records one method:

- `NATIVE_AGGRESSOR_FLAG` — side supplied by the source;
- `QUOTE_TEST` — inferred from a quote whose as-of time is not later than the trade;
- `TICK_RULE` — inferred only from a strictly preceding trade in the same source stream;
- `UNCLASSIFIED` — no defensible side; confidence is zero.

Inference is never relabeled as source-native truth.

## Delta / CVD

For an explicit source stream:

`Delta = classified buy volume - classified sell volume`

Unclassified volume is preserved separately and does not enter Delta.

`CVD_end = explicit CVD_start + Delta`

The reference implementation requires contiguous sequence numbers for CVD. Gaps, duplicate/out-of-order sequence, reversed event time or mixed streams fail closed instead of silently producing a misleading curve.

## Coverage

Two distinct quality measures are retained:

- classification coverage — fraction of total printed volume that received BUY/SELL classification;
- size-weighted classification confidence — confidence only across classified volume.

Neither is a probability of trade success.

## Validation target

- deterministic content-addressed trade/classification/snapshot identities;
- future quote leakage rejected;
- Forex global/consolidated flow claims rejected;
- quote/tick proxies rejected as trades;
- sequence gaps rejected for reference CVD;
- unknown volume retained separately;
- no execution or recommendation authority.

## Safety

- Production order-flow vendor: NOT_SELECTED
- Country assumption: NONE
- LIVE_TRADING: DISABLED
- AUTO_TRADING: DISABLED
- Direct trade/order authority: FORBIDDEN


## Canonical closure evidence

- Implementation PR: `#192` = MERGED
- Final implementation head: `c1f9c1408857a0df427518545837ac58dda84b52`
- Implementation merge SHA: `629b39cb5cfc0718045536b06f8ee3e92d1e5a4c`
- PR Governance: `38048202174` = SUCCESS
- PR artifact: `sha256:5e0c059983d122e7d55776af8a550fd90e4ba998cf35c61eb98eb6d080b05b9a`
- Post-merge Governance: `38048256001` = SUCCESS
- Post-merge artifact: `sha256:8b5416254fff09f90a7d02311d99ce288f85de6392b0efd7deaffc29582bd6fe`
- Post-merge Branch Hygiene: `38048256050` = SUCCESS
- Strict typecheck / P09 tests / deterministic P09-B evidence: PASS
- supply-chain and reproducibility controls: PASS

P09-C — Volume Profile becomes `READY_NOT_STARTED`.
