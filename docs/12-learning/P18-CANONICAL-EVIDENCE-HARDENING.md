# P18 Canonical Evidence Hardening — FIN-P18-WH-001-R01

State: CANONICAL_COMPLETE after governed merge

## Authoritative evidence path

The pure P18 primitives remain useful deterministic components and unit-test surfaces. They are not, by themselves, authoritative evidence for cross-phase validation or promotion.

The authoritative path is `packages.learning.canonical_evidence`.

It independently resolves:
- P17 Strategy Record;
- P17 Model Record;
- P14 Signal Decision evidence;
- P15 Risk Decision evidence;
- P16 Firewall Decision evidence;
- curated Dataset identity;
- Experiment identity;
- candidate validation, challenger comparison, drift assessment, risk review and audit bundle identities.

Unknown, wrong-kind, wrong-state or degenerate placeholder artifacts fail closed.

## Governed metrics

Canonical evaluations require a versioned Metric Policy. Every metric has:
- metric id;
- version;
- unit;
- direction (HIGHER_BETTER or LOWER_BETTER).

Evaluation metric sets must exactly match the policy.

## Retraining budgets

Canonical retraining evidence includes and enforces explicit:
- CPU-seconds budget;
- peak-memory budget;
- wall-time budget;
- attempt limit.

Usage beyond any ceiling fails closed.

## Promotion

Authoritative Demo promotion accepts artifact references only. It resolves their canonical states itself; caller-supplied pass/fail booleans are not authoritative. LIVE always returns OWNER_LIVE_GATE_REQUIRED.

## CI binding

Governance derives canonical P18 lineage from the same-run P14-H, P15-I, P16-H and empirical P17 evidence outputs and requires deterministic byte-identical evidence twice.

P19 is not started by this repair. Live/Auto remain disabled.


## R03 typed trust-boundary closure — FIN-P18-WI-001-R03

R03 removes the remaining wrapper trust boundary.

- P17 Strategy/Model identities come from the actual canonical P17 module outputs.
- P14 Signal, P15 independent Risk Validation and P16 G8 Firewall identities are parsed and validated from their typed source evidence; whole-file hashes are provenance only and cannot masquerade as typed identities.
- authoritative Demo promotion resolves candidate validation, challenger comparison, drift, risk review and audit artifacts from `CanonicalEvidenceStore`; caller booleans remain non-authoritative.
- Controlled Retraining uses a subprocess sandbox with Linux CPU and address-space ceilings, subprocess wall timeout and bounded attempts. The resulting candidate still has no champion/promotion/execution authority.
- LIVE targets remain fail-closed at `OWNER_LIVE_GATE_REQUIRED`.

PR Governance `39039915556`, post-merge Governance `39040128212`, post-merge runtime `39040128177` and Branch Hygiene `39040128159` all passed.

This closes the technical acceptance criteria behind audits #382, #383 and #384 without starting P19 or enabling Live/Auto trading.
