# P22-C — Auto Diagnostics

Task: `FIN-P22-WC-001`  
Phase: P22 — Operations / Diagnostics / Recovery  
Status: CANONICAL_COMPLETE

## Objective

Create deterministic automatic diagnostic reports from explicit operational symptoms and evidence references, without crossing into remediation or self-healing.

## Diagnostic semantics

Known symptom codes are mapped by a fixed policy to a category, severity and hypothesis code. Multiple known symptoms are resolved by deterministic severity ranking and lexical tie-breaking.

Unknown symptoms are never guessed into a root cause. They return `UNRESOLVED` with `UNRESOLVED_REQUIRES_OPERATOR_REVIEW`.

P22-B system state supplies a severity floor, so a diagnostic report cannot silently understate an already-restricted operational state.

## Evidence contract

Diagnostic reports require bounded symptom codes, one or more content-addressed evidence references, an explicit system state, correlation ID and timestamp. Inputs are canonicalized before report hashing.

## Authority boundary

A diagnostic hypothesis is not repair authority. Every report has `remediation_authority = false`. P22-C performs no network query, restart, failover, state mutation, self-healing or risk-policy change.

`LIVE_TRADING` and `AUTO_TRADING` remain disabled. P22-C is canonically closed and P22-D — Restricted Self-Healing is READY_NOT_STARTED.


## Canonical closure evidence

- implementation PR #453 = MERGED;
- final implementation head = `c0bb38549ac6e4507075798f7591768c6663aec5`;
- implementation Governance = `40321143754` / SUCCESS;
- implementation artifact = `12648268915` / `sha256:e560ce00fcef619baf58a3be96f0a9c8d294277b19630850467d727544a543ef`;
- deterministic evidence ID = `c6066aeed512f6c38c02371303cdb1346366492b491aa605d5ba7c6e1540bdb3`;
- deterministic evidence SHA256 = `937509617e102d2817fb9dedad02456fe5fd5c34630f2e5e7066bfc03ba5d51a`;
- implementation merge SHA = `489ae15cc7491070dd9820e2f79c92f3684c2451`;
- post-merge Governance = `40321433063` / SUCCESS;
- post-merge artifact = `12649880228` / `sha256:53c7863c96b8d4de60abdad5cd2093cddd0c82bff0f0a785814efd67f83f744b`;
- post-merge Branch Hygiene = `40321432961` / SUCCESS;
- lock = RELEASED.

P22-D = READY_NOT_STARTED.  
G12_OPERATIONS_VALIDATED = NOT_REACHED.  
LIVE_TRADING / AUTO_TRADING = DISABLED.
