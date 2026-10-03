# Finance / NEXUS QUANT — Master Roadmap Details

STATE = GOVERNED_COMPANION  
BASELINE = `docs/01-roadmap/MASTER-ROADMAP-v2.0.md`  
BASELINE_STATE = FROZEN  
DIRECT_BASELINE_MUTATION = FORBIDDEN  
TASK = `FIN-P00-WE-001`  
LIVE_TRADING = DISABLED  
AUTO_TRADING = DISABLED

## 1. Purpose and authority

This document is the detailed companion to Master Roadmap v2.0. It expands the frozen phase definitions into implementation-ready scope, outputs, validation classes, evidence expectations, primary agent ownership and exit criteria.

It does **not** replace or mutate the frozen Master Roadmap. If this companion conflicts with the frozen baseline, the frozen baseline wins until an approved ERRATA, ADR, RFC or ROADMAP ADDENDUM resolves the conflict.

The execution sequence and workstream identifiers are defined in `EXECUTION-ROADMAP.md`.

## 2. Cross-cutting invariants

These rules apply to every phase and every workstream:

- GitHub `main` + merged commit + CI evidence is the technical source of truth.
- Linear coordinates work but cannot override canonical GitHub evidence.
- Every governed implementation task requires a Task Contract, Fresh Live Guard, dependency check and lock check.
- Secrets never enter source control, Linear descriptions, evidence comments or model prompts.
- AI/LLM output is never sole authority for a live order.
- Data uncertainty, execution uncertainty or safety uncertainty must fail closed at the relevant gate.
- Risk Engine and Pre-Trade Firewall retain independent veto.
- Correlated indicators cannot be counted as independent confirmations.
- Auto-retrain may be allowed later; automatic promotion to Live is forbidden.
- Research → Backtest → Demo → Shadow → Manual/Semi-Auto → Micro-Capital/Canary → Controlled Auto cannot be skipped.
- Every material market decision must be reproducible from data/model/strategy/policy/config/code versions.
- Provider, framework and hosting names in roadmap documents are candidates unless a later governed architecture/provider task explicitly selects them.
- Private owner/team use is the baseline; public SaaS, marketplace and copy-trading are out of scope unless introduced by later governance.

## 3. Standard phase template

Every phase must eventually have:

1. objective and business/safety rationale;
2. explicit in-scope and out-of-scope boundaries;
3. upstream dependencies and required gates;
4. phase workstreams and task decomposition;
5. expected contracts/interfaces/data schemas;
6. candidate technology/provider evaluation where relevant;
7. security, risk and operational controls;
8. test and evidence plan;
9. rollback/recovery plan where runtime behavior exists;
10. closure evidence and next-phase handoff.

---

## P00 — Charter & Governance

**Objective:** create the control plane that makes all later work auditable, reproducible and safe.

**Workstreams**
- **P00-A — Charter & Source of Truth:** project identity, mission, priorities, environment names, canonical branch, source-of-truth hierarchy.
- **P00-B — Repository Governance & Branch Hygiene:** protected `main`, squash-only policy, required checks, branch naming, safe merged-branch cleanup.
- **P00-C — Project Management:** Linear project, project lead, operational PM, phase milestones, GitHub↔Linear reconciliation policy.
- **P00-D — Toolchain Governance:** Plugin/Skill/Access Matrix, least privilege, agent-to-tool boundaries, runtime separation.
- **P00-E — Detailed & Execution Roadmap:** this companion package, workstream map, dependencies, gates, provider/technology candidate matrix and test/evidence map.
- **P00-F — Governance Closure:** audit P00 artifacts, resolve drift, verify no active locks, satisfy `G0_GOVERNANCE_READY`.

**Primary agents:** A0, A8, A10; A1 consults on future architecture boundaries.

**Outputs:** Charter, Governance, Current State, Task Catalog, Agent Registry, Toolchain Matrix, detailed roadmap package, lock/evidence conventions.

**Validation:** schema validation, governance CI, protected-branch behavior, source-of-truth reconciliation, no-secret checks.

**Exit:** `G0_GOVERNANCE_READY` with all P00 task locks released and no contradictory GitHub/Linear state.

---

## P01 — Market / Provider / Compliance Research

**Objective:** define what can legally, reliably and economically be observed and later traded.

**Workstreams**
- **P01-A — Universe & Instrument Taxonomy:** Crypto spot/perpetual/futures candidates, Forex pairs, context-market symbols, venue/instrument metadata.
- **P01-B — Market Data Provider Inventory:** real-time/historical depth, rate limits, timestamps, coverage, redistribution rights, SLAs.
- **P01-C — Broker / Exchange Inventory:** order types, sandbox/demo support, API stability, regional availability, rate limits, margin/leverage, reconciliation support.
- **P01-D — Jurisdiction & Compliance:** geographic restrictions, account eligibility, data licensing, execution limitations, retention obligations.
- **P01-E — Cost / Licensing / Data Rights:** fixed/usage fees, exchange fees, professional/non-professional status, redistribution constraints.
- **P01-F — Primary / Backup Provider Strategy:** provider independence, fallback paths, cross-provider validation feasibility.
- **P01-G — Provider Baseline Decision:** evidence-backed shortlist and rejection reasons; no credentials are provisioned yet.

**Primary agents:** A1, A2, A3, A5, A8, A10.

**Mandatory research:** official provider/exchange/broker/legal documentation first; external research tools are supporting evidence only.

**Outputs:** universe registry draft, provider scorecards, compliance matrix, cost model, fallback design assumptions.

**Validation:** source freshness, jurisdiction labeling, licensing evidence, rate-limit checks, test/sandbox availability.

**Exit:** `G1_PROVIDER_BASELINE`.

---

## P02 — Master Architecture

**Objective:** freeze an architecture that is modular, testable, recoverable and proportionate to the private ≤10-user scope.

**Workstreams**
- **P02-A — Architecture Principles & ADR Set:** simplicity-first, modular core, dedicated critical services only where isolation is justified.
- **P02-B — Domain Boundaries:** ingestion, storage, feature/data quality, intelligence, signals, risk, execution, learning, operations, UX.
- **P02-C — Data Architecture:** event schemas, time-series/history, raw archive, feature store, provenance, replay.
- **P02-D — Analysis Architecture:** independent evidence families, macro/news/order-flow pipelines, market memory, probability and explanation.
- **P02-E — Risk & Execution Architecture:** independent Risk Engine, Pre-Trade Firewall, OMS, reconciliation, kill switches.
- **P02-F — Agent Architecture:** A0–A10 interfaces, specialist spawning, permissions, audit and failure behavior.
- **P02-G — Network / Environment / DR Topology:** DEV, TEST, RESEARCH, DEMO, SHADOW, CANARY, LIVE isolation.
- **P02-H — Capacity & Cost Envelope:** expected instruments, event rates, storage growth, latency classes, retention.
- **P02-I — Architecture Freeze:** ADR review and interface freeze.

**Primary agents:** A1 lead; A2, A4, A5, A6, A8, A9 consulted; A10 audits.

**Outputs:** architecture diagrams, ADRs, interface contracts, service/data ownership, environment topology, capacity assumptions.

**Validation:** threat/risk review, failure-mode review, replayability, provider portability, operational complexity review.

**Exit:** `G2_ARCHITECTURE_FREEZE`.

---

## P03 — Security & Identity

**Objective:** establish least-privilege identity, secret, administrative and audit controls before sensitive runtime integration.

**Workstreams**
- **P03-A — Threat Model:** assets, actors, attack surfaces, abuse cases, supply-chain risks, broker/exchange credential risks.
- **P03-B — Identity / MFA / RBAC:** owner/admin/operator/researcher/viewer roles; session and device policy.
- **P03-C — Secrets & Key Management:** vault/KMS strategy, rotation, environment separation, no withdrawal permission.
- **P03-D — Private Administration:** VPN/private access where justified, trusted devices, administrative exposure minimization.
- **P03-E — Audit & Change Integrity:** tamper-evident logs, high-risk change attribution, maker/checker where required.
- **P03-F — Supply Chain Security:** dependency policy, secret scanning, SBOM hooks, signed artifacts/attestation decision.
- **P03-G — Incident / Emergency Access:** credential compromise procedures, revocation, emergency halt.
- **P03-H — Security Baseline Closure:** independent A8 verification.

**Primary agents:** A8 lead; A1/A9 support; A10 evidence; A5 consulted on trading credential/risk boundaries.

**Validation:** security tests, access-review scenarios, secret-leak drill, revoked-credential test, audit completeness.

**Exit:** `G3_SECURITY_BASELINE`.

---

## P04 — Engineering Foundation

**Objective:** create reproducible engineering foundations before market-system implementation.

**Workstreams**
- **P04-A — Repository / Workspace Structure:** monorepo or governed multi-package structure selected by P02.
- **P04-B — Language / Runtime / Dependency Baseline:** exact versions, lockfiles, upgrade policy, reproducible local environment.
- **P04-C — CI/CD Foundation:** lint, typecheck, unit, contract, security, build, artifact and environment promotion gates.
- **P04-D — Config / Environment Contract:** config-as-code; secret references only; environment-specific overrides.
- **P04-E — Test Harness:** fixtures, mocks, simulators, deterministic clocks, replay hooks.
- **P04-F — Dependency / License / SBOM Governance:** allowed licenses, CVE policy, dependency bot strategy.
- **P04-G — Developer Tooling:** local bootstrap, formatting, pre-commit/pre-push choices, debugging.
- **P04-H — Reproducible Build Evidence:** clean-machine build and rollback-ready artifacts.

**Primary agents:** A1, A8, A9, A10.

**Exit evidence:** deterministic build, CI required checks, environment bootstrap and dependency inventory.

---

## P05 — Real-Time Data

**Objective:** ingest trustworthy, time-aligned market data continuously with measurable latency and failure behavior.

**Workstreams**
- **P05-A — Crypto Real-Time Adapters**
- **P05-B — Forex Real-Time Adapters**
- **P05-C — Context-Market Adapters**
- **P05-D — Canonical Normalization / Symbol Master / Clock Model**
- **P05-E — Streaming / Heartbeat / Backpressure**
- **P05-F — Reconnect / Failover / Gap Recovery**
- **P05-G — Latency / Throughput / Soak Validation**
- **P05-H — Real-Time Data Gate Closure**

**Key outputs:** normalized tick/trade/book/bar/event contracts, source timestamps, receive timestamps, sequence/gap metadata, provider health.

**Controls:** clock drift alerts, gap detection, duplicate handling, bounded buffers, retry budgets, circuit breakers.

**Primary agents:** A2 lead; A9 operations; A8 security; A10 evidence.

**Exit:** `G4_REALTIME_DATA`.

---

## P06 — Historical Data & Feature Store

**Objective:** preserve reproducible raw/historical inputs and features for backtest, replay, learning and audits.

**Workstreams**
- **P06-A — Raw Immutable Archive**
- **P06-B — Historical Market Ingestion**
- **P06-C — Time-Series Store**
- **P06-D — Dataset Versioning / Snapshots**
- **P06-E — Macro Vintage Storage**
- **P06-F — Feature Store**
- **P06-G — Replay Snapshot Compatibility**
- **P06-H — Retention / Compaction / Cost Policy**

**Requirements:** event-time preservation, timezone normalization, source/version metadata, immutable raw copy, deterministic feature regeneration.

**Primary agents:** A2, A4, A7, A9, A10.

---

## P07 — Data Quality & Provenance

**Objective:** prevent bad, stale, inconsistent or unverifiable data from contaminating decisions.

**Workstreams**
- **P07-A — Schema / Contract Validation**
- **P07-B — Missing / Duplicate Detection**
- **P07-C — Outlier / Stale / Sequence Detection**
- **P07-D — Cross-Provider Validation**
- **P07-E — Provenance / Confidence Model**
- **P07-F — Quarantine / Fail-Closed Routing**
- **P07-G — Data-Quality SLOs & Monitoring**
- **P07-H — Trusted Data Gate Closure**

**Outputs:** per-field/source provenance, confidence, quality reasons, quarantine states, incident linkage.

**Primary agents:** A2 lead; A8/A9 support; A5 consumes safety status; A10 audits.

**Exit:** `G5_TRUSTED_DATA`.

---

## P08 — Technical Intelligence

**Objective:** build technical evidence families whose votes are independent enough to justify aggregation.

**Workstreams**
- **P08-A — Technical Feature / Indicator Library**
- **P08-B — Trend Family**
- **P08-C — Momentum Family**
- **P08-D — Market Structure & Price Action**
- **P08-E — Volatility & Mean Reversion**
- **P08-F — Breakout / Expansion**
- **P08-G — Multi-Timeframe & Regime**
- **P08-H — Independence / Correlation Audit**
- **P08-I — Technical Validation Gate**

**Rule:** multiple correlated transforms of the same market property are not independent confirmations.

**Outputs:** family-level evidence objects with direction, strength, freshness, timeframe, confidence and invalidation metadata.

**Primary agents:** A3, A4; A10 evidence.

**Exit:** `G6_TECHNICAL_VALIDATED`.

---

## P09 — Volume / Order Flow / Liquidity

**Objective:** model participation, pressure, liquidity and execution capacity without overstating incomplete Forex volume.

**Workstreams**
- **P09-A — Volume Taxonomy / Proxy Labels**
- **P09-B — Trades / Buy-Sell Flow / Delta / CVD**
- **P09-C — Volume Profile**
- **P09-D — Order Book / Spread / Depth / Imbalance**
- **P09-E — Liquidity Heatmap / Capacity**
- **P09-F — Funding / OI / Liquidation / Crowding**
- **P09-G — Forex Proxy Coverage Confidence**
- **P09-H — Validation / Performance**

**Rule:** Spot FX volume is explicitly labeled as broker/tick/futures/ECN proxy with provider and coverage confidence.

**Primary agents:** A2, A3, A4, A6.

---

## P10 — Fundamental / Macro / Event Intelligence

**Objective:** ingest primary macro/fundamental data with vintage-aware surprise and event context.

**Workstreams**
- **P10-A — Official Source Adapters**
- **P10-B — Economic Calendar / Event Schema**
- **P10-C — First Release / Previous-at-Time / Revision History**
- **P10-D — Macro Surprise Engine**
- **P10-E — Rates / Yields / Currency Macro**
- **P10-F — Oil / Gold / Commodity Context**
- **P10-G — Crypto Fundamental / On-Chain Context**
- **P10-H — Reliability / Latency Validation**

**Official-first baseline:** Fed/FRED/ALFRED, BLS, BEA, CFTC, ECB/Eurostat, BoE, BoJ, BIS, IMF, World Bank, EIA/OPEC/IEA, WGC/LBMA and validated exchange/on-chain sources.

**Primary agents:** A3 lead; A2 ingestion; A4 validation; A10 provenance.

---

## P11 — News & Sentiment

**Objective:** turn noisy news into attributed, deduplicated and reliability-aware event context.

**Workstreams**
- **P11-A — Source / License Policy**
- **P11-B — Ingestion / Deduplication**
- **P11-C — Entity / Asset Mapping**
- **P11-D — Sentiment / Topic / Importance**
- **P11-E — Source Reliability / Rumor Control**
- **P11-F — Event Horizon / Decay**
- **P11-G — Alerting & Narrative Inputs**
- **P11-H — Evaluation / Adversarial Tests**

**Rule:** unconfirmed news alone cannot create a trade.

**Primary agents:** A3, A8 for source/safety, A10 evidence.

---

## P12 — Market Memory & Knowledge Graph

**Objective:** retain regime-aware market relationships and historical context without presenting correlation as causation.

**Workstreams**
- **P12-A — Knowledge Graph Schema**
- **P12-B — Rolling / Conditional Correlations**
- **P12-C — Lead / Lag Analysis**
- **P12-D — Event Studies**
- **P12-E — Historical Analogs**
- **P12-F — Seasonality**
- **P12-G — Attribution Guardrails**
- **P12-H — Versioning / Replay**

**Outputs:** relationship edges with period, regime, sample, strength, uncertainty and provenance; narrative labels such as Likely Driver / Supporting Factor remain evidence-backed.

**Primary agents:** A3, A4, A7, A10.

---

## P13 — Timing & Opportunity

**Objective:** identify when an otherwise valid strategy/asset setup should or should not be considered.

**Workstreams**
- **P13-A — Session / Market Calendar**
- **P13-B — Best Trading Time Engine**
- **P13-C — Opportunity Scanner**
- **P13-D — Opportunity Ranking**
- **P13-E — No-Trade Engine**
- **P13-F — Signal Expiry / No-Chase**
- **P13-G — Scenario Engine**
- **P13-H — Timing / Ranking Validation**

**Primary agents:** A3, A4, A5.

---

## P14 — Signal / Probability / Explainability

**Objective:** fuse independent evidence into calibrated, explainable decision candidates.

**Workstreams**
- **P14-A — Evidence Contract**
- **P14-B — Weighted Evidence Fusion**
- **P14-C — Probability / Calibration Engine**
- **P14-D — Sample Size / Confidence Interval / Regime Similarity / Uncertainty**
- **P14-E — TP / Stop Outcome Probabilities**
- **P14-F — Persian Explainability**
- **P14-G — Independent Red-Team Challenge**
- **P14-H — Signal Output Contract**
- **P14-I — Signal Validation Gate**

**Outputs:** LONG / SHORT / WAIT / NO_TRADE, entry zone, invalidation, candidate SL/TP, reasons for/against, evidence freshness, calibrated probabilities and uncertainty.

**Rule:** LLMs may explain or challenge evidence; they may not invent empirical probabilities.

**Primary agents:** A3/A4; A5 risk review; Red-Team specialist; A10 audit.

**Exit:** `G7_SIGNAL_VALIDATED`.

---

## P15 — Risk & Portfolio

**Objective:** independently constrain loss, leverage, concentration, correlation and counterparty exposure.

**Workstreams**
- **P15-A — Risk Policy / Budget Hierarchy**
- **P15-B — Position Sizing**
- **P15-C — Asset / Strategy Limits**
- **P15-D — Portfolio / Correlation Exposure**
- **P15-E — Leverage / Margin**
- **P15-F — Drawdown / Risk-of-Ruin**
- **P15-G — Counterparty / Capital Segmentation**
- **P15-H — Defensive / De-Risk Modes**
- **P15-I — Independent Risk Validation**

**Primary agent:** A5 lead with veto; A4 quantitative support; A8/A9 operational-security context.

**Rule:** A5 cannot modify its own ceilings and cannot send broker orders.

---

## P16 — Pre-Trade Risk Firewall

**Objective:** provide a final independent fail-closed barrier immediately before any execution path.

**Workstreams**
- **P16-A — Signal Age / Price-Deviation Check**
- **P16-B — Duplicate / Idempotency Precheck**
- **P16-C — Size / Leverage / Exposure Check**
- **P16-D — Spread / Liquidity / Capacity Check**
- **P16-E — Event / Data / Broker / System Health Check**
- **P16-F — Daily Loss / Circuit Breaker**
- **P16-G — Fail-Closed / Override Governance**
- **P16-H — Pre-Trade Safety Gate**

**Primary agents:** A5 lead; A6 consumes decision; A8/A9 health signals; A10 evidence.

**Exit:** `G8_PRETRADE_SAFE`.

---

## P17 — Backtesting / Strategy Factory

**Objective:** measure edge under realistic costs and robust validation while preventing leakage and overfitting.

**Workstreams**
- **P17-A — Backtest Engine**
- **P17-B — Fees / Spread / Slippage / Funding / Latency / Partial Fill Model**
- **P17-C — Lookahead / Leakage / Survivorship Guards**
- **P17-D — Out-of-Sample / Walk-Forward**
- **P17-E — Monte Carlo / Stress / Sensitivity**
- **P17-F — Liquidity / Capacity Testing**
- **P17-G — Strategy Registry**
- **P17-H — Model Registry**
- **P17-I — Benchmark / Quant Gate**

**Primary agents:** A4 lead; A2 data; A5 risk; A7 learning; A10 audit.

**Exit:** `G9_QUANT_VALIDATED`.

---

## P18 — Continuous Demo Learning

**Objective:** operate a permanent paper-learning loop that continues after any future live launch.

**Workstreams**
- **P18-A — Demo / Paper Trading Engine**
- **P18-B — Decision / Outcome Journal**
- **P18-C — Training Dataset Curation**
- **P18-D — Experiment Tracking**
- **P18-E — Controlled Retraining**
- **P18-F — Champion / Challenger**
- **P18-G — Drift / Strategy Decay**
- **P18-H — Promotion Governance**
- **P18-I — 24/7 Learning Loop Operations**

**Rule:** retraining may be automated; Live promotion is never automated.

**Primary agents:** A7 lead; A4, A5, A9, A10.

---

## P19 — Shadow / Replay / Digital Twin

**Objective:** prove deterministic decision behavior and measure simulation-vs-real execution drift before capital expansion.

**Workstreams**
- **P19-A — Shadow Decisioning**
- **P19-B — Data Replay**
- **P19-C — Decision Replay**
- **P19-D — Incident Replay**
- **P19-E — Digital Twin Fill / Slippage Model**
- **P19-F — Paper / Live Drift Metrics**
- **P19-G — Deterministic Reproducibility**
- **P19-H — Shadow Validation Gate**

**Primary agents:** A4, A6, A7, A9, A10.

**Exit:** `G10_SHADOW_VALIDATED`.

---

## P20 — Execution & Order Management

**Objective:** execute intended actions exactly once, recover safely and reconcile continuously.

**Workstreams**
- **P20-A — Broker / Exchange Adapter Contract**
- **P20-B — Crypto Execution Adapter**
- **P20-C — Forex Execution Adapter**
- **P20-D — OMS State Machine**
- **P20-E — Idempotency / Duplicate Prevention**
- **P20-F — Retry / Timeout / Crash Recovery**
- **P20-G — Reconciliation**
- **P20-H — Latency / Slippage Measurement**
- **P20-I — Broker Simulation / Certification Gate**

**Primary agent:** A6 lead; A5 firewall/risk; A9 operations; A8 secrets/security; A10 evidence.

**Exit:** `G11_EXECUTION_VALIDATED`.

---

## P21 — Position Management

**Objective:** manage open exposure deterministically through normal and emergency lifecycle events.

**Workstreams**
- **P21-A — Canonical Position State**
- **P21-B — TP / SL**
- **P21-C — Partial Close**
- **P21-D — Break-Even / Trailing / Dynamic Protection**
- **P21-E — Emergency Exit**
- **P21-F — Broker Reconciliation**
- **P21-G — Restart / Crash Recovery**
- **P21-H — Position Lifecycle Tests**

**Primary agents:** A6 lead; A5 risk veto; A9 resilience.

---

## P22 — Operations / Diagnostics / Recovery

**Objective:** keep the platform observable, diagnosable, recoverable and safe under failure.

**Workstreams**
- **P22-A — Metrics / Logs / Traces**
- **P22-B — Health / System-State Machine**
- **P22-C — Auto Diagnostics**
- **P22-D — Constrained Self-Healing**
- **P22-E — Backup**
- **P22-F — Restore Drills**
- **P22-G — Disaster Recovery**
- **P22-H — Incident / Postmortem**
- **P22-I — SLO / Capacity / Cost Monitoring**
- **P22-J — Operations Validation Gate**

**System states:** NORMAL, DEGRADED, SAFE_MODE, HALTED, EMERGENCY, RECOVERY.

**Self-healing boundary:** only pre-approved reversible actions; no silent risk-policy relaxation.

**Primary agents:** A9 lead; A8 security; A5 safety; A10 audit.

**Exit:** `G12_OPERATIONS_VALIDATED`.

---

## P23 — UX / Team / Notifications

**Objective:** provide a Persian RTL operational interface that explains decisions, risk and system state clearly.

**Workstreams**
- **P23-A — Information Architecture / User Flows**
- **P23-B — Design System / RTL / Terminology**
- **P23-C — Core Screens**
- **P23-D — Learning Mode / Glossary**
- **P23-E — Team Collaboration**
- **P23-F — Notifications / Escalation**
- **P23-G — Accessibility / Responsive / Performance**
- **P23-H — Security / Dangerous-Action UX**
- **P23-I — End-to-End UX Validation**

**Core surfaces:** Dashboard, Markets, Opportunities, Trades, Portfolio, Demo, Research, Reports, System, Settings, Glossary.

**Notification severity:** Informational, Important, Critical, Emergency with deduplication, grouping, quiet hours and escalation.

**Primary agents:** UX specialist with A1/A5/A8/A9/A10 support.

---

## P24 — Controlled Production

**Objective:** introduce real capital only after all technical, quant, risk, security, execution and operations gates prove readiness.

**Workstreams**
- **P24-A — Production Readiness Dossier**
- **P24-B — Manual Live**
- **P24-C — Semi-Automatic**
- **P24-D — Micro-Capital**
- **P24-E — Canary**
- **P24-F — Controlled Auto**
- **P24-G — Kill-Switch / Emergency Drills**
- **P24-H — Continuous Live Monitoring**
- **P24-I — Owner Approval / Production Closure**

**Kill-switch hierarchy:** Strategy → Asset → Market → Broker → New Orders → Pending Orders → Risk Reduction → Close Positions → Global Halt.

**Initial live posture:** few assets/strategies, low capital, low leverage, strict loss limits, active reconciliation and readily tested kill switches.

**Primary agents:** A5 and A6 with independent A8/A9/A10 review. A0 coordinates but cannot approve past gates.

**Exit:** `G13_OWNER_LIVE_APPROVAL` requires explicit Owner approval. No automation may grant this gate.

---

## 4. Deferred or deliberately excluded from the baseline

The following are not baseline requirements and require explicit future governance before adoption:

- Kubernetes solely for sophistication rather than measured need;
- excessive microservice decomposition;
- reinforcement learning as an initial strategy engine;
- fully autonomous strategy creation and live promotion;
- smart multi-broker routing before one execution path is proven;
- whale activity as a primary standalone signal;
- public SaaS / marketplace / copy trading;
- withdrawal-capable exchange credentials;
- any design that allows LLM judgment to bypass deterministic data/risk/execution controls.

## 5. Completion semantics

A phase is not complete because code exists. Phase completion requires all required workstreams to be either CANONICAL_COMPLETE or explicitly DEFERRED with approved rationale, the relevant gate to pass, required evidence to be reproducible, active locks to be released and CURRENT-STATE/Linear to agree.

The next document to use for day-to-day sequencing is `EXECUTION-ROADMAP.md`.
