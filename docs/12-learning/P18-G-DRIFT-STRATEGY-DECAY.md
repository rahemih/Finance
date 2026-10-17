# P18-G — Drift / Strategy Decay

State: CANONICAL_COMPLETE  
Task: `FIN-P18-WG-001`

P18-G compares non-overlapping monitoring windows for the same strategy/model lineage. It tracks distribution drift, performance degradation and calibration degradation against explicit WARN/DECAY thresholds. DECAY emits `retrain_recommended=true` only; it does not directly retrain or promote. Live/Auto remain disabled.


## Canonical closure

PR #373 merged at `1c53636ec0f71648dfbafc3bf5cc425cf8b93a8d`; Governance `39022774417` SUCCESS; artifact `sha256:fe55d6e7bd5d92f0f499ba095cb30f04888cdf640a81186255330f432c916b5a`. P18-H READY_NOT_STARTED.
