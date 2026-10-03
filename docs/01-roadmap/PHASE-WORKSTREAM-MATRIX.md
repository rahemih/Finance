# Finance / NEXUS QUANT — Phase / Workstream Matrix

STATE = GOVERNED_COMPANION  
TASK = `FIN-P00-WE-001`

This matrix is the compact planning index for all canonical phases. Detailed scope lives in `MASTER-ROADMAP-DETAILS.md`; ordering lives in `EXECUTION-ROADMAP.md`.

| Phase | Workstreams | Primary agents | Key canonical outputs | Gate / phase exit |
|---|---|---|---|---|
| P00 Charter & Governance | A Charter/SoT; B Repo Governance; C Linear PM; D Toolchain; E Detailed Roadmap; F Closure | A0, A8, A10 | Charter, Governance, Current State, Task Catalog, Agent Registry, Toolchain Matrix, Roadmap Package | G0 |
| P01 Market/Provider/Compliance | A Universe; B Data Providers; C Brokers/Exchanges; D Compliance; E Cost/Rights; F Backup; G Baseline | A1, A2, A3, A5, A8, A10 | Universe registry, provider scorecards, compliance/cost/fallback matrices | G1 |
| P02 Master Architecture | A Principles; B Domains; C Data; D Analysis; E Risk/Execution; F Agents; G Network/DR; H Capacity; I Freeze | A1 lead, A2/A4/A5/A6/A8/A9/A10 | ADRs, diagrams, interfaces, topology, sizing | G2 |
| P03 Security & Identity | A Threats; B MFA/RBAC; C Secrets; D Admin Network; E Audit; F Supply Chain; G Incident; H Closure | A8 lead, A1/A5/A9/A10 | Threat model, access policy, secret architecture, incident runbooks | G3 |
| P04 Engineering Foundation | A Repo; B Runtime; C CI/CD; D Config; E Tests; F SBOM; G Dev Tooling; H Reproducibility | A1, A8, A9, A10 | workspace, lockfiles, CI, test harness, SBOM, build evidence | Phase exit |
| P05 Real-Time Data | A Crypto; B Forex; C Context; D Normalization; E Streaming; F Failover; G Perf; H Closure | A2 lead, A8/A9/A10 | adapters, canonical events, heartbeats, latency evidence | G4 |
| P06 Historical/Feature Store | A Raw; B Backfill; C Time-Series; D Versioning; E Macro Vintages; F Features; G Replay; H Retention | A2, A4, A7, A9, A10 | raw archive, versioned datasets, feature store, replay snapshots | Phase exit |
| P07 Data Quality/Provenance | A Schema; B Missing/Duplicate; C Outlier/Stale; D Cross-Provider; E Provenance; F Quarantine; G SLO; H Closure | A2 lead, A5/A8/A9/A10 | quality engine, provenance/confidence, quarantine, SLOs | G5 |
| P08 Technical Intelligence | A Library; B Trend; C Momentum; D Structure/PA; E Vol/MeanRev; F Breakout; G MTF/Regime; H Independence; I Closure | A3, A4, A10 | family evidence contracts, independence audit, benchmarks | G6 |
| P09 Volume/Order Flow/Liquidity | A Taxonomy; B Delta/CVD; C Profile; D Book; E Liquidity; F Derivatives; G FX Proxy; H Validation | A2, A3, A4, A6 | flow/liquidity evidence with coverage confidence | Phase exit |
| P10 Fundamental/Macro/Event | A Official Sources; B Calendar; C Vintages; D Surprise; E Rates/FX; F Commodities; G Crypto; H Validation | A2, A3, A4, A10 | official-source event/fundamental evidence, vintage history | Phase exit |
| P11 News/Sentiment | A Sources; B Ingest/Dedup; C Mapping; D Sentiment; E Reliability; F Decay; G Alerts; H Eval | A3, A8, A10 | deduped attributed news evidence and reliability metadata | Phase exit |
| P12 Market Memory/Graph | A Ontology; B Correlation; C LeadLag; D Event Studies; E Analogs; F Seasonality; G Attribution; H Replay | A3, A4, A7, A10 | graph, relation evidence, analog/event-study services | Phase exit |
| P13 Timing/Opportunity | A Sessions; B Timing; C Scanner; D Rank; E No-Trade; F Expiry; G Scenarios; H Validation | A3, A4, A5 | timing scores, ranked opportunities, no-trade decisions | Phase exit |
| P14 Signal/Probability/Explainability | A Evidence; B Fusion; C Calibration; D Uncertainty; E TP/Stop; F Persian Explain; G Red-Team; H Contract; I Closure | A3, A4, A5, A10 + Red-Team | calibrated decision candidates and explanations | G7 |
| P15 Risk/Portfolio | A Policy; B Sizing; C Asset/Strategy; D Portfolio; E Leverage; F Drawdown; G Counterparty; H Defensive; I Validation | A5 lead, A4/A8/A9/A10 | risk budgets, sizing, exposure limits, defensive modes | Phase exit |
| P16 Pre-Trade Firewall | A Freshness; B Duplicate; C Size/Exposure; D Liquidity; E Health/Event; F Daily Loss; G Fail-Closed; H Closure | A5 lead, A6/A8/A9/A10 | deterministic pre-trade verdict + reason codes | G8 |
| P17 Backtest/Strategy Factory | A Engine; B Costs; C Leakage; D OOS/WF; E MC/Stress; F Capacity; G Strategy Registry; H Model Registry; I Closure | A4 lead, A2/A5/A7/A10 | backtests, registries, validation dossiers | G9 |
| P18 Continuous Demo Learning | A Paper; B Journal; C Dataset; D Experiments; E Retrain; F Champion/Challenger; G Drift; H Promotion; I Loop | A7 lead, A4/A5/A9/A10 | permanent demo loop, experiment and drift evidence | Phase exit |
| P19 Shadow/Replay/Digital Twin | A Shadow; B Data Replay; C Decision Replay; D Incident Replay; E Twin; F Drift; G Determinism; H Closure | A4, A6, A7, A9, A10 | replayable shadow/digital-twin evidence | G10 |
| P20 Execution/OMS | A Contract; B Crypto; C Forex; D OMS; E Idempotency; F Recovery; G Reconcile; H Quality; I Closure | A6 lead, A5/A8/A9/A10 | execution adapters, OMS, reconciliation, recovery | G11 |
| P21 Position Management | A State; B TP/SL; C Partial; D BE/Trail; E Emergency; F Reconcile; G Restart; H Tests | A6 lead, A5/A9 | deterministic position lifecycle | Phase exit |
| P22 Operations/Recovery | A Telemetry; B States; C Diagnostics; D Self-Heal; E Backup; F Restore; G DR; H Incident; I SLO/Cost; J Closure | A9 lead, A5/A8/A10 | observability, backup/restore, DR, runbooks | G12 |
| P23 UX/Team/Notifications | A IA; B RTL System; C Screens; D Learning/Glossary; E Team; F Notifications; G A11y/Perf; H Security UX; I E2E | UX specialist, A1/A5/A8/A9/A10 | Persian RTL product surfaces and notification workflows | Phase exit |
| P24 Controlled Production | A Dossier; B Manual; C Semi-Auto; D Micro; E Canary; F Controlled Auto; G Kill Switch; H Monitor; I Owner Closure | A5/A6/A8/A9/A10, A0 coordinates | staged production evidence and owner approvals | G13 |

## Shared writer / lock-sensitive files

The following are treated as high-conflict shared writers and require explicit coordination when multiple tasks exist:

- `docs/02-current-state/CURRENT-STATE.md`
- `docs/13-tasks/TASK-CATALOG.md`
- Agent Registry and Toolchain Matrix
- shared architecture contracts
- canonical schemas
- risk policies
- execution contracts
- model/strategy registries
- deployment/environment manifests

## Parallel-work guidance

Parallel tasks should prefer phase-owned folders and immutable evidence artifacts. A0 must serialize shared-writer mutations when evidence cannot prove non-conflict.
