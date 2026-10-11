# P11-C — Entity / Asset Mapping

Task: `FIN-P11-WC-001`  
Linear: `HOS-244`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P11-WC-001-01` / ACQUIRED  
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
