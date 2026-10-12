# P12-F — Seasonality

Task: `FIN-P12-WF-001`  
Linear: `HOS-257`  
State: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P12-WF-001-01` / RELEASED  
Canonical base: `eb054db8022ad75133b6337286c1d8815a4308f0`

## Objective

Measure deterministic UTC calendar seasonality in historical market memory without overlapping P13 session/calendar ownership or overstating recurring patterns.

## Contract

- governed UTC buckets: hour-of-day / day-of-week / month-of-year;
- optional canonical P08-G regime conditioning;
- signed-bps historical return observations;
- minimum sample count and duplicate timestamp fail-closed rules;
- deterministic mean return, dispersion and sampling uncertainty;
- immutable provenance SHA-256 and source dataset versions;
- exchange/session/holiday calendars are explicitly out of scope.

## Safety

Seasonality is descriptive historical evidence. It is not causation, probability, a signal, risk approval or execution authority. LIVE_TRADING and AUTO_TRADING remain DISABLED.


## Canonical closure evidence
- implementation PR #256 = MERGED
- final implementation head `570eecfb4ec4197998a01fdb1469b6789758b54e`
- implementation Governance `38222075697` = SUCCESS
- implementation artifact `sha256:a8a50677ab155097e92b963f81dde275540aa7f6921ec7454c1eee06a8f48198`
- implementation merge SHA `56d15e598a9aeb8b1c519bf7f9fc2fabeb3909a6`
- post-merge Governance `38222323292` = SUCCESS
- post-merge Branch Hygiene `38222323322` = SUCCESS
- P12-G = READY_NOT_STARTED
