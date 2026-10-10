# P10-G — Crypto Fundamental / On-Chain Context

Task: FIN-P10-WG-001
Linear: HOS-240
State: IMPLEMENTATION_ACTIVE
Lock: LOCK-FIN-P10-WG-001-01 / ACQUIRED

P10-G creates a deterministic, chain-anchored contract for crypto fundamental and on-chain evidence.

The canonical source baseline comes from P01-G:
- Blockscout = supplemental on-chain reference;
- independent validation = direct node or second indexer, still TBD;
- production provider = NOT_SELECTED.

A live capability check during P10-G confirmed Blockscout currently exposes Ethereum mainnet as chain ID 1. This check is source-validation evidence only. Canonical tests are fully offline and do not depend on a live Blockscout session or credential.

Every point carries chain ID, block height/hash/timestamp, NEXUS observed-at time, finality state, source snapshot digest and exact integer value/unit. Point-in-time resolution only sees chain views observed by the requested decision time.

Reorg safety is explicit: a later observation at the same height with a different block hash is a new observation; the earlier chain view remains preserved for historical replay.

P10-G intentionally excludes unverified exchange-wallet labels/reserve estimates. Blockscout on-chain evidence is not treated as exchange market data. No bullish/bearish inference, causal price-impact claim, probability, Risk approval or execution authority is produced.

Production on-chain provider: NOT_SELECTED.
Country assumption: NONE.
LIVE_TRADING: DISABLED.
AUTO_TRADING: DISABLED.

Next after canonical closure: P10-H — Reliability / Latency Validation.
