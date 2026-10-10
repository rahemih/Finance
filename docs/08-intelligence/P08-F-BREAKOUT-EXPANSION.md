# P08-F — Breakout / Expansion

Task: `FIN-P08-WF-001`  
Linear: `HOS-218`  
Lock: RELEASED  
State: CANONICAL_COMPLETE

## Objective

Implement deterministic point-in-time Breakout / Expansion evidence on the canonical P08 technical-intelligence foundation.

## Prior-only channel

The breakout reference channel is built strictly from the governed lookback bars **before** the current completed bar. The current bar is excluded from both prior high and prior low. This prevents self-referential breakout detection.

A completed close beyond the prior channel plus the governed buffer produces directional breakout context:

- above prior high + buffer = bullish breakout;
- below prior low - buffer = bearish breakout;
- otherwise = neutral.

## Expansion context

The current candle range is compared with the average range of the prior channel bars.

Expansion is correlated confirmation context inside the same `range-breakout-expansion` family. It may increase deterministic strength/confidence but it never becomes a second TechnicalEvidence vote.

A breakout may exist without expansion; expansion is confirmation quality, not a mandatory second condition.

## Independence boundary

The family emits exactly one BREAKOUT TechnicalEvidence object. Cross-family independence remains `PROVISIONAL_PENDING_P08_H` until the formal P08-H audit.

## Score semantics

Strength and confidence are deterministic technical-evidence scores, not empirical win probability, signal probability, trade recommendation or risk approval.

## Safety

- Direct trade/order output: FORBIDDEN
- Live Trading: DISABLED
- Auto Trading: DISABLED
- Country assumption: NONE
- Network/credentials required: NO

## Boundary

P08-G and later workstreams remain out of scope. G6 is not evaluated here.


## Canonical closure evidence

- Implementation PR: `#178` = MERGED
- Final implementation head: `3d97b9a1f734b0bff5aa8dc2d21e57e407b5f38d`
- Implementation merge SHA: `8a7cf93fec9c33944356c759738f5b5223eb4e01`
- PR Governance: `38040833918` = SUCCESS
- PR artifact: `sha256:d297a8f28e9f9ea9b75c79efd2c6375186db1c7553f5192a7412fe9ead532eae`
- Post-merge Governance: `38040905613` = SUCCESS
- Post-merge artifact: `sha256:061d3f5604148adaf7048ad29b215cf2f25ae9b189208dcee0b5d3b9e7e927f2`
- Post-merge Branch Hygiene: `38040905645` = SUCCESS
- Strict Pyright: PASS
- P08 technical-intelligence tests: PASS
- Deterministic P08-F evidence: PASS
- Current bar remains excluded from the reference channel
- Expansion remains correlated context, never a second vote
- Cross-family independence remains PROVISIONAL_PENDING_P08_H

P08-G — Multi-Timeframe & Regime is READY_NOT_STARTED. G6 remains NOT_EVALUATED.
