# Finance / NEXUS QUANT — Execution Roadmap

STATE = GOVERNED_EXECUTION_COMPANION  
BASELINE = `MASTER-ROADMAP-v2.0.md`  
DETAILS = `MASTER-ROADMAP-DETAILS.md`  
TASK = `FIN-P00-WE-001`

## 1. Execution model

Work advances by governed task, not by informal phase labels.

Each task follows:

`Fresh Live Guard → Task Contract → Lock → Branch → Implementation/Docs → Tests → Evidence → PR → Required Checks → Merge → Post-Merge Verify → Lock Release → Task Catalog + Current State + Linear Reconciliation`.

A workstream identifier such as `P05-D` is a planning unit. Actual implementation tasks use IDs such as `FIN-P05-WD-001`, `FIN-P05-WD-002`, and repair tasks use `-RNN`.

No later-phase work may silently consume an unfinished dependency. Parallel execution is permitted only when write scopes, locks and technical dependencies do not conflict.

## 2. Gate-aware sequencing

The default critical path is:

`P00 → G0 → P01 → G1 → P02 → G2 → P03 → G3 → P04 → P05 → G4 → P06 → P07 → G5 → P08 → G6 → P09/P10/P11/P12 → P13 → P14 → G7 → P15 → P16 → G8 → P17 → G9 → P18 → P19 → G10 → P20 → G11 → P21 → P22 → G12 → P23 → P24 → G13`.

Some research and UX work may begin earlier only when it does not create implementation coupling or bypass a gate.

## 3. Current execution position

Canonical completion:
- P00 — Charter & Governance: CANONICAL_COMPLETE / G0 PASS
- P01 — Market / Provider / Compliance Research: CANONICAL_COMPLETE / G1 PASS
- P02 — Master Architecture: CANONICAL_COMPLETE / G2_ARCHITECTURE_FREEZE PASS
- P03 — Security & Identity: CANONICAL_COMPLETE / G3_SECURITY_BASELINE PASS
- P04 — Engineering Foundation: CANONICAL_COMPLETE / Engineering Foundation exit PASS
- P05 — Real-Time Data: CANONICAL_COMPLETE / G4_REALTIME_DATA PASS
- P06 — Historical Data & Feature Store: CANONICAL_COMPLETE

Phase transition:
- P06 — Historical Data & Feature Store: CANONICAL_COMPLETE
- P07 — Data Quality & Provenance: ACTIVE
- active governed task: none
- active lock: none
- completed workstreams: P07-A — Schema Validators / CANONICAL_COMPLETE; P07-B — Completeness / Duplicate Checks / CANONICAL_COMPLETE; P07-C — Staleness / Outlier / Sequence Checks / CANONICAL_COMPLETE; P07-D — Cross-Provider Comparison / CANONICAL_COMPLETE; P07-E — Provenance & Confidence Contract / CANONICAL_COMPLETE; P07-F — Quarantine / Fail-Closed Routing / CANONICAL_COMPLETE
- next governed workstream: P07-G — Quality Dashboards / SLOs / READY_NOT_STARTED

Completed P05 baselines:
- P05-A — Kaiko crypto adapter: CANONICAL_COMPLETE
- P05-B — dxFeed Forex quote adapter: CANONICAL_COMPLETE
- P05-C — Databento Gold context adapter: CANONICAL_COMPLETE
- P05-D — Canonical Normalization / Symbol Master / Clock Model: CANONICAL_COMPLETE
- P05-E — Streaming / Heartbeat / Backpressure: CANONICAL_COMPLETE
- P05-F — Reconnect / Failover / Gap Recovery: CANONICAL_COMPLETE
- P05-G — Latency / Throughput / Soak Validation: CANONICAL_COMPLETE
- P05-H — Real-Time Data Gate Closure / G4: CANONICAL_COMPLETE
- P05-A R01 fresh revalidation: CANONICAL_COMPLETE

P06 canonical boundary:
- P06-A — Immutable Raw Archive: CANONICAL_COMPLETE
- P06-B — Historical Backfill: CANONICAL_COMPLETE
- P06-C — Time-Series Optimized Query Layer: CANONICAL_COMPLETE
- P06-D — Dataset Manifests & Versioning: CANONICAL_COMPLETE
- P06-E — Macro Vintage Model: CANONICAL_COMPLETE
- P06-F — Feature Definitions & Materialization: CANONICAL_COMPLETE
- P06-G — Replay Snapshot Interfaces: CANONICAL_COMPLETE
- P06-H — Retention / Compaction / Storage-Cost Tests: CANONICAL_COMPLETE

P07 active boundary:
- P07-A — Schema Validators: CANONICAL_COMPLETE
- P07-B — Completeness / Duplicate Checks: CANONICAL_COMPLETE
- P07-C — Staleness / Outlier / Sequence Checks: CANONICAL_COMPLETE
- P07-D — Cross-Provider Comparison: CANONICAL_COMPLETE
- P07-E — Provenance & Confidence Contract: CANONICAL_COMPLETE
- P07-F — Quarantine / Fail-Closed Routing: CANONICAL_COMPLETE
- P07-G — Quality Dashboards / SLOs: READY_NOT_STARTED
- P07-H — Trusted-Data Gate / G5: BLOCKED

---

## 4. Phase-by-phase execution plan

### P00 — Charter & Governance

| Order | Workstream | Deliverable | Dependency | Closure |
|---|---|---|---|---|
| 1 | P00-A | Charter, Governance, baseline SoT | none | COMPLETE |
| 2 | P00-B | Protected main + branch hygiene | P00-A | COMPLETE |
| 3 | P00-C | Linear management baseline | P00-A/B | COMPLETE |
| 4 | P00-D | Toolchain/Plugin/Skill/Access Matrix | P00-C | COMPLETE |
| 5 | P00-E | Detailed roadmap package | P00-D | COMPLETE |
| 6 | P00-F | P00 audit, state reconciliation, G0 dossier | P00-E | COMPLETE |

P00-F must verify no unresolved drift, no active lock, roadmap documents canonical, Linear synchronized and all governance required checks passing.

### P01 — Market / Provider / Compliance Research

1. **P01-A Universe Registry:** define candidate tradable crypto/forex instruments and context markets; establish stable instrument IDs and venue metadata requirements.
2. **P01-B Data Provider Scorecards:** evaluate real-time, historical, order-book, derivatives and context data.
3. **P01-C Broker/Exchange Scorecards:** demo/sandbox, order types, API reliability, margin, reconciliation, regional eligibility.
4. **P01-D Compliance/Jurisdiction Matrix:** region availability, account constraints, market/data licenses, retention/redistribution restrictions.
5. **P01-E Cost Model:** subscription, exchange, broker, egress, storage, observability and operational cost assumptions.
6. **P01-F Primary/Backup Design:** independent fallback and cross-provider validation options.
7. **P01-G Baseline Decision:** documented shortlist, rejected alternatives and open risks; pass G1.

No secrets or live credentials are provisioned in P01.

### P02 — Master Architecture

1. **P02-A ADR Framework & Architecture Principles**
2. **P02-B Domain / Module Boundaries**
3. **P02-C Data Flow & Storage Architecture**
4. **P02-D Intelligence / Signal Architecture**
5. **P02-E Risk / Firewall / Execution Architecture**
6. **P02-F Agent Architecture & Authority Model**
7. **P02-G Environment / Network / DR Topology**
8. **P02-H Capacity / Cost Envelope**
9. **P02-I Architecture Review + G2 Freeze**

Required diagrams: context, containers/modules, data flow, decision flow, execution path, recovery path and agent interaction.

### P03 — Security & Identity

1. **P03-A Threat Model**
2. **P03-B RBAC/MFA/Session/Device Policy**
3. **P03-C Secrets/KMS/Vault and Environment Separation**
4. **P03-D Private Admin/Network Exposure**
5. **P03-E Audit Integrity + High-Risk Change Control**
6. **P03-F Dependency/Supply-Chain Security**
7. **P03-G Incident / Emergency Access Runbooks**
8. **P03-H Security Validation + G3**

Broker/exchange API keys later must be trading-only and withdrawal-disabled.

### P04 — Engineering Foundation

1. **P04-A Workspace / Repository Layout**
2. **P04-B Runtime / Language / Version Baseline**
3. **P04-C CI/CD Pipeline**
4. **P04-D Configuration Contract**
5. **P04-E Testing Harness / Deterministic Clocks / Mocks**
6. **P04-F SBOM / License / Dependency Policy**
7. **P04-G Developer Bootstrap & Tooling**
8. **P04-H Reproducible Build / Artifact Verification**

No market logic starts until clean build/test foundations exist.

### P05 — Real-Time Data

1. **P05-A Crypto adapter contract + first provider**
2. **P05-B Forex adapter contract + first provider**
3. **P05-C Context-market ingestion**
4. **P05-D Canonical normalization, symbols, time semantics**
5. **P05-E Streaming bus, heartbeat, buffering/backpressure**
6. **P05-F Reconnect, gap recovery, provider failover**
7. **P05-G Throughput/latency/load/soak tests**
8. **P05-H Data gate evidence + G4**

Recommended rollout: one instrument/one provider per market first, then expand after contract stability.

### P06 — Historical Data & Feature Store

1. **P06-A Immutable raw archive**
2. **P06-B Historical backfill**
3. **P06-C Time-series optimized query layer**
4. **P06-D Dataset manifests/versioning**
5. **P06-E Macro vintage model**
6. **P06-F Feature definitions/materialization**
7. **P06-G Replay snapshot interfaces**
8. **P06-H Retention/compaction/storage-cost tests**

### P07 — Data Quality & Provenance

1. **P07-A Schema validators**
2. **P07-B Completeness/duplicate checks**
3. **P07-C Staleness/outlier/sequence checks**
4. **P07-D Cross-provider comparison**
5. **P07-E Provenance and confidence contract**
6. **P07-F Quarantine/fail-closed routing**
7. **P07-G Quality dashboards/SLOs**
8. **P07-H Trusted-data gate + G5**

No downstream signal engine may treat quarantined or critically stale data as valid.

### P08 — Technical Intelligence

1. **P08-A Feature/indicator foundation**
2. **P08-B Trend models**
3. **P08-C Momentum models**
4. **P08-D Market Structure / Price Action**
5. **P08-E Volatility / Mean Reversion**
6. **P08-F Breakout / Expansion**
7. **P08-G Multi-Timeframe / Regime**
8. **P08-H Independence/correlation audit**
9. **P08-I Benchmark/calibration + G6**

Each family outputs a common evidence contract instead of directly sending trades.

### P09 — Volume / Order Flow / Liquidity

1. **P09-A Volume/proxy ontology**
2. **P09-B Trade flow, Delta, CVD**
3. **P09-C Volume Profile**
4. **P09-D Book/spread/depth/imbalance**
5. **P09-E Liquidity heatmap/capacity**
6. **P09-F Funding/OI/liquidation/crowding**
7. **P09-G Forex proxy confidence**
8. **P09-H Data/performance validation**

### P10 — Fundamental / Macro / Event

1. **P10-A Primary official-source adapters**
2. **P10-B Calendar/event schema**
3. **P10-C Release/vintage/revision storage**
4. **P10-D Surprise engine**
5. **P10-E Rates/yields/FX macro context**
6. **P10-F Oil/gold/commodity context**
7. **P10-G Crypto fundamental/on-chain context**
8. **P10-H Reliability/latency tests**

### P11 — News & Sentiment

1. **P11-A Source/licensing baseline**
2. **P11-B Ingestion and deduplication**
3. **P11-C Entity/asset mapping**
4. **P11-D Sentiment/topic/importance**
5. **P11-E Reliability/rumor controls**
6. **P11-F Event horizon/decay**
7. **P11-G Notifications/narrative feed**
8. **P11-H Accuracy/adversarial evaluation**

### P12 — Market Memory & Knowledge Graph

1. **P12-A Entity/relation ontology**
2. **P12-B Regime-conditioned correlation**
3. **P12-C Lead/lag**
4. **P12-D Event studies**
5. **P12-E Historical analog search**
6. **P12-F Seasonality**
7. **P12-G Attribution labels/causality guardrails**
8. **P12-H Versioning/replay validation**

### P13 — Timing & Opportunity

1. **P13-A Session/calendar service**
2. **P13-B Best Trading Time Engine**
3. **P13-C Opportunity scanner**
4. **P13-D Ranking model**
5. **P13-E No-Trade rules/model**
6. **P13-F Expiry/no-chase**
7. **P13-G Scenario generation**
8. **P13-H Ranking/timing validation**

### P14 — Signal / Probability / Explainability

1. **P14-A Evidence schema**
2. **P14-B Fusion/scoring**
3. **P14-C Empirical probability/calibration**
4. **P14-D Uncertainty/sample/regime similarity**
5. **P14-E TP/Stop probability**
6. **P14-F Persian explanation**
7. **P14-G Independent Red-Team**
8. **P14-H Final signal contract**
9. **P14-I G7 validation**

No probability may be a free-form LLM guess.

### P15 — Risk & Portfolio

1. **P15-A Risk-policy hierarchy**
2. **P15-B Position sizing**
3. **P15-C Asset/strategy limits**
4. **P15-D Portfolio/correlation limits**
5. **P15-E Margin/leverage**
6. **P15-F Drawdown/risk-of-ruin**
7. **P15-G Counterparty/capital segmentation**
8. **P15-H Defensive modes**
9. **P15-I Independent validation**

### P16 — Pre-Trade Risk Firewall

1. **P16-A Signal freshness/price drift**
2. **P16-B Duplicate/idempotency**
3. **P16-C Size/leverage/exposure**
4. **P16-D Spread/liquidity/capacity**
5. **P16-E Data/event/broker/system health**
6. **P16-F Daily-loss/circuit breakers**
7. **P16-G Fail-closed and override governance**
8. **P16-H G8 validation**

### P17 — Backtesting / Strategy Factory

1. **P17-A Deterministic backtest engine**
2. **P17-B Reality-aware execution cost model**
3. **P17-C Leakage/lookahead/survivorship guards**
4. **P17-D OOS/Walk-Forward**
5. **P17-E Monte Carlo/stress/sensitivity**
6. **P17-F Capacity/liquidity**
7. **P17-G Strategy Registry**
8. **P17-H Model Registry**
9. **P17-I G9 quant dossier**

### P18 — Continuous Demo Learning

1. **P18-A Demo execution**
2. **P18-B Journal/outcomes**
3. **P18-C Dataset curation**
4. **P18-D Experiment tracking**
5. **P18-E Retraining pipeline**
6. **P18-F Champion/Challenger**
7. **P18-G Drift/decay**
8. **P18-H Promotion governance**
9. **P18-I Continuous loop monitoring**

Demo remains permanently enabled as a learning environment after Live exists.

### P19 — Shadow / Replay / Digital Twin

1. **P19-A Shadow signals/decisions**
2. **P19-B Raw data replay**
3. **P19-C Decision replay**
4. **P19-D Incident replay**
5. **P19-E Digital Twin fills/slippage**
6. **P19-F Paper-vs-live drift**
7. **P19-G Determinism audit**
8. **P19-H G10 validation**

### P20 — Execution & OMS

1. **P20-A Adapter contract**
2. **P20-B Crypto execution**
3. **P20-C Forex execution**
4. **P20-D OMS lifecycle**
5. **P20-E Idempotency/duplicate prevention**
6. **P20-F Retry/timeout/crash recovery**
7. **P20-G Reconciliation**
8. **P20-H Execution-quality metrics**
9. **P20-I Broker/exchange simulation + G11**

### P21 — Position Management

1. **P21-A Position state**
2. **P21-B TP/SL**
3. **P21-C Partial close**
4. **P21-D Break-even/trailing/dynamic exits**
5. **P21-E Emergency exit**
6. **P21-F Broker reconciliation**
7. **P21-G Restart recovery**
8. **P21-H Lifecycle validation**

### P22 — Operations / Diagnostics / Recovery

1. **P22-A Metrics/logs/traces**
2. **P22-B System state machine**
3. **P22-C Diagnostics**
4. **P22-D Restricted self-healing**
5. **P22-E Backup**
6. **P22-F Restore drills**
7. **P22-G Disaster recovery**
8. **P22-H Incident/postmortem**
9. **P22-I SLO/capacity/cost**
10. **P22-J G12 validation**

### P23 — UX / Team / Notifications

1. **P23-A IA and workflows**
2. **P23-B RTL design system**
3. **P23-C Operational screens**
4. **P23-D Learning Mode and glossary**
5. **P23-E Team comments/mentions/assignments/approvals**
6. **P23-F Notification engine**
7. **P23-G Accessibility/responsive/performance**
8. **P23-H Dangerous-action/security UX**
9. **P23-I E2E validation**

### P24 — Controlled Production

1. **P24-A Readiness dossier**
2. **P24-B Manual Live**
3. **P24-C Semi-Auto**
4. **P24-D Micro-Capital**
5. **P24-E Canary**
6. **P24-F Controlled Auto**
7. **P24-G Kill-switch/emergency drills**
8. **P24-H Continuous production monitoring**
9. **P24-I G13 Owner approval / production closure**

Every escalation in autonomy/capital requires fresh evidence. A later stage does not inherit approval merely because an earlier stage passed.

---

## 5. Parallelization policy

Allowed examples:
- P09/P10/P11 research implementations may progress in parallel after trusted data contracts exist.
- UI design may explore future screens while backend contracts are being developed, but implementation claims remain provisional until interfaces are canonical.
- Independent tests/security reviews may run in parallel with documentation closure if they do not mutate shared files.

Forbidden examples:
- execution adapter work that bypasses G8;
- probability engine using datasets that have not passed trusted-data requirements;
- production automation before G13;
- two active tasks writing the same canonical shared file without explicit coordinated lock.

## 6. Workstream completion states

A workstream may be:
`NOT_STARTED → READY → ACTIVE → VALIDATION → PASS → CANONICAL_COMPLETE`.

Alternate states:
`NOT_READY, BLOCKED, HUMAN_GATE, REPAIR, PAUSED, DEFERRED, RETIRED`.

Only CANONICAL_COMPLETE or explicitly governed DEFERRED items may count toward phase closure.

## 7. Owner gates

Owner interaction should be minimized to actual Human Gates. Expected high-impact Owner Gates include:
- first real-capital Live activation;
- material risk/leverage ceiling increases;
- production broker/exchange credential changes or provider legal/account acceptance;
- critical model/strategy promotion to Live;
- emergency-policy or critical permission changes;
- G13 production approval.

Routine engineering, documentation, testing, repair and evidence reconciliation should continue without unnecessary Owner interruption.
