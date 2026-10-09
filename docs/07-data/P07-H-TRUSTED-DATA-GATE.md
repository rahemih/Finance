# P07-H — Trusted Data Gate / G5

Task: `FIN-P07-WH-001`  
Linear: `HOS-210`  
State: CANONICAL_COMPLETE  
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

## Canonical gate result

`G5_TRUSTED_DATA = PASS`

All P07-A through P07-G canonical evidence and integrated fail-closed invariants passed. P07 is eligible for canonical phase closure.

## Implementation evidence

- Implementation PR: `#166` = MERGED
- Final implementation head: `4d3453778e07b84dfaca194b95a115189520d3c4`
- Implementation merge SHA: `ecfecc909263153d719314979fd11b52dc4ce2e8`
- PR Governance: `37965972296` = SUCCESS
- PR artifact: `sha256:8ec2a2d58cbd246d04495ba62cd1f5856e47f34381bb708b284186359fdeea90`
- Post-merge Governance: `37966153751` = SUCCESS
- Post-merge artifact: `sha256:77f5804326333152a3faef4ef988146871790aad234183876dffc3f794212869`
- Post-merge Branch Hygiene: `37966153603` = SUCCESS
- Lock: RELEASED

P08 remains `NOT_STARTED / OWNER_PHASE_AUTHORIZATION_REQUIRED`.
