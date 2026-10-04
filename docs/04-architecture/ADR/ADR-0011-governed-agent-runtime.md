# ADR-0011 — Governed Agent Runtime

Status: ACCEPTED  
Task: `FIN-P02-WF-001`

## Context

NEXUS QUANT already has canonical A0–A10 roles, specialist contracts, typed envelopes, security/memory rules and evaluation requirements.

P02-F must select a practical runtime approach without allowing an external agent framework to become the source of authority.

The project is a private <=10-user system, so framework sprawl and unnecessary distributed orchestration are explicit risks.

## Decision

Adopt:

`Project-owned Governance Kernel + PydanticAI Runtime Adapter`

PydanticAI is selected as the primary agent runtime adapter because current documentation supports:
- typed dependencies;
- structured outputs;
- model/provider abstraction;
- dynamic/filterable toolsets;
- approval-required/deferred tools;
- MCP integration;
- durable-execution integration options.

The project-owned Governance Kernel remains authoritative for:
- Task Contracts;
- locks/gates;
- A0–A10 role authority;
- A5 Risk veto;
- A8 Security veto;
- Human Gates;
- tool/resource authorization;
- budgets/circuit breakers;
- audit/evidence.

Exact runtime version/dependency pinning is deferred to P04.

## Alternatives considered

### OpenAI Agents SDK
Strong lightweight option with handoffs, guardrails, tracing, sessions and MCP approvals.

Retained as an alternative/OpenAI-specific adapter, but not primary because NEXUS QUANT prioritizes model/provider portability.

### LangGraph
Strong durable graph/checkpoint/interrupt system.

Deferred because its graph/orchestration complexity is not currently justified by the private-system scope.

### Microsoft Agent Framework
Strong workflow/checkpoint/durability and enterprise hosting options.

Deferred because the current architecture does not require its larger runtime/hosting surface.

### Fully custom agent framework
Rejected.

A custom Governance Kernel is necessary, but rebuilding model/tool/approval/runtime mechanics would create avoidable cost and risk.

## MCP decision

MCP is adopted only as a **tool/context interoperability protocol behind the Tool Gateway**.

MCP servers/tools do not grant authority.

Controls include:
- allowlists;
- filtered per-run tool exposure;
- least-privilege authorization;
- input/output validation;
- timeout/rate limits;
- approval for sensitive operations;
- audit;
- treating annotations/results as untrusted unless independently trusted.

## A2A decision

A2A is deferred.

Internal A0–A10 roles use canonical typed envelopes and project-owned routing.

A2A is reconsidered only when independently deployed/external agent services create a real network interoperability need.

## Authority model

Framework Agent objects are runtime adapters for canonical project roles.

They cannot:
- expand role permissions;
- create persistent roles;
- suppress A5/A8 veto;
- rewrite Task Contracts;
- auto-enable Live/Auto Trading;
- use tool availability as permission.

Specialist spawning is bounded:
- catalog-listed only;
- default depth 1;
- no child spawning by Specialist by default;
- child authority is a strict subset/intersection;
- TTL/token/cost/tool/wall-clock/concurrency limits required.

## State and recovery

Workflow checkpoints are not market/account/order truth.

On resume, freshness-sensitive and permission-sensitive facts are revalidated.

Side-effecting tools use idempotency-aware retry behavior; uncertain side effects are reconciled before retry.

## Human Gate

Approval is bound to exact action/scope/argument digest and expiry.

Approval cannot be reused for broader authority.

## Observability

OpenTelemetry-compatible telemetry is the canonical portability layer.

Framework-specific tracing is optional enrichment only.

A10 owns evidence integrity.  
A9 owns operational health.

## Consequences

Positive:
- typed and provider-portable runtime;
- small framework footprint;
- strong separation of deterministic authority from LLM mechanics;
- MCP integration without ambient permission;
- easy exit path if framework changes.

Negative:
- project must implement/maintain a thin Governance Kernel;
- some framework-native features cannot be trusted automatically and must pass project policy;
- checkpoint persistence still needs P04 implementation choice.

## Risks / mitigations

Risk: framework API/version changes.  
Mitigation: adapter boundary + P04 version pinning + contract tests.

Risk: dynamic toolset accidentally exposes excess capability.  
Mitigation: project Tool Gateway computes filtered effective tools independently.

Risk: model fallback changes behavior.  
Mitigation: same authority/budget/policy applies to every fallback and model identity is traced.

Risk: checkpoint resumes stale facts.  
Mitigation: mandatory resume freshness revalidation.

Risk: untrusted MCP/content changes agent behavior.  
Mitigation: Tool Gateway, provenance, content trust boundary and A8 quarantine.

## Validation / evidence

P04 must validate exact dependency/version/license and implement contract/eval tests.

P03 validates Identity/Secrets/RBAC boundaries.

P22 validates agent health/degraded/recovery behavior.

P24 retains Human Gate for Live/Auto activation.

## Rollback / supersession

PydanticAI may be replaced without changing A0–A10 authority if the replacement passes the same typed/tool/state/security/evidence contracts.

Any framework replacement requires an ADR and migration/exit test.

## Related tasks / gates

P01-WG-001, P01-WG-002, P02-F, P03, P04, P22, P24, G2, G3.
