# P18-H — Promotion Governance

State: CANONICAL_COMPLETE  
Task: `FIN-P18-WH-001`

P18-H consumes immutable candidate, Champion/Challenger, drift and audit evidence and produces a fail-closed governance decision.

A DEMO_CHAMPION request may receive an `APPROVE_DEMO_CHAMPION_RECORD` only when candidate validation, challenger recommendation, risk review and audit evidence all pass and there are zero critical blockers. This record does not mutate any registry.

Every `LIVE` target is unconditionally returned as `OWNER_LIVE_GATE_REQUIRED`. P18 has no authority to perform or automate live promotion.

Live Trading and Auto Trading remain disabled.


## Canonical closure

PR #376 merged at `149f50d225cdf5af99fb2eef79fb827124a530cd`; Governance `39025338750` SUCCESS; artifact `sha256:ccf5538eeb304c5bebf591f9aa77b887b686b23163a69c92cbdbebb96e674a8b`. P18-I READY_NOT_STARTED. Live target remains owner-gated.
