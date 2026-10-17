# P18-H — Promotion Governance

State: IN_PROGRESS  
Task: `FIN-P18-WH-001`

P18-H consumes immutable candidate, Champion/Challenger, drift and audit evidence and produces a fail-closed governance decision.

A DEMO_CHAMPION request may receive an `APPROVE_DEMO_CHAMPION_RECORD` only when candidate validation, challenger recommendation, risk review and audit evidence all pass and there are zero critical blockers. This record does not mutate any registry.

Every `LIVE` target is unconditionally returned as `OWNER_LIVE_GATE_REQUIRED`. P18 has no authority to perform or automate live promotion.

Live Trading and Auto Trading remain disabled.
