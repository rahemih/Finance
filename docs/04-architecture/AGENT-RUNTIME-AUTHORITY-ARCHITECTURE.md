# NEXUS QUANT — Agent Runtime & Authority Architecture

STATE = P02-F BASELINE  
TASK = `FIN-P02-WF-001`  
PHASE = `P02 — Master Architecture`

## 1. Objective

Turn the already-canonical A0–A10 contracts into a runtime architecture without allowing any agent framework to redefine project authority.

The central rule is:

> Framework mechanics are replaceable. Governance, Risk, Security and Audit authority are not.

## 2. Primary runtime decision

Selected architecture:

`Project Governance Kernel + PydanticAI Runtime Adapter`

PydanticAI is selected as the **primary runtime adapter**, not as the governance system.

Why:
- typed dependencies and outputs;
- provider/model abstraction;
- dynamic/filterable toolsets;
- approval-required/deferred tools;
- MCP support;
- durable-execution integration options;
- Python-first typed development;
- good fit for a small private system without forcing a large graph/runtime platform.

Exact version pinning and installation are deferred to P04.

## 3. Rejected / deferred alternatives

### OpenAI Agents SDK
Status: retained alternative / OpenAI-specific adapter.

Strengths:
- lightweight;
- handoffs;
- guardrails;
- sessions;
- tracing;
- MCP approvals.

Not selected as primary because the architecture prioritizes model/provider portability and framework-neutral authority.

### LangGraph
Status: deferred optional complex-workflow engine.

Strengths:
- durable graph state;
- checkpoints;
- interrupts;
- human-in-loop;
- subgraphs.

Not selected now because current scope does not justify the additional orchestration complexity.

### Microsoft Agent Framework
Status: deferred enterprise alternative.

Strengths:
- workflows;
- checkpoint/resume;
- human-in-loop;
- durable execution;
- self-hosting.

Not selected because its runtime/hosting surface is larger than the current private-system requirement.

### Fully custom agent framework
Status: rejected as primary runtime.

A small **custom Governance Kernel** is required, but rebuilding model/tool/approval/runtime mechanics from zero would create unnecessary implementation burden.

## 4. Governance Kernel

Owner: **A0**

The Governance Kernel is deterministic project-owned code.

Responsibilities:
- load active Task Contract;
- validate task/lock/gate state;
- resolve agent/specialist contract;
- calculate effective capabilities;
- authorize tool/resource actions;
- enforce time/token/cost/retry/concurrency limits;
- enforce A5/A8 veto state;
- create Human Gate requests;
- coordinate checkpoint/resume validation;
- emit trace/evidence metadata.

A0 can route.

A0 cannot override:
- A5 Risk veto;
- A8 Security veto;
- Owner/Human Gate;
- Task Contract;
- protected governance rules.

## 5. Runtime Adapter

PydanticAI handles:
- model calls;
- typed structured output;
- dependency injection;
- toolset registration;
- deferred/approval tool mechanics;
- model fallback mechanics where policy permits.

It does not decide authorization.

## 6. Tool Gateway

Owners: **A8 + A0**

Every tool/plugin/MCP call passes an authorization pipeline.

Before tool execution:

1. active governed Task Contract;
2. valid task state/lock;
3. agent role permits capability;
4. specialist contract permits capability;
5. tool/plugin is allowed;
6. resource/path/domain is in scope;
7. environment/gate permits action;
8. required Human Gate matches exact action;
9. A8 Security permits action;
10. A5 Risk permits financial/action path where applicable;
11. cost/time/rate/circuit budgets permit action.

After tool execution:
- validate output schema;
- attach provenance;
- scan untrusted content;
- redact sensitive output;
- record audit/trace;
- update budgets/retries/health.

**Tool availability is not permission.**

## 7. Canonical agent authority

A0 — Governance / Orchestrator  
A1 — Architecture  
A2 — Data  
A3 — Market Intelligence  
A4 — Quant  
A5 — Risk  
A6 — Execution  
A7 — Learning  
A8 — Security  
A9 — Operations  
A10 — Evidence / Audit

Framework Agent objects are adapters for these roles.

They are not new identities with broader authority.

## 8. Agent health states

Role health:
- READY
- DEGRADED
- PAUSED
- QUARANTINED
- RETIRED

Run states:
- CREATED
- RUNNING
- WAITING_TOOL
- WAITING_HUMAN
- WAITING_DEPENDENCY
- DEGRADED
- VETOED
- BLOCKED
- COMPLETED
- FAILED
- CANCELED

## 9. Specialist lifecycle

Only:
- A0; or
- an explicitly authorized core parent

may spawn a Specialist.

Rules:
- Specialist must exist in canonical catalog.
- Authority = intersection of Task + parent + Specialist contract + Tool policy.
- Default max spawn depth = **1**.
- Specialist may not spawn children by default.
- Specialist is ephemeral by default.
- TTL, turns, tool calls, token/cost and wall-clock budget are mandatory.

Termination occurs on:
- deliverable returned;
- scope expiry;
- timeout/budget;
- parent cancel;
- A5/A8 veto;
- missing required evidence;
- Security quarantine.

## 10. Typed handoffs

Production-relevant handoffs use the canonical Agent Message Envelope or a typed domain-specific superset.

Natural-language text alone is insufficient for material actions.

Envelope propagates:
- run/task/agent identity;
- source/evidence refs;
- as-of/freshness;
- assumptions;
- supporting/opposing evidence;
- conflicts;
- uncertainty;
- risk flags;
- action class;
- tool trace;
- limitations.

## 11. State and memory

Four categories:

### Ephemeral Working Memory
Current run reasoning/context.

### Workflow Checkpoint
Only state required to resume the workflow correctly.

### Governed Evidence History
Auditable evidence and result references.

### User Preference Context
UX/workflow preferences only.

Memory is not market truth.

The following are always re-read from canonical deterministic services when material:
- market price;
- account balance;
- position;
- order/fill state;
- risk limits;
- credential permissions.

## 12. Checkpoint / resume

Checkpoint may include:
- run/task/agent identity;
- workflow step;
- pending tool/approval IDs;
- evidence references;
- budget/retry/circuit counters;
- model/tool trace refs.

Checkpoint excludes:
- raw secrets;
- assumed account/market truth;
- unnecessary unbounded chat history;
- provider credentials.

On resume, revalidate:
- task/lock/gates;
- tool permissions;
- A5/A8 veto state;
- freshness-sensitive data;
- account/order/risk truth if relevant;
- tool/model availability;
- Human Gate validity.

Corrupt or untrusted checkpoint = fail closed.

Checkpoint backend selection is deferred to P04.

## 13. Risk / Security veto

A5 and A8 vetoes are deterministic external gates.

No:
- majority vote;
- agent consensus;
- A0 routing;
- model fallback;
- Human-readable reasoning

can suppress an active veto.

## 14. Human Gate

A Human Gate request contains:
- approval ID;
- task/run/agent;
- exact action/tool;
- normalized argument digest;
- resource/environment scope;
- evidence refs;
- Risk/Security flags;
- rollback/stop controls;
- expiry.

Approval is bound to exact action.

Changing scope/arguments requires new approval.

Expired/denied approval fails closed.

## 15. MCP

Decision:

`MCP = ADOPTED AS TOOL/CONTEXT PROTOCOL BEHIND TOOL GATEWAY`

Rules:
- allowlisted servers;
- filtered tool list per run;
- descriptions/annotations treated as untrusted unless server trusted;
- input/output validation;
- least-privilege authorization scopes;
- resource/audience validation;
- sensitive-operation approval;
- timeouts/rate limits;
- audit;
- tool output treated as untrusted until validated.

MCP does not grant authority.

## 16. A2A

Decision:

`A2A = DEFERRED`

Reason:

A0–A10 are internal roles inside one governed system. They do not need public/network agent discovery now.

Reconsider A2A only for:
- independently deployed external agent services;
- cross-organization integration;
- real need for Agent Card / network task lifecycle.

## 17. Untrusted content / prompt injection

External:
- web;
- news;
- email;
- social;
- PDFs;
- filings;
- third-party prompts;
- untrusted repo text;
- MCP descriptions/results

are data.

They cannot change:
- system policy;
- Task Contract;
- tool permission;
- agent authority;
- Risk/Security rules.

Suspicious content can trigger A8 quarantine.

## 18. Quarantine

Triggers include:
- prompt-injection indicators;
- repeated forbidden tool attempts;
- schema violations;
- permission mismatch;
- corrupted checkpoint;
- provenance loss;
- secret exposure;
- repeated model/tool failure beyond circuit threshold.

Quarantine:
- disables writes/sensitive tools;
- preserves trace/evidence;
- routes to A8/A9/A10;
- requires explicit clearance before READY.

## 19. Observability and budgets

Canonical telemetry is OpenTelemetry-compatible.

Trace dimensions:
- task/run;
- parent/child;
- model/provider;
- prompt/template version;
- tools;
- handoffs;
- approvals;
- vetoes;
- latency;
- token/cost;
- retries;
- errors;
- terminal state.

Framework-specific tracing may enrich but cannot be the only audit source.

Every Agent Contract has:
- max turns;
- max tool calls;
- max wall-clock;
- token budget;
- cost budget;
- concurrency limit;
- retry limit;
- circuit threshold.

Exceeding budget enters DEGRADED/BLOCKED rather than looping indefinitely.

## 20. Model routing

Model selection is based on:
- capability;
- quality;
- latency;
- cost;
- availability;
- provider policy.

Model fallback never expands authority.

Different models/personas are not automatically independent evidence.

## 21. P04 handoff

P04 must:
- pin exact PydanticAI version/license;
- pin Python/runtime dependencies;
- implement Governance Kernel interfaces;
- select checkpoint backend;
- implement Tool Gateway/MCP policy;
- wire OTel + Evidence sink;
- build evaluation/red-team harness.

Do not install LangGraph, Microsoft Agent Framework or OpenAI Agents SDK unless a later bounded Task proves a need.

## 22. Safety

Runtime dependency installation = NOT_PERFORMED  
New permissions = NONE  
Accounts/credentials = NONE  
Live Trading = DISABLED  
Auto Trading = DISABLED
