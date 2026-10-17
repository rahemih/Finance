# P18-D — Experiment Tracking

State: IN_PROGRESS  
Task: `FIN-P18-WD-001`

P18-D records immutable experiment specifications and externally produced evaluation run records. Every experiment is bound to one P18-C dataset manifest, code SHA-256, Strategy Registry identity/version, Model Registry identity/version, hypothesis and canonical numeric parameters.

Run records carry deterministic metrics and artifact identity. Experiment and run records are content-addressed and the registry snapshot is deterministic.

P18-D does **not** train or retrain models and does not select or promote candidates. P18-E owns Controlled Retraining. Live/Auto Trading and automatic live promotion remain disabled.
