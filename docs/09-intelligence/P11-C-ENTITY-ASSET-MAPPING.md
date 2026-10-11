# P11-C — Entity / Asset Mapping

Task: `FIN-P11-WC-001`  
Linear: `HOS-244`  
State: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P11-WC-001-01` / RELEASED  
Canonical base: `aff6dc19b5bce63e46cba4e1f93ad4362e4045d8`

## Objective
Map deterministic news mentions to canonical entities/assets after P11-B ingestion and before sentiment/importance logic.

## Rules
- registry aliases are explicit and normalized;
- cross-entity alias ambiguity fails closed;
- matching is Unicode and word-boundary aware;
- mapping result preserves the ingested news content ID;
- no-match is explicit;
- canonical tests are offline;
- LIVE_TRADING and AUTO_TRADING remain DISABLED.


## Canonical closure evidence
- PR #226 merged as `61e0c9932ea95401b50fd42623d30019d58fd811`
- Human Gate approved exact head `de2046208362ce2999efe943efbc3328aa44b9b0`
- Human Gate artifact `sha256:8a7d8382dc0a1d44928692d9eb4483cbb7037f48d97f6f43709668ccd66cc2da`
- implementation Governance `38121521870` = SUCCESS
- post-merge Governance `38124210685` = SUCCESS
- post-merge Branch Hygiene `38124210733` = SUCCESS
- P11-D = READY_NOT_STARTED
