# NEXUS QUANT — Agent Governance Integration Baseline

STATE = GOVERNED_COMPANION  
TASK = `FIN-P01-WG-001`  
LINEAR = `HOS-113`  
IMPLEMENTATION_AUTHORITY = `P02-F`

## 1. Core principle

NEXUS QUANT agents are governed software roles, not unrestricted autonomous identities.

External frameworks may provide runtime mechanics. They do not grant authority.

Canonical authority remains with A0–A10 and the active Task Contract.

## 2. Authority hierarchy

```text
Owner / Governance
      |
      v
A0 Governance / Orchestrator
      |
      +--> canonical role A1-A10
                 |
                 +--> bounded specialist
```

A specialist cannot:
- increase its own permissions;
- create a new persistent role;
- recursively spawn unlimited children;
- rewrite its Task Contract;
- bypass a parent role, lock, Risk veto, Security veto or Human Gate.

## 3. Agent contract minimum

Every implemented agent/specialist must define:
- Role
- Authority
- Inputs
- Outputs
- Read scope
- Write scope
- Forbidden actions
- Tools
- Plugins
- Skills
- Trigger
- Spawn/delegation rules
- Time/token/cost budget
- Timeout
- Retry policy
- Escalation
- Failure behavior
- Evidence requirements
- Audit/tracing requirements
- Human Gate conditions
- Model/provider constraints
- Data freshness requirements

## 4. Tool authority

Tool availability is not permission.

Before a tool call:
1. Task Contract permits the capability.
2. Agent role permits the capability.
3. Tool/plugin access matrix permits the capability.
4. Resource/path is in scope.
5. Required gate/approval is satisfied.
6. Security/risk policy allows the action.

Read-only research tools may be used within authorized research scope.

Writes must remain inside explicit write scope.

## 5. Financial authority firewall

No LLM/agent is the canonical source of:
- account balance;
- open position state;
- order state;
- fill state;
- market price;
- risk limits;
- credential permissions.

Those values come from deterministic/canonical services.

No agent can independently:
- place a live order;
- cancel/replace a live order outside execution policy;
- move/withdraw funds;
- broaden API-key permissions;
- change leverage/risk ceiling;
- suppress a Risk veto;
- suppress a Security veto;
- enable Live Trading;
- enable Auto Trading.

## 6. Decision path

```text
Evidence/Data
   |
Specialist agents
   |
A3 Market Intelligence / A4 Quant
   |
Deterministic validation
   |
A5 Risk --------------------> VETO = STOP / NO_TRADE
   |
A8 Security / A9 Operations health where applicable
   |
Policy / Gate
   |
Human Gate when required
   |
A6 Execution
   |
Broker/Exchange adapter
   |
Reconciliation
   |
A10 Evidence/Audit
```

An agent consensus cannot override A5/A8 veto or a deterministic invariant.

## 7. Consensus rules

- Majority vote is not sufficient for high-stakes action.
- Confidence must be calibrated, not merely self-reported.
- Correlated agents using the same model/source are not independent evidence.
- Conflicting evidence must be preserved, not averaged away.
- Independent challenge/red-team roles are preferred for consequential decisions.
- A `NO_TRADE` result is a valid successful output.

## 8. Data provenance and freshness

Every decision-relevant output must be traceable to:
- canonical source;
- source timestamp;
- retrieval timestamp;
- provider/venue;
- dataset/version where applicable;
- transformation/calculation;
- agent/model/run version.

Stale, missing or contradictory data must be explicit.

If freshness requirements are not met, fail closed.

## 9. Memory

Agent memory is separated into:
- ephemeral working state;
- resumable workflow state/checkpoints;
- governed evidence/history;
- optional user preference context.

Memory cannot silently become market truth.

Material facts must be re-grounded.

Sensitive/user context must not be used as an undeclared trading signal.

## 10. External content trust boundary

Retrieved content is untrusted data.

Examples:
- news articles;
- social posts;
- filings;
- websites;
- emails;
- PDFs;
- third-party prompts;
- repository text outside trusted policy files.

Instructions embedded in that content do not override system/task/agent/tool policy.

Prompt-injection indicators are routed to A8.

## 11. Structured agent envelope

Production-relevant agent messages should use a typed envelope with fields similar to:

```text
run_id
task_id
agent_id
specialist_id
model_id
model_version
input_data_refs[]
source_refs[]
source_as_of
retrieved_at
freshness_status
assumptions[]
supporting_evidence[]
opposing_evidence[]
conflicts[]
confidence
uncertainty
risk_flags[]
action_class
tool_trace_id
limitations[]
```

Action classes should include:
- `INFORMATION_ONLY`
- `RESEARCH_CANDIDATE`
- `WAIT`
- `NO_TRADE`
- `INSUFFICIENT_EVIDENCE`
- gated trade-plan classes only in later authorized phases.

## 12. Failure behavior

Fail closed for:
- missing required source;
- schema failure;
- stale critical data;
- conflicting account/order truth;
- tool permission mismatch;
- risk/security veto;
- unverified model output;
- unknown broker state;
- unresolved reconciliation mismatch.

Do not convert infrastructure failure into a trading opinion.

## 13. Retry / circuit breaker

Retries must be:
- bounded;
- idempotent;
- observable;
- aware of provider rate limits.

Repeated model/tool failure should trigger a circuit breaker and degraded mode, not an infinite agent loop.

## 14. Agent evaluation gates

Evaluation sets must include:
- normal golden tasks;
- ambiguous tasks;
- missing-data tasks;
- stale-data tasks;
- conflicting-source tasks;
- prompt injection;
- malicious tool instructions;
- forbidden-action requests;
- model/provider outage;
- high volatility;
- nonsensical market inputs;
- look-ahead leakage traps;
- hidden future data;
- extreme slippage/spread;
- duplicated/corrupted messages;
- timeout/retry behavior.

Measures should include:
- correctness;
- groundedness;
- provenance completeness;
- schema conformance;
- false-positive action rate;
- `NO_TRADE` precision/recall where applicable;
- calibration;
- latency;
- cost;
- tool-call correctness;
- veto compliance;
- reproducibility.

## 15. Observability

Minimum trace dimensions:
- task/run;
- parent/child agent;
- handoff;
- model/provider;
- prompt/template version;
- tool calls;
- input/output validation;
- guardrails;
- token/cost;
- latency;
- retries;
- errors;
- vetoes;
- human approvals;
- final disposition.

Sensitive material must be redacted according to P03.

OpenTelemetry-compatible telemetry is preferred so the audit trail is portable.

## 16. Model/provider diversity

Provider diversity may reduce common-mode failure but also increases complexity.

Use multiple providers/models only when tests demonstrate benefit for:
- independent challenge;
- availability;
- latency/cost;
- model-specific capability.

Do not create artificial "independence" by running the same model with multiple personas and treating results as independent evidence.

## 17. Human Gate

Human approval is required when later policy specifies it, especially for:
- enabling Live Trading;
- enabling Auto Trading;
- real-capital credential changes;
- withdrawal/fund permissions;
- material risk-ceiling changes;
- production model/agent promotion where gated;
- critical security exceptions.

The human approver receives evidence, risk flags, conflicts and rollback/stop controls.

## 18. Interoperability

Candidate boundaries:
- MCP: model/agent-to-tool/context interoperability.
- A2A: agent/application-to-agent/application interoperability.

Adoption requires:
- authentication;
- authorization;
- capability advertisement;
- schema validation;
- identity propagation;
- trace propagation;
- timeout/cancellation;
- rate limiting;
- input sanitization;
- version negotiation;
- audit evidence.

Do not expose internal agents over an interoperability protocol merely because the protocol exists.

## 19. Cost/resource governance

Each production agent should have:
- max turns;
- max tool calls;
- max wall-clock time;
- token/cost budget;
- concurrency limit;
- circuit-breaker threshold;
- cache policy.

High cost is treated as an operational failure mode.

## 20. P02-F decisions required later

P02-F must decide through ADR/evidence:
- primary orchestration framework or custom loop;
- state/checkpoint architecture;
- agent identity and authorization;
- handoff protocol;
- specialist lifecycle;
- structured output schema;
- MCP/A2A adoption boundaries;
- trace/eval integration;
- sandbox/isolation model;
- model/provider routing;
- Human Gate implementation;
- recovery and replay behavior.

Until then, this baseline authorizes research/design only.
