# Change Control

The Master Roadmap is immutable after approval.

## Allowed change mechanisms

- ERRATA: factual/typographical correction without scope change
- ADR: architecture decision
- RFC: significant design or scope proposal
- ROADMAP ADDENDUM: new capability outside the frozen baseline

## Critical change flow

Proposal → Diff → Risk Review → Approval → Deploy → Monitor → Audit → Rollback/Close.

Critical changes include live credentials, risk ceilings, leverage ceilings, kill-switch policy, model promotion to live, and execution-policy changes.

During a SEV-0/SEV-1 incident, non-essential changes may be frozen.
