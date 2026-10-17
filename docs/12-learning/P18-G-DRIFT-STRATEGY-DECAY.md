# P18-G — Drift / Strategy Decay

State: IN_PROGRESS  
Task: `FIN-P18-WG-001`

P18-G compares non-overlapping monitoring windows for the same strategy/model lineage. It tracks distribution drift, performance degradation and calibration degradation against explicit WARN/DECAY thresholds. DECAY emits `retrain_recommended=true` only; it does not directly retrain or promote. Live/Auto remain disabled.
