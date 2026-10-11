# P11-B — Ingestion / Deduplication

Task: `FIN-P11-WB-001`  
Linear: `HOS-243`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P11-WB-001-01` / ACQUIRED  
Canonical base: `be2ff32cdbe5cc7cc3e9e014caee06833482c4fe`

## Objective
Create deterministic provider-neutral ingestion and deduplication primitives before entity mapping or sentiment logic is allowed to consume news.

## Rules
- P11-A source/license/admissibility validation is mandatory before ingestion.
- Title/body normalization is deterministic and Unicode-safe.
- Exact identity is content-sensitive and point-in-time aware.
- Near-duplicate fingerprints ignore case/punctuation and remain deterministic.
- Dedup group identity is order-independent.
- No sentiment, asset mapping, signal, risk or execution authority is introduced.
- Canonical tests are offline.

## Safety
LIVE_TRADING and AUTO_TRADING remain DISABLED. Production news vendor remains NOT_SELECTED.
