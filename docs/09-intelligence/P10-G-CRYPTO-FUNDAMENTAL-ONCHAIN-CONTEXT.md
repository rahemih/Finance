# P10-G — Crypto Fundamental / On-Chain Context

Task: FIN-P10-WG-001
Linear: HOS-240
State: CANONICAL_COMPLETE
Lock: RELEASED

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

## Canonical implementation evidence

- Implementation PR: #218 = MERGED
- Final implementation head: `006df3e20ddde59b13c61355fa3aa0dcaa053812`
- Implementation merge SHA: `f3228ed5ba7bf7a3e675b4e9f7616b979ad7e635`
- PR Governance: `38082210100` = SUCCESS
- PR artifact: `sha256:110e883f61f882c8c5d9efac463abfa93454ae3d67aebb584f42b38e6ca39ae2`
- Post-merge Governance: `38082293194` = SUCCESS
- Post-merge artifact: `sha256:3ae12d1e44b6a71c9eeb431202d667e37a0275bcdb02ee9bb9dd673a0b3cb9cb`
- Post-merge Branch Hygiene: `38082293124` = SUCCESS

P10-H becomes READY_NOT_STARTED.
