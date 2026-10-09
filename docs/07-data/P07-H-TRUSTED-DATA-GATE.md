# P07-H — Trusted Data Gate / G5

Task: `FIN-P07-WH-001`  
Linear: `HOS-210`  
State: IN_PROGRESS  
Lead: A10 Evidence/Audit  
Supporting: A0, A1, A2, A4, A8, A9

## Objective

Certify the complete P07 data-quality chain and close `G5_TRUSTED_DATA` only when all canonical prerequisites and fail-closed invariants are proven.

## Gate inputs

The evaluator consumes the machine-readable closure documents for P07-A through P07-G. Every prerequisite must be `CANONICAL_COMPLETE`, have its lock released, and contain merge/post-merge Governance/artifact/Branch-Hygiene evidence.

## Required integrated invariants

- Live Trading remains DISABLED.
- Auto Trading remains DISABLED.
- Country assumption remains NONE.
- P07-E exposes the canonical FeatureMaterialization quality adapter.
- P07-F forbids non-accepted downstream routing.
- P07-G treats NO_DATA as blocking.
- Missing or malformed evidence fails the gate.

## Governance boundary

A PASS produced by the evaluator during CI is certification evidence only. Canonical `G5_TRUSTED_DATA = PASS` is written only after the P07-H implementation PR and its post-merge checks succeed, followed by the closure reconciliation.

P07-H does not start P08. After G5 passes, P08 remains `NOT_STARTED / OWNER_PHASE_AUTHORIZATION_REQUIRED`.

## Safety

Network: not required.  
Credentials: not required.  
Country assumption: NONE.  
Live Trading: DISABLED.  
Auto Trading: DISABLED.
