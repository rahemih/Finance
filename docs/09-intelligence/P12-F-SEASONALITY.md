# P12-F — Seasonality

Task: `FIN-P12-WF-001`  
Linear: `HOS-257`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P12-WF-001-01` / ACQUIRED  
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
