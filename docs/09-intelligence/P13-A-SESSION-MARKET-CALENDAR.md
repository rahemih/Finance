# P13-A — Session / Market Calendar

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P13-WA-001`  
Linear: `HOS-261`

## Objective

Provide deterministic timing context for Crypto and Forex without turning timing context into a trade signal, probability, ranking or execution authority.

## Canonical baseline

- all canonical timestamps are UTC;
- Crypto Spot and Crypto Futures are modeled as 24/7;
- Forex Spot uses a governed 24/5 weekly baseline with Sunday 22:00 UTC open and Friday 22:00 UTC close;
- regional context windows are ASIA 00:00–08:00 UTC, EUROPE 07:00–16:00 UTC and US 13:00–21:00 UTC;
- overlapping regional windows are reported as context, not as a recommendation;
- unknown market kinds and invalid timestamps fail closed.

## Production-boundary guardrails

This baseline does **not** claim to be a provider/exchange holiday calendar. Dynamic DST adjustment and production holiday calendars remain out of scope until a governed production calendar source is selected. The production calendar vendor remains `NOT_SELECTED`.

P12-F keeps historical UTC seasonality ownership. P13-A owns session/calendar semantics. P13-B owns Best Trading Time scoring.

## Safety

- no probability output;
- no opportunity ranking;
- no risk approval;
- no execution authority;
- network/credentials not required;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.
