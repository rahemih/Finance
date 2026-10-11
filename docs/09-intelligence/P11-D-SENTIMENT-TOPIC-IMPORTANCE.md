# P11-D — Sentiment / Topic / Importance

Task: `FIN-P11-WD-001`  
Linear: `HOS-245`  
State: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P11-WD-001-01` / RELEASED  
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


## Canonical closure evidence
- PR #228 merged as `102cfff3bbfe6db1ce85d0777ddfae8c8098d124`
- Human Gate approved exact head `d1652598b507c73b9d26089c67da4a4a111f1c8d`
- Human Gate artifact `sha256:4f22fe5ee992e65f2da68eede857c4188462bd007c56bf98269186a0c0a7ba9e`
- implementation Governance `38124661826` = SUCCESS
- post-merge Governance `38124784280` = SUCCESS
- post-merge Branch Hygiene `38124784268` = SUCCESS
- P11-E = READY_NOT_STARTED
