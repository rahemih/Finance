# P07-E — Provenance & Confidence Contract

Task: `FIN-P07-WE-001`  
Linear: `HOS-207`  
State: CANONICAL_COMPLETE  
Lead: A2 Data  
Supporting: A0, A1, A3, A4, A8, A9, A10

## Objective

Create one canonical evidence-lineage, confidence and eligibility contract for downstream data consumers.

## Provenance components

P07-E requires explicit evidence for:

- P07-A schema validation;
- P07-B completeness/duplicate checks;
- P07-C staleness/outlier/sequence checks;
- P07-D cross-provider comparison.

Every component carries its control ID, explicit PASS/FAIL outcome, explicit confidence in basis points and the SHA-256 digest of its evidence.

## Confidence

No confidence is inferred from missing information and no adaptive weighting is allowed. Policy version `p07e-v1` defines an explicit score scale, eligibility threshold and weight for each required control.

The aggregate is deterministic and order-independent.

## Eligibility

- missing required provenance → `UNKNOWN`;
- any explicit FAIL → `INELIGIBLE`;
- complete PASS provenance below threshold → `INELIGIBLE`;
- complete PASS provenance at/above threshold → `ELIGIBLE`.

Only `ELIGIBLE` is accepted by the existing P06 FeatureMaterialization contract. P07-E exposes an adapter to its canonical `QualityEligibility` type.

## Boundaries

P07-F owns quarantine/fail-closed routing. P07-G owns quality dashboards/SLOs. P07-H owns G5 trusted-data closure.

## Safety

Production data-quality vendor: NOT_SELECTED.  
Network: not required.  
Credentials: not required.  
Country assumption: NONE.  
Live Trading: DISABLED.  
Auto Trading: DISABLED.

P07-E closure is canonical. P07-F is READY_NOT_STARTED under the existing P07 Owner authorization.

## Closure evidence

- Implementation PR: `#160` = MERGED
- Final implementation head: `6421b19e2a5b8e6d3edf4f8ddd0b83d6f75e996b`
- Implementation merge SHA: `53de9831ee75a527033aafb890c7a528a5ffbbf7`
- PR Governance: `37959787553` = SUCCESS
- PR artifact digest: `sha256:cb8a8b1c832e68ffef8f42bd6b963a7517eaddf274d6926573a90c3d9cac7e06`
- Post-merge Governance: `37959921604` = SUCCESS
- Post-merge artifact digest: `sha256:8f26a04d9f0683cfa1099cb199669bcc9c77494b213711559b930562bd0d42cf`
- Post-merge Branch Hygiene: `37959921534` = SUCCESS
- Lock: RELEASED
- G5_TRUSTED_DATA: NOT_EVALUATED
