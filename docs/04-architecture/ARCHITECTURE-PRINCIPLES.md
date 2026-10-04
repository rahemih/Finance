# NEXUS QUANT — Architecture Principles

STATE = P02-A BASELINE  
TASK = `FIN-P02-WA-001`  
PHASE = `P02 — Master Architecture`

## 1. Purpose

These principles govern every architectural decision made in P02 and later phases.

They are intentionally technology-agnostic. A library, database, cloud, broker, exchange or vendor cannot override them merely because it is convenient.

## 2. Core principles

### AP-01 — Simplicity first

NEXUS QUANT is a private system for a small team, not a public hyperscale SaaS.

Default:
- one governed repository;
- a modular core;
- the fewest runtime processes necessary;
- explicit boundaries inside the codebase before network boundaries.

A module becomes a dedicated service only when at least one of these is proven:
- independent scaling need;
- fault-isolation requirement;
- stronger security boundary;
- independently deployable integration boundary;
- materially different runtime/latency profile;
- operational ownership that justifies the extra complexity.

Microservices are not a default architecture goal.

### AP-02 — Country-neutral and provider-portable

Architecture must not depend on any assumed country/location.

Provider-specific details live behind adapters and contracts.

No provider symbol, proprietary schema, broker order ID, exchange-specific funding convention or legal entity becomes a global domain primitive.

The system must be able to replace:
- market-data provider;
- broker/exchange;
- storage backend;
- message transport;
- model/LLM provider

without rewriting the business/risk domain.

### AP-03 — Canonical domain contracts before adapters

External systems are translated at the boundary.

Canonical internal contracts own:
- instrument identity;
- timestamps;
- price/quantity precision;
- order intent;
- execution state;
- provenance;
- risk verdict;
- signal/evidence;
- audit metadata.

Adapters never leak provider-specific assumptions into downstream logic.

### AP-04 — Event time, provenance and replay are first-class

Every material market/data/decision event must preserve:
- source timestamp;
- receive timestamp;
- processing timestamp where relevant;
- provider/source identity;
- instrument canonical ID;
- sequence/gap metadata where available;
- transformation/version metadata.

The system must support deterministic replay of important decisions from versioned inputs.

### AP-05 — Raw evidence is immutable; derived state is reproducible

Raw source evidence is append-only/versioned where legally permitted.

Derived features, scores, signals and narratives must be reproducible from:
- exact source versions;
- exact code/model version;
- exact configuration;
- exact clock/replay context.

### AP-06 — Risk is an independent veto authority

Strategy, Quant, AI/LLM, Market Intelligence and Execution cannot bypass Risk.

Risk can:
- reject;
- reduce;
- halt;
- force defensive state according to policy.

Risk cannot silently increase its own ceilings.

### AP-07 — Pre-Trade Firewall is deterministic and final

Before any executable intent can reach an execution adapter, the Pre-Trade Firewall must independently verify:
- freshness;
- duplicate intent;
- size;
- leverage/exposure;
- liquidity;
- event/data/provider/system health;
- drawdown/daily-loss conditions;
- later policy-specific constraints.

Unknown critical state fails closed.

### AP-08 — Execution is deterministic, idempotent and reconcilable

An order intent is not an order acknowledgement, and an acknowledgement is not a fill.

OMS design must support:
- stable intent IDs;
- idempotency;
- duplicate prevention;
- retries with bounded semantics;
- timeout/uncertain states;
- crash recovery;
- deterministic reconciliation against broker/exchange truth.

Blind cross-broker replay is forbidden.

### AP-09 — Safety states are explicit

Runtime control uses explicit states such as:
- NORMAL;
- DEGRADED;
- SAFE_MODE;
- HALTED;
- EMERGENCY;
- RECOVERY.

Critical failures never degrade silently into a normal state.

### AP-10 — Environment separation is architectural, not cosmetic

DEV, TEST, RESEARCH, DEMO, SHADOW, CANARY and LIVE are separate security/risk contexts.

They must not casually share:
- credentials;
- writable state;
- execution authority;
- secrets;
- risk ceilings.

Promotion is evidence-driven, not config-toggle-driven.

### AP-11 — Least privilege by construction

Every human, agent, service and integration gets the minimum required authority.

Trading credentials later must be:
- trading-only where possible;
- withdrawal-disabled;
- environment-specific;
- revocable;
- auditable.

### AP-12 — Agents are bounded roles, not superusers

A0–A10 and specialist agents operate under explicit contracts.

No agent can:
- self-grant authority;
- bypass Risk;
- bypass Security;
- bypass Governance;
- self-promote a model to Live;
- create withdrawal authority.

Agent actions must be attributable and auditable.

### AP-13 — LLMs explain and assist; deterministic controls decide

LLMs may:
- research;
- summarize;
- classify;
- explain;
- generate hypotheses;
- assist workflows.

LLMs must not be the sole authority for:
- risk limits;
- order duplication control;
- account/permission changes;
- probability calibration;
- provider legal eligibility;
- execution safety.

### AP-14 — Empirical probability, not narrative probability

Any probability exposed as a trading metric must come from empirical/calibrated evidence with:
- sample size;
- calibration method;
- uncertainty;
- regime similarity;
- validation window.

Natural-language confidence is not a substitute.

### AP-15 — Data quality can stop downstream decisions

Bad/stale/unverifiable data must not be silently consumed.

Downstream components must understand:
- freshness;
- quality;
- provenance;
- confidence;
- quarantine state.

### AP-16 — Observability and evidence are part of the design

Every critical domain must expose enough telemetry to answer:
- what happened;
- when;
- why;
- with which inputs/config/version;
- who/what authorized it;
- whether recovery succeeded.

Logs alone are not sufficient; structured traces/metrics/audit evidence are required where appropriate.

### AP-17 — Recovery is designed before optimization

Every critical component must define:
- failure modes;
- retry boundaries;
- fallback behavior;
- recovery procedure;
- reconciliation;
- evidence after recovery.

Performance optimization must not remove recovery guarantees.

### AP-18 — Cost and operational complexity are explicit architecture metrics

A design that is theoretically elegant but expensive to operate is not automatically superior.

Architecture review must consider:
- monthly fixed cost;
- variable/usage cost;
- data entitlements;
- storage growth;
- observability cost;
- operator burden;
- incident complexity.

### AP-19 — Security and compliance constraints are preserved even when deferred

P01 is country-neutral, but that does not mean legal/provider constraints disappear.

Jurisdiction/client/product/account eligibility is deferred to activation-time gates and must remain represented in architecture as policy inputs.

### AP-20 — Persian UX is presentation, not domain coupling

The product UX is Persian/RTL, but internal domain contracts remain language-neutral and structured.

User-facing explanations map structured reasons into Persian.

### AP-21 — No hidden autonomous escalation

Autonomy may increase only through explicit roadmap gates.

Forbidden:
- automatic promotion from Demo/Shadow to Live;
- autonomous risk-ceiling increase;
- autonomous provider/account permission escalation;
- hidden background trading behavior.

### AP-22 — Interfaces are versioned; breaking change is explicit

Critical contracts use versioned schemas/interfaces.

Breaking changes require:
- impact review;
- migration/replay plan;
- compatibility decision;
- ADR/task evidence where material.

## 3. Architecture decision test

Before accepting an architecture choice, A1/A10 must be able to answer:

1. Does it preserve provider portability?
2. Does it preserve deterministic replay?
3. Does it preserve Risk independence?
4. Does it preserve fail-closed behavior?
5. Does it minimize operational complexity for the actual scale?
6. Can it be tested without Live capital?
7. Can it be recovered/reconciled after a crash or outage?
8. Does it avoid hidden country/location assumptions?
9. Can its critical behavior be audited?
10. Is there a simpler design that meets the same requirements?

If the final answer to #10 is yes, the simpler design is preferred unless evidence justifies otherwise.

## 4. P02 downstream use

These principles are mandatory inputs to:
- P02-B domain boundaries;
- P02-C data architecture;
- P02-D intelligence architecture;
- P02-E risk/execution architecture;
- P02-F agent architecture;
- P02-G network/environment/DR;
- P02-H capacity/cost;
- P02-I architecture freeze.

No later P02 workstream may silently contradict them.
