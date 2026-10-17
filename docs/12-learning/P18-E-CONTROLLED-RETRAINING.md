# P18-E — Controlled Retraining

State: IN_PROGRESS  
Task: `FIN-P18-WE-001`

Controlled Retraining consumes canonical P18-C/P18-D lineage and executes only an injected offline trainer under an immutable request containing dataset, experiment, base-model, strategy, code, deterministic seed and explicit CPU/memory/output budgets.

The result is always a **candidate-only** record. Required validation metrics are evaluated fail-closed. A failed candidate is retained as evidence but cannot proceed as validated. A passing candidate may only proceed to P18-F Champion / Challenger evaluation.

P18-E never grants promotion authority and has no broker/exchange, Live Trading or Auto Trading path.
