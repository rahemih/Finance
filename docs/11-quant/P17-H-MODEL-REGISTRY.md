# P17-H — Model Registry

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P17-WH-001`

## Objective

Provide an immutable deterministic registry for model versions and their data, feature, strategy and validation lineage.

A model version binds:
- model artifact, code and config SHA-256;
- feature schema and training dataset SHA-256;
- Strategy Registry record SHA-256;
- optional P17-D/P17-E validation certificates.

A `VALIDATED` model requires P17-D walk-forward and P17-E robustness lineage.

## Authority boundary

P17-H does not:
- retrain models automatically;
- promote models automatically;
- claim profitability;
- pass G9;
- route/execute orders;
- start P18.

P17-I remains the final Benchmark / Quant Gate.  
`G9_QUANT_VALIDATED` = NOT_REACHED.  
P18 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.
