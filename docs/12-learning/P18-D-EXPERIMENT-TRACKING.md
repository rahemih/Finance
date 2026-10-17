# P18-D — Experiment Tracking

State: CANONICAL_COMPLETE  
Task: `FIN-P18-WD-001`

P18-D records immutable experiment specifications and externally produced evaluation run records. Every experiment is bound to one P18-C dataset manifest, code SHA-256, Strategy Registry identity/version, Model Registry identity/version, hypothesis and canonical numeric parameters.

Run records carry deterministic metrics and artifact identity. Experiment and run records are content-addressed and the registry snapshot is deterministic.

P18-D does **not** train or retrain models and does not select or promote candidates. P18-E owns Controlled Retraining. Live/Auto Trading and automatic live promotion remain disabled.


## Canonical closure

PR #367 merged at `29d05dfeea55706c0fbe55ccb8ca5f9e5ecea1b0`; Governance `39021475846` SUCCESS; artifact `sha256:dfd5d6a66f19d983713ae496b48f90a304253a525837e40e2226ba4a27410086`. P18-E is READY_NOT_STARTED.
