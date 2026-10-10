# P08-C — Momentum Family

Task: `FIN-P08-WC-001`
Linear: `HOS-213`
Lock: RELEASED
State: CANONICAL_COMPLETE

## Objective

Implement a deterministic point-in-time Momentum Family distinct from P08-B Trend.

## Model

The reference family uses short-horizon rate of change, long-horizon rate of change, and horizon-normalized acceleration. These correlated measurements are one family under `return-momentum`, not multiple independent confirmations.

The family emits one `TechnicalEvidence` object with bullish, bearish, or neutral direction.

## Controls

Inputs must share symbol, timeframe, dataset version, and data-quality lineage; event times are strictly increasing and future as-of information is rejected.

Strength and confidence are deterministic technical-evidence scores, not empirical trade probabilities.

## Safety

Direct trade output is forbidden. Live Trading and Auto Trading remain DISABLED. Country assumption is NONE. No network or credentials are required.

## Boundary

P08-D and later workstreams remain out of scope. G6 is not evaluated here.


## Canonical closure evidence

- Implementation PR: `#172` = MERGED
- Final implementation head: `e4fbaf93eefb9c184194ab34ea15b2dca8068c6a`
- Implementation merge SHA: `ab9918f10d77bbc58884990afb4c57002b036938`
- PR Governance: `38036207633` = SUCCESS
- PR artifact: `sha256:61e95e548bb03e5c8297d0abad0e7b8095ea1660faf58ddbfb1acc06e4b4c0f3`
- Post-merge Governance: `38036267374` = SUCCESS
- Post-merge artifact: `sha256:bcd35d740b9e33571acc8df2f474431a3129695f17bfdadad87d882511301518`
- Post-merge Branch Hygiene: `38036267380` = SUCCESS
- Strict Pyright: PASS
- P08 technical-intelligence tests: PASS
- Deterministic P08-C momentum evidence: PASS

P08-D — Market Structure & Price Action is READY_NOT_STARTED. G6 remains NOT_EVALUATED.
