# NEXUS QUANT — Domain / Module Boundaries

STATE = P02-B BASELINE  
TASK = `FIN-P02-WB-001`  
PHASE = `P02 — Master Architecture`

## 1. Objective

Define logical ownership and dependency boundaries before selecting physical deployment topology.

This document answers:
- which domain owns which state;
- which domain may call/read another;
- which dependencies are forbidden;
- which modules are candidates for physical process isolation later.

It does **not** mean every domain becomes a microservice.

## 2. Primary decision path

The main market-to-execution path is:

`Provider → Adapter → Canonical Market Data → Data Quality → Feature/Evidence → Intelligence + Quant → Signal/Probability → Risk → Pre-Trade Firewall → Execution/OMS`

No component may skip forward across safety boundaries.

In particular:

`Strategy / Signal → Execution` directly is forbidden.

## 3. Domain map

### D01 — Instrument & Reference Data
Owner: **A2**

Owns:
- canonical instrument IDs;
- provider/venue aliases;
- precision and contract metadata;
- calendars/reference metadata.

Does not own:
- signals;
- risk;
- orders.

### D02 — Market Data Adapters
Owner: **A2**

Owns:
- provider-native streaming/API translation;
- reconnect/heartbeat boundary;
- provider-health events.

Provider SDK/schema ends here.

### D03 — Canonical Market/Event Stream
Owner: **A2**

Owns:
- canonical timestamps;
- provider provenance;
- canonical instrument identity;
- sequence/gap metadata;
- normalized units.

### D04 — Raw / Historical Data
Owner: **A2**

Owns:
- immutable/versioned raw evidence;
- historical snapshots;
- replay sources.

### D05 — Data Quality & Provenance
Owner: **A2**

Owns:
- freshness;
- completeness;
- duplicate/outlier/sequence checks;
- cross-provider validation;
- provenance/confidence;
- quarantine.

Critical quarantined data cannot be treated as valid downstream.

### D06 — Feature / Evidence Foundation
Owner: **A2**  
Co-owner: **A4**

Owns:
- derived feature versions;
- evidence inputs;
- deterministic feature regeneration.

### D07 — Market Intelligence
Owner: **A3**

Owns:
- technical evidence;
- macro/event evidence;
- order-flow evidence;
- news/sentiment evidence;
- market memory/regime/narrative evidence.

Cannot send broker orders.

### D08 — Quant / Strategy
Owner: **A4**

Owns:
- strategies;
- models;
- backtest artifacts;
- empirical validation;
- candidate model versions.

Cannot self-promote to Live.

### D09 — Signal / Probability / Explainability
Owner: **A3**  
Co-owner: **A4**

Owns:
- LONG / SHORT / WAIT / NO_TRADE candidate;
- calibrated probability;
- structured reasons;
- uncertainty.

LLM confidence is not accepted as calibrated probability.

### D10 — Portfolio / Risk Engine
Owner: **A5**

Owns:
- sizing;
- exposure;
- leverage;
- drawdown;
- portfolio and counterparty limits;
- independent veto.

Risk cannot raise its own ceilings without governed policy change.

### D11 — Pre-Trade Firewall
Owner: **A5**

Owns the final deterministic executable-intent safety verdict.

Unknown critical state = fail closed.

### D12 — Execution / OMS / Reconciliation
Owner: **A6**

Owns:
- approved intent execution;
- order lifecycle;
- idempotency;
- retries/timeouts;
- fills;
- positions;
- reconciliation.

Cannot override Risk/Firewall.

### D13 — Learning / Experimentation
Owner: **A7**

Owns:
- experiments;
- retraining;
- champion/challenger evidence;
- drift;
- candidate model versions.

Can only emit promotion proposals.  
Auto-Promote-to-Live is forbidden.

### D14 — Security / Identity / Secrets
Owner: **A8**

Owns:
- authorization context;
- MFA/RBAC policy;
- secret handles;
- credential policy;
- security events.

Raw secrets must not leak into ordinary domain state.

### D15 — Operations / Observability / Recovery
Owner: **A9**

Owns:
- health;
- telemetry;
- incidents;
- SLOs;
- backup/restore evidence;
- operational recovery state.

Operations may request halt/safe mode, but may not silently change risk policy.

### D16 — Agent Control Plane
Owner: **A0**

Owns:
- A0–A10 routing;
- specialist spawning;
- tool scopes;
- handoffs;
- agent health;
- escalation envelopes.

Agents access domains through governed APIs/contracts rather than direct DB/provider access.

### D17 — Evidence / Audit
Owner: **A10**

Owns:
- append-only audit events;
- evidence manifests;
- closure evidence;
- decision traceability.

Audit can verify but does not make trading decisions.

### D18 — Application API / Persian UX / Notifications
Architecture owner: **A1**  
Final product/UX ownership resolved later in P23.

Owns:
- user commands;
- read models;
- Persian/RTL presentation;
- approvals;
- annotations/team collaboration;
- notification preferences.

Cannot connect directly to providers/brokers or secrets.

## 4. Feedback paths

The primary decision graph is directional, but safe feedback exists through events:

- Execution/OMS emits fill/position events to Risk.
- Operations publishes system/provider health to Risk, Firewall and Execution.
- Learning reads historical/replay/audit evidence and outputs only candidate artifacts.
- Audit receives evidence from all domains but has no command authority.

This avoids unsafe synchronous cycles while preserving required state feedback.

## 5. Forbidden couplings

The following are architecture violations:

- Strategy/Quant/Signal directly sends an order to broker/exchange.
- Execution overrides a Risk or Firewall rejection.
- Learning activates a Live model by itself.
- Agent runtime directly mutates broker/provider state outside domain APIs.
- UX talks directly to broker/provider.
- Provider SDK is imported into core Intelligence/Risk/Strategy domain.
- Operations silently edits risk ceilings.
- LLM narrative becomes probability without empirical calibration.
- One domain writes another domain's authoritative state directly.

## 6. Ownership rule

**Only the owning domain mutates its authoritative state.**

Other domains may:
- query through contracts;
- subscribe to events;
- consume replicated read models.

They do not gain ownership.

## 7. Physical extraction candidates

Logical boundaries do not force physical services.

### Strong dedicated-process candidates

**Market Data Adapters**
- continuous streaming;
- reconnect/backpressure;
- provider outage isolation.

**Execution / OMS**
- credentials;
- crash/reconciliation isolation;
- security boundary.

**Agent Control Plane**
- LLM/tool attack surface;
- independent permissions/quarantine.

**Application API / UX**
- user/network attack surface;
- independent deployability.

### Conditional extraction

**Risk + Pre-Trade Firewall**

Must be logically independent now.  
Physical isolation is decided in P02-E/G based on latency, fault isolation and operational evidence.

### Modular core + workers

**Intelligence / Quant / Signal**

Default to logical modules plus controlled workers/jobs where CPU/batch workloads justify them.

## 8. Cross-domain contract families

P02-B reserves these contract families for later detailed schema definition:

- `InstrumentDefinition`
- `CanonicalMarketEvent`
- `QualityVerdict`
- `FeatureValue / EvidenceInput`
- `IntelligenceEvidence`
- `StrategyEvidence`
- `SignalCandidate`
- `ProbabilityEstimate`
- `RiskVerdict`
- `FirewallVerdict`
- `ApprovedTradeIntent`
- `OrderStateEvent`
- `FillEvent`
- `PositionStateEvent`
- `ExperimentArtifact`
- `SecurityContext`
- `SystemHealthView`
- `AuditEvent`
- `AgentTaskEnvelope`
- `UserCommand`

Exact schemas belong to P02-C/D/E/F and later implementation phases.

## 9. Dependency policy

Rules:

1. External provider details stop at adapters.
2. Shared DB tables are not used as hidden cross-domain APIs.
3. Cross-domain writes use explicit command/event contracts.
4. Material commands/events carry correlation/audit IDs.
5. Read models may be replicated without transferring state ownership.
6. Country/location is never embedded as a domain dependency.
7. Production eligibility remains a policy input applied later, not a structural assumption.

## 10. P02 downstream implications

P02-C must design data ownership around D01–D06 and replay/audit needs.

P02-D must design Intelligence/Quant/Signal interactions without bypassing D05 quality.

P02-E must preserve strict D10 → D11 → D12 authority sequence.

P02-F must map agent tools to domain APIs.

P02-G must decide physical isolation for strong candidates.

P02-H must size each boundary based on event rates, retention and workloads.

P02-I must reject any architecture that violates these boundaries.
