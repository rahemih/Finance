# P11-D — Sentiment / Topic / Importance

Task: `FIN-P11-WD-001`  
Linear: `HOS-245`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P11-WD-001-01` / ACQUIRED  
Canonical base: `f97d92f1c255d828546a79f52033915ab1c61eb1`

## Objective

Add deterministic, explainable classification after P11-C entity/asset mapping.

## Rules

- topic classification uses explicit keyword rules and deterministic ordering;
- sentiment is descriptive only: POSITIVE / NEGATIVE / MIXED / NEUTRAL;
- importance is HIGH / MEDIUM / LOW from explicit event/content evidence;
- evidence terms and reason codes are emitted for auditability;
- P11-C content identity must match or classification fails closed;
- source reliability/rumor controls remain P11-E;
- canonical tests are offline;
- no probability, signal, risk or execution authority is introduced;
- LIVE_TRADING and AUTO_TRADING remain DISABLED.
