# P08-F — Breakout / Expansion

Task: `FIN-P08-WF-001`  
Linear: `HOS-218`  
Lock: `LOCK-FIN-P08-WF-001-01`  
State: IMPLEMENTATION_ACTIVE

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
