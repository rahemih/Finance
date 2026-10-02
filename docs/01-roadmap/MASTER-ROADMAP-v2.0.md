# Finance / NEXUS QUANT — Master Roadmap v2.0

MASTER_ROADMAP_V2.0 = APPROVED_BASELINE  
ROADMAP_STATE = FROZEN  
DIRECT_ROADMAP_MUTATION = FORBIDDEN  
LIVE_TRADING = DISABLED  
AUTO_TRADING = DISABLED

## Scope

Markets v1: Crypto + Forex. Gold, Oil, DXY, Bonds, Indices and Commodities are initially context markets.

The platform will provide 24/7 market ingestion, technical/fundamental/macro/order-flow intelligence, market memory, lead/lag and historical analog analysis, opportunity ranking, explainable Entry/SL/TP plans, calibrated probability with uncertainty, independent risk veto, permanent demo learning, controlled execution, audit, backup, diagnostics, Persian RTL UX, notifications and agent governance.

## Immutable principles

1. AI/LLM is not sole authority for live trading.
2. Technical analysis uses independent evidence families, not a fixed indicator count.
3. Baseline signal eligibility requires multiple independent confirmations plus weighted evidence; risk/data/liquidity/event/execution/portfolio gates remain mandatory.
4. Demo learning remains active after live launch.
5. Auto-retrain may exist; automatic live promotion is forbidden.
6. Critical-data or execution uncertainty fails closed.
7. Every important decision must be reproducible from data/model/strategy/policy/config/code versions.
8. Production progression cannot skip Research → Backtest → Demo → Shadow → Manual/Semi-Auto → Micro-Capital/Canary → Controlled Auto.

## Canonical phases

### P00 — Charter & Governance
Project identity, Source of Truth, governance, Task/Evidence/Lock contracts, Agent Registry, Current State and closure rules.
Gate: `G0_GOVERNANCE_READY`.

### P01 — Market / Provider / Compliance Research
Crypto/Forex universe, context markets, data-provider/broker/exchange comparison, licensing, regional availability, cost and backup providers.
Gate: `G1_PROVIDER_BASELINE`.

### P02 — Master Architecture
System/data/analysis/risk/execution/agent/network architecture. Modular Core + dedicated critical services; avoid premature microservices/Kubernetes.
Gate: `G2_ARCHITECTURE_FREEZE`.

### P03 — Security & Identity
Threat model, MFA, RBAC, session/device controls, secrets, private administration, audit security and least privilege.
Gate: `G3_SECURITY_BASELINE`.

### P04 — Engineering Foundation
Repository conventions, CI/CD, environments, config-as-code, dependency governance, SBOM and reproducible builds.

### P05 — Real-Time Data
Crypto and Forex adapters, normalization, WebSocket/event streaming, heartbeat, failover, time synchronization and latency validation.
Gate: `G4_REALTIME_DATA`.

### P06 — Historical Data & Feature Store
Raw/historical ingestion, Timeseries storage, dataset versioning, macro-vintage data, Feature Store and Replay compatibility.

### P07 — Data Quality & Provenance
Missing/duplicate/outlier/stale detection, cross-provider validation, provenance/confidence and fail-closed behavior.
Gate: `G5_TRUSTED_DATA`.

### P08 — Technical Intelligence
Trend, Momentum, Market Structure, Price Action, Volatility, Mean Reversion, Breakout, Multi-Timeframe and Regime models. Correlated indicators do not receive independent votes.
Gate: `G6_TECHNICAL_VALIDATED`.

### P09 — Volume / Order Flow / Liquidity
Buy/Sell flow, Delta, CVD, Volume Profile, Order Book imbalance, spread/depth, liquidity heatmap, capacity and liquidation/crowding context. Forex volume is explicitly labeled as broker/tick/futures/ECN proxy with coverage confidence.

### P10 — Fundamental / Macro / Event Intelligence
Official-first sources: Fed/FRED/BLS/BEA/CFTC, ECB/Eurostat, BoE, BoJ, IMF/BIS/World Bank, EIA/OPEC/IEA, World Gold Council/LBMA, validated crypto sources. Store forecast, first release, previous-at-time and later revisions.

### P11 — News & Sentiment
News ingestion, deduplication, entity/asset mapping, importance, sentiment, source reliability, rumor control and event horizon. Unconfirmed news alone cannot create a trade.

### P12 — Market Memory & Knowledge Graph
Correlation, lead/lag, regime-dependent relationships, event studies, historical analogs, seasonality and attribution. Correlation is never presented as proven causation.

### P13 — Timing & Opportunity
Best/weak/no-trade windows by asset/strategy/timeframe/session/regime; opportunity scanning/ranking and signal expiry/no-chase logic.

### P14 — Signal / Probability / Explainability
Evidence fusion; LONG/SHORT/WAIT/NO_TRADE; calibrated probability, sample size, uncertainty, TP/Stop probabilities; explainable Persian reasoning and Red-Team challenge.
Gate: `G7_SIGNAL_VALIDATED`.

### P15 — Risk & Portfolio
Trade/asset/strategy/portfolio/correlation/leverage/drawdown/risk-of-ruin/counterparty controls, capital segmentation and defensive modes. Risk retains independent veto.

### P16 — Pre-Trade Risk Firewall
Independent final checks for signal age, price deviation, duplicates, size, leverage, exposure, spread, liquidity, event/data/broker/system health and daily loss.
Gate: `G8_PRETRADE_SAFE`.

### P17 — Backtesting / Strategy Factory
Reality-aware costs/slippage/funding/latency/partial fill/liquidity, OOS, Walk-Forward, Monte Carlo, stress, anti-lookahead/leakage/overfitting, Strategy and Model registries.
Gate: `G9_QUANT_VALIDATED`.

### P18 — Continuous Demo Learning
Permanent Observe → Analyze → Demo Trade → Outcome → Journal → Dataset → Experiment → Retrain/Validate → Challenger. Drift and strategy decay monitoring. No automatic live promotion.

### P19 — Shadow / Replay / Digital Twin
Shadow decisions, deterministic data/decision/incident replay, live-vs-simulated Digital Twin and paper/live drift monitoring.
Gate: `G10_SHADOW_VALIDATED`.

### P20 — Execution & Order Management
Broker/exchange adapters, OMS lifecycle, idempotency, duplicate prevention, retry/timeout/crash recovery and reconciliation.
Gate: `G11_EXECUTION_VALIDATED`.

### P21 — Position Management
TP/SL, partial close, break-even, trailing/dynamic/emergency exit and broker reconciliation.

### P22 — Operations / Diagnostics / Recovery
Metrics/logs/traces, diagnostics, constrained self-healing, backup/restore drills, disaster recovery and incident/postmortem management.
Gate: `G12_OPERATIONS_VALIDATED`.

### P23 — UX / Team / Notifications
Figma/Next.js Persian RTL interface, Dashboard/Markets/Opportunities/Trades/Portfolio/Demo/Research/Reports/System/Settings/Glossary, Learning Mode, collaboration and prioritized multi-channel notifications.

### P24 — Controlled Production
Manual Live → Semi-Auto → Micro-Capital → Canary → Controlled Auto. Few assets/strategies, low risk/leverage and active kill switch initially.
Gate: `G13_OWNER_LIVE_APPROVAL`.

## System states

NORMAL, DEGRADED, SAFE_MODE, HALTED, EMERGENCY, RECOVERY.

## Kill-switch hierarchy

Strategy → Asset → Market → Broker → New Orders → Pending Orders → Risk Reduction → Close Positions → Global Halt.

## Agent baseline

A0 Governance/Orchestrator  
A1 Architecture  
A2 Data  
A3 Market Intelligence  
A4 Quant  
A5 Risk  
A6 Execution  
A7 Learning  
A8 Security  
A9 Operations  
A10 Evidence/Audit

Specialist agents spawn on demand. Each agent has Role, Authority, Read/Write/Forbidden scope, tools/plugins/skills, escalation and audit requirements.

## Mandatory validation classes

Unit, Integration, Contract, Regression, E2E, Security, Performance, Load, Spike, Stress, Soak, Chaos, Recovery, Restore, Replay, Data Quality, Backtest, Walk-Forward, Monte Carlo, Calibration, Paper, Shadow, Broker Simulation and Failover.

## Definition of Ready

Dependencies pass; Task Contract valid; Fresh Live Guard passes; HEAD/locks/shared writers verified; access/secrets/test/rollback plans exist.

## Definition of Done

Implementation and required tests pass; security/performance/contracts/docs/evidence/monitoring/rollback complete; no unresolved Critical/High blocker; PR merged; post-merge verification passes; lock released; Task Catalog and Current State reconciled.

## Change policy

This file is frozen. Future changes use ERRATA, ADR, RFC or ROADMAP ADDENDUM, never direct mutation.

## Next authorized phase

P00 — Charter & Governance.
