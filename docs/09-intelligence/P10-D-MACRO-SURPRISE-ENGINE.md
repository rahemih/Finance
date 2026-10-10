# P10-D — Macro Surprise Engine

Task: `FIN-P10-WD-001`  
Linear: `HOS-236`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P10-WD-001-01` / ACQUIRED

## Objective

Compute point-in-time macro surprise without allowing revisions or late consensus data to leak into the historical decision context.

## Inputs

### Actual

Actual is **only** the P10-C revision-zero first release.

Later revisions remain available to audit through P10-C, but they cannot rewrite the historical surprise.

### Consensus

Consensus is a separately evidenced snapshot with:

- the same macro series ID and unit as the actual;
- explicit provider identity;
- `CONSENSUS_MEDIAN` or `CONSENSUS_MEAN`;
- at least two contributing forecasts;
- finite Decimal value;
- observed-at timestamp;
- source dataset and payload SHA-256 evidence.

The consensus observed-at timestamp must be **strictly earlier** than the first-release release timestamp. A snapshot first seen at or after release is ineligible.

## Calculation

`raw_surprise = first_release_actual - consensus`

Decimal arithmetic is used. No float conversion is allowed.

The only direction labels are:

- `ABOVE_CONSENSUS`
- `BELOW_CONSENSUS`
- `AT_CONSENSUS`

These labels describe the numerical comparison only. They are **not** bullish/bearish labels and do not imply LONG/SHORT direction.

## Previous-at-time

P10-C `previous_at_first_release` provenance is retained in the result by vintage ID. It is context, not a substitute for consensus.

## Explicit non-claims

P10-D does not provide:

- standardized surprise z-scores;
- market-impact estimates;
- causal claims;
- asset direction;
- trade-success probability;
- recommendation;
- Risk approval;
- execution.

## Safety

Production consensus provider: NOT_SELECTED.  
Network/credentials required: false.  
Country assumption: NONE.  
LIVE_TRADING: DISABLED.  
AUTO_TRADING: DISABLED.
