# P07-E — Provenance & Confidence Contract

Task: `FIN-P07-WE-001`  
Linear: `HOS-207`  
State: IN_PROGRESS  
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

P07-F remains blocked until P07-E canonical closure.
