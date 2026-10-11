# P11-E — Reliability / Rumor Controls

Task: `FIN-P11-WE-001`  
Linear: `HOS-246`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P11-WE-001-01` / ACQUIRED  
Canonical base: `43e0cbe1c46e2ef34e32cbe92d2f70f683737fb0`

## Objective

Convert canonical P11-A source/admissibility metadata and corroboration into deterministic reliability, rumor and review states after P11-D classification.

## Rules

- source-class reliability weights are explicit and versioned;
- P11-A admissibility state is authoritative for rumor state;
- UNCONFIRMED content is fail-closed as BLOCKED / QUARANTINED;
- COMMUNITY and SOCIAL content without corroboration requires review;
- HIGH-importance SINGLE_SOURCE content requires review;
- corroboration bonus is deterministic and capped;
- content identity must match P11-D or assessment fails closed;
- canonical tests are offline;
- production news vendor remains NOT_SELECTED;
- no probability, signal, risk or execution authority is introduced;
- LIVE_TRADING and AUTO_TRADING remain DISABLED.
