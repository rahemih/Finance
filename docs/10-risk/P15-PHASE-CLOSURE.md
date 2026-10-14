# P15 — Risk & Portfolio — Canonical Phase Closure

State: CANONICAL_COMPLETE  
Owner phase authorization: GRANTED for P15 / CONSUMED  
Independent validation: `P15_INDEPENDENT_RISK_VALIDATION / PASS`  
Frozen-roadmap exit gate: NONE DEFINED FOR P15  
Next phase: P16 — Pre-Trade Risk Firewall / OWNER_PHASE_AUTHORIZATION_REQUIRED  
Canonical closure base: `a18c582855d15f15e17a011716358f00ba4e5181`

## Closure result

P15-A through P15-I are CANONICAL_COMPLETE. All governed P15 locks are RELEASED. There is no active P15 governed task or lock.

P15 delivers a deterministic portfolio-risk layer spanning hierarchical risk budgets, candidate position sizing, asset/strategy limits, portfolio/correlation exposure, margin/leverage, drawdown/risk-of-ruin, counterparty/capital segmentation, defensive new-risk modes and independent integrated validation.

The frozen Master Roadmap defines no named exit gate for P15. The canonical P15 validation marker is therefore `P15_INDEPENDENT_RISK_VALIDATION / PASS`; it closes P15 only and must not be confused with P16's frozen `G8_PRETRADE_SAFE` gate.

## Workstream closure

| Workstream | Task | Linear | State | Implementation PR | Closure PR |
|---|---|---|---|---|---|
| P15-A — Risk Policy / Budget Hierarchy | FIN-P15-WA-001 | CONTINUATION_REGISTER | CANONICAL_COMPLETE | #302 | #303 |
| P15-B — Position Sizing | FIN-P15-WB-001 | CONTINUATION_REGISTER | CANONICAL_COMPLETE | #305 | #306 |
| P15-C — Asset / Strategy Limits | FIN-P15-WC-001 | CONTINUATION_REGISTER | CANONICAL_COMPLETE | #307 | #308 |
| P15-D — Portfolio / Correlation Exposure | FIN-P15-WD-001 | CONTINUATION_REGISTER | CANONICAL_COMPLETE | #309 | #310 |
| P15-E — Margin / Leverage | FIN-P15-WE-001 | CONTINUATION_REGISTER | CANONICAL_COMPLETE | #311 | #312 |
| P15-F — Drawdown / Risk-of-Ruin | FIN-P15-WF-001 | CONTINUATION_REGISTER | CANONICAL_COMPLETE | #314 | #315 |
| P15-G — Counterparty / Capital Segmentation | FIN-P15-WG-001 | CONTINUATION_REGISTER | CANONICAL_COMPLETE | #316 | #317 |
| P15-H — Defensive / De-Risk Modes | FIN-P15-WH-001 | CONTINUATION_REGISTER | CANONICAL_COMPLETE | #318 | #319 |
| P15-I — Independent Risk Validation | FIN-P15-WI-001 | CONTINUATION_REGISTER | CANONICAL_COMPLETE | #320 | #321 |

## Capability closure

P15 now provides:
- hierarchical, finite, explicit risk-budget governance with non-bypassable veto semantics;
- deterministic candidate position sizing from explicit equity and stop geometry;
- explicit asset and strategy risk/open-position ceilings;
- portfolio gross/net and correlation-cluster exposure controls;
- explicit leverage and margin-utilization controls with conservative rounding;
- deterministic drawdown and explicit validated risk-of-ruin controls;
- explicit counterparty and capital-segment allocation ceilings;
- NORMAL / REDUCED_RISK / DEFENSIVE / HALT_NEW_RISK policy modes for future new-risk admission;
- independent fail-closed validation of A→H lineage, veto propagation, defensive-mode consistency and zero execution authority.

## Validation closure

Across P15 implementation and closure runs:
- strict product typecheck passed;
- Forward Task Contract validation passed;
- direct P15 unit-test suite passed;
- deterministic P15-A through P15-I evidence passed;
- upstream regression suites passed;
- dependency / waiver validation passed;
- CycloneDX SBOM generation and license validation passed;
- Trivy supply-chain scanning passed;
- reproducible clean-source build passed;
- workflow supply-chain security passed;
- promotion fail-closed verification passed;
- deterministic foundation manifest passed.

P15-I final evidence:
- implementation PR #320 = MERGED;
- implementation head = `d61909b7e1364e79aff4a15cef11a34763615f67`;
- implementation Governance = `38554807405` / SUCCESS;
- implementation artifact = `sha256:a4e15b61776aa9e7bd5eb57a603e72d1a68ecbbff1e89911de36473952470333`;
- implementation merge SHA = `6f93bf3a9d066e91af808aa348b7f6f4bf0236eb`;
- closure PR #321 = MERGED;
- closure Governance = `38555188341` / SUCCESS;
- closure artifact = `sha256:cb73c025f3592744d560a42252a32470c4cb18679e05be2fcadad317500db836`;
- closure merge SHA = `a18c582855d15f15e17a011716358f00ba4e5181`;
- validation marker = `P15_INDEPENDENT_RISK_VALIDATION / PASS`.

## Safety and authority boundaries

- P15 positive outputs are risk eligibility/candidate directives, not final pre-trade approval;
- P15-I is independent validation of P15 only and has no P16 approval authority;
- production numeric risk/leverage/allocation defaults remain unset unless explicitly governed;
- P15-H HALT_NEW_RISK does not itself liquidate or close existing positions;
- P16 remains owner of the independent Pre-Trade Risk Firewall and frozen `G8_PRETRADE_SAFE` gate;
- P20/P21 remain owners of execution and position management;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.

## Linear synchronization

P15 execution and closure evidence are synchronized through the Finance management continuation register and P15 milestone/status updates.

## Phase transition

P15 is CANONICAL_COMPLETE.

P16 remains NOT_STARTED and MUST NOT start until explicit Owner phase authorization is provided.
