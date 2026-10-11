# P11-G — Alerting & Narrative Inputs

Task: `FIN-P11-WG-001`  
Linear: `HOS-248`  
State: IMPLEMENTATION_ACTIVE  
Lock: `LOCK-FIN-P11-WG-001-01` / ACQUIRED  
Canonical base: `85299333743d4e670df8aad1874976a1642023e0`

## Objective

Turn canonical P11 context into deterministic alert eligibility/severity and a structured narrative-input envelope.

## Rules

- severity is INFORMATIONAL / IMPORTANT / CRITICAL / SUPPRESSED;
- EXPIRED, BLOCKED or QUARANTINED content is suppressed;
- critical severity requires HIGH importance + HIGH reliability + FRESH state;
- important severity requires eligible HIGH/MEDIUM context with adequate reliability/freshness;
- narrative input preserves source/content/entity/topic/sentiment/reliability/freshness evidence;
- a stable grouping key supports downstream dedup/grouping;
- no notification channel delivery occurs in P11-G;
- no LLM-generated narrative is required in canonical CI;
- production news vendor remains NOT_SELECTED;
- no signal probability, risk or execution authority is introduced;
- LIVE_TRADING and AUTO_TRADING remain DISABLED.
