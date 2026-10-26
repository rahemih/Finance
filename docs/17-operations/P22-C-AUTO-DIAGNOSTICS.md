# P22-C — Auto Diagnostics

Task: `FIN-P22-WC-001`  
Phase: P22 — Operations / Diagnostics / Recovery  
Status: IN_PROGRESS

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

`LIVE_TRADING` and `AUTO_TRADING` remain disabled. P22-D remains NOT_STARTED until P22-C is canonically closed.
