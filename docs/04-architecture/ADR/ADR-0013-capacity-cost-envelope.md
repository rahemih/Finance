# ADR-0013 — Provisional Capacity & Cost Envelope

Status: ACCEPTED  
Task: `FIN-P02-WH-001`

## Context

P02 architecture needs explicit sizing and cost assumptions before concrete engineering choices can be evaluated.

Measured production data do not yet exist, so pretending to know final throughput/storage/SLA values would create false precision.

## Decision

Adopt the provisional envelope defined in:

- `docs/04-architecture/CAPACITY-COST-ENVELOPE.md`
- `docs/04-architecture/capacity-cost-envelope.json`

Use three scenario classes:
- BOOTSTRAP;
- OPERATING;
- STRESS.

All numeric values are design assumptions until replaced by benchmark evidence.

The OPERATING scenario is the primary P04 design point.

The STRESS scenario is an architecture-review boundary, not a promise of silent unlimited scale.

NEXUS QUANT is explicitly **non-HFT**.

### Storage

Use formula-driven sizing based on event rate and serialized size.

Raw retention remains licensing-aware.

Compression ratios are planning assumptions only.

### Latency

Separate:
- provider/source latency;
- internal ingest latency;
- signal-generation latency;
- Risk/Firewall latency;
- OMS dispatch latency.

Do not hide upstream/network latency inside internal SLOs.

### Cost

Use a category formula rather than hard-coded vendor totals.

Budget pressure may throttle discretionary research/AI workloads but cannot disable Risk, Firewall, Security, Audit, Reconciliation or Kill Switches.

### DR

Use provisional RPO/RTO classes that P22 must validate through drills.

Recovery targets never replace broker/exchange reconciliation.

## Alternatives considered

### No numeric envelope until real data exists
Rejected because P04 cannot evaluate technologies without a bounded target.

### Treat provisional values as production SLA
Rejected because they are not measured.

### Optimize for HFT/microsecond latency
Rejected because it adds cost/complexity unrelated to current project goals.

### Fix cloud/vendor cost now
Rejected because no cloud/runtime/provider procurement decision belongs in P02-H.

## Consequences

Positive:
- P04 has measurable design targets;
- cost/storage growth is visible early;
- later measurements can explicitly replace assumptions;
- scaling triggers prevent silent architecture drift.

Negative:
- provisional numbers will need maintenance;
- conservative envelopes may temporarily over-provision;
- provider-specific data feeds can break assumptions.

## Risks / mitigations

Risk: assumptions are mistaken for guarantees.  
Mitigation: every artifact labels them PROVISIONAL and requires downstream replacement.

Risk: storage explodes from order-book feeds.  
Mitigation: measured P05/P06 data, rights-aware retention and review triggers.

Risk: cost pressure weakens safety.  
Mitigation: safety/security/audit components are outside discretionary cost shedding.

Risk: STRESS envelope becomes de facto target.  
Mitigation: exceeding/approaching it triggers architecture review.

## Validation / evidence

P04 benchmarks candidate technologies.

P05 measures real event rates/sizes/latency.

P06 measures compression/retention/replay.

P17/P18 measure research/learning cost.

P22 validates backup/restore/RPO/RTO.

## Rollback / supersession

Measured benchmarks may replace provisional values through governed updates without weakening safety boundaries.

Material envelope changes that alter architecture require ADR review.

## Related tasks / gates

P02-H, P04, P05, P06, P17, P18, P22, G2.
