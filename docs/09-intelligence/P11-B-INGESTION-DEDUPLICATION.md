# P11-B — Ingestion / Deduplication

Task: `FIN-P11-WB-001`  
Linear: `HOS-243`  
State: CANONICAL_COMPLETE  
Lock: `LOCK-FIN-P11-WB-001-01` / RELEASED  
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


## Canonical closure evidence
- PR #224 merged as `bb332e04639ad62bf5e5beabef420e26087e94af`
- Human Gate approved exact head `9c9fc990db9ea095f09623cc04c728a7a086b34a`
- Human Gate artifact `sha256:111545f2b04f32a10a4fb926a5ceb4b321624e0f61c338071d8179847391dd9e`
- implementation Governance `38120779553` = SUCCESS
- post-merge Governance `38121023703` = SUCCESS
- post-merge Branch Hygiene `38121023870` = SUCCESS
- P11-C = READY_NOT_STARTED
