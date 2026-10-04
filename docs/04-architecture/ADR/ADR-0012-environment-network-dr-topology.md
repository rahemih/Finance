# ADR-0012 — Environment Isolation, Trust Zones & Disaster Recovery Topology

Status: ACCEPTED  
Task: `FIN-P02-WG-001`

## Context

NEXUS QUANT separates research, simulation, shadow and future production authority. A shared network/credential/state plane would allow accidental privilege escalation and make recovery unsafe.

The project must remain country-neutral and cloud-portable.

## Decision

Adopt the topology defined in:

- `docs/04-architecture/ENVIRONMENT-NETWORK-DR-TOPOLOGY.md`
- `docs/04-architecture/environment-network-dr-topology.json`

### Environment isolation

DEV, TEST, RESEARCH, DEMO, SHADOW, CANARY and LIVE are distinct authority contexts.

CANARY/LIVE credentials and mutable execution state cannot be reused by lower environments.

SHADOW has no live execution command path.

### Trust zones

Use logical trust zones separating:
- user edge;
- application ingress;
- control plane;
- data plane;
- execution enclave;
- security/secrets;
- observability/audit;
- backup/DR.

Public/user traffic cannot reach Execution or Secrets directly.

Broker/exchange execution traffic originates only from the Execution Enclave.

### Cross-environment movement

Code/model/config promote as immutable artifacts and evidence.

Ambient credentials, hidden agent memory and mutable runtime state do not promote.

Production state copied downward must be explicitly sanitized and governed.

### DR

Classify recovery data into:
- DR0 execution/authority state;
- DR1 control/security state;
- DR2 market/history/research state;
- DR3 rebuildable derived state.

Recovery enters HALTED/SAFE_MODE, restores trusted control/security dependencies, reconciles external execution truth and only then permits risk-increasing execution.

A backup in the same failure domain is not full DR.

Geographic region and cloud/provider remain unspecified.

## Alternatives considered

### One shared environment with feature flags
Rejected because credentials, mutable state and execution authority require stronger isolation.

### Direct public/API access to execution components
Rejected because it expands the attack surface and bypass risk.

### DR as simple database backup
Rejected because execution recovery requires reconciliation of broker/exchange truth, not only storage restore.

### Select cloud/region now
Rejected because P02 defines logical architecture; physical implementation belongs to P04/P22.

## Consequences

Positive:
- authority isolation;
- lower accidental-live risk;
- clearer security boundaries;
- safer recovery;
- provider/cloud portability.

Negative:
- more environment/configuration discipline;
- later infrastructure implementation has additional isolation and replication cost.

## Risks / mitigations

Risk: environment drift.  
Mitigation: config-as-code, artifact promotion and P04 validation.

Risk: production credentials leak into non-production.  
Mitigation: separate secret namespaces/handles and policy checks.

Risk: recovered local state disagrees with broker.  
Mitigation: reconciliation before risk-increasing execution.

Risk: DR target shares primary failure domain.  
Mitigation: P04/P22 must validate actual failure-domain independence.

## Validation / evidence

P03 validates identity/network/secrets policy.

P04 chooses concrete infrastructure and proves environment isolation.

P22 implements backup/restore/DR drills.

P24 controls CANARY/LIVE activation.

## Rollback / supersession

Cloud, network products and physical deployment may change without superseding this ADR if logical isolation, execution enclave, recovery/reconciliation and environment authority boundaries remain.

Weakening those guarantees requires A1/A6/A8/A9/A10 review.

## Related tasks / gates

P02-G, P03, P04, P22, P24, G2, G3, G12, G13.
