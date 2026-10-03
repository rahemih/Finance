# A0–A10 Interaction and Handoff Matrix

| From | To | Purpose | Mandatory guard |
|---|---|---|---|
| Owner/Governance | A0 | authorized task and boundaries | active governed task |
| A0 | A1 | architecture/interface analysis | no authority expansion |
| A0 | A2 | data/freshness/provenance work | deterministic source rules |
| A0 | A3 | market evidence synthesis | evidence + freshness |
| A0 | A4 | quantitative research/validation | leakage/reproducibility controls |
| A0 | A5 | independent risk review | veto is binding |
| A0 | A6 | execution-system design/reconciliation work | cannot bypass A5 |
| A0 | A7 | learning/drift/experiment work | no self-promotion |
| A0 | A8 | security review | veto is binding |
| A0 | A9 | operations/health/recovery | degraded-mode authority only |
| A0 | A10 | evidence/audit/closure | cannot self-approve critical implementation |
| A3 | A4 | evidence/features/hypotheses | source provenance preserved |
| A4 | A5 | model/strategy evidence | deterministic validation first |
| A5 | A6 | risk-approved action proposal | A5 veto stops path |
| A8 | A6 | security authorization context | A8 veto stops path |
| A9 | A6 | health/circuit status | unhealthy providers fail closed |
| any | A10 | evidence/trace handoff | immutable provenance fields |

## Spawn
Only A0 or an explicitly authorized parent may spawn a bounded specialist listed in the specialist catalog and named in the active Task Contract.

## Termination
Specialists terminate when their bounded deliverable is returned, scope expires, budget/timeout is reached, parent cancels, veto occurs, or required evidence becomes unavailable.
