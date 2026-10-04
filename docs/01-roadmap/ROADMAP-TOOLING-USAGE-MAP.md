# Finance / NEXUS QUANT — Roadmap Tooling Usage Map

STATE = GOVERNED_ROADMAP_COMPANION  
TASK = `FIN-P01-WT-001`  
LINEAR = `HOS-119`  
EFFECTIVE_DATE = 2026-10-03  
MASTER_ROADMAP = `MASTER-ROADMAP-v2.0.md` / FROZEN  
PRODUCTION_SELECTIONS = NOT_AUTHORIZED_BY_THIS_DOCUMENT

## 1. Purpose

This is the single human-readable map showing **which project tool/capability is used in which roadmap phase and for what purpose**.

It covers:
- plugins/connectors;
- skills;
- open-source repositories;
- frontend libraries;
- agent frameworks and ready-agent references;
- automation/orchestration systems;
- standards/protocols;
- infrastructure/security/data/ML/testing/observability capabilities;
- project-native governance tools.

It is an index and usage map. Specialist registries remain authoritative for selection details, licensing, benchmarks and exact adoption decisions.

## 2. State legend

| State | Meaning |
|---|---|
| `ACTIVE_NOW` | Already approved and actively used for project work |
| `BASELINE_STANDARD` | Standard/design rule to follow; package installation may not be required |
| `ADOPT_CANDIDATE` | Preferred candidate; must be revalidated before production adoption |
| `USE_CANDIDATE` | Useful for a bounded use case |
| `ALTERNATIVE` | Fallback/alternative; not installed in parallel by default |
| `REFERENCE` | Architecture/research reference only |
| `CONDITIONAL` | Evaluate only if the triggering architecture/use case exists |
| `LICENSE_REVIEW` | Exact production license/terms must be verified |
| `HUMAN_GATE` | Explicit authorized human action is required |
| `DEFERRED` | Intentionally not active until its roadmap phase |

## 3. Canonical specialist registries

| Domain | Canonical source |
|---|---|
| Plugins / connectors / skills | `docs/09-agents/TOOLCHAIN-MATRIX.md` |
| Open-source finance/quant repositories | `docs/03-research/OPEN-SOURCE-REPOSITORY-DEPENDENCY-REGISTRY.md` |
| Frontend repositories | `docs/03-research/FRONTEND-UI-UX-REPOSITORY-REGISTRY.md` |
| Frontend quality | `docs/03-research/FRONTEND-EXCELLENCE-BASELINE.md` |
| Agent frameworks / ready agents | `docs/03-research/AGENT-FRAMEWORK-READY-AGENT-REGISTRY.md` |
| Agent governance | `docs/09-agents/AGENT-GOVERNANCE-INTEGRATION.md` |
| Automation/orchestration | `docs/03-research/AUTOMATION-ORCHESTRATION-REGISTRY.md` |
| Automation governance | `docs/00-governance/AUTOMATION-GOVERNANCE.md` |
| Master capability registry | `docs/03-research/PROJECT-CAPABILITY-TOOLING-MASTER-REGISTRY.md` |
| Phase activation policy | `docs/00-governance/PHASE-TOOLING-ACTIVATION-POLICY.md` |
| Build readiness | `docs/02-current-state/BUILD-READINESS-CHECKLIST.md` |
| Provider / technology comparison | `docs/01-roadmap/TECHNOLOGY-PROVIDER-MATRIX.md` |

## 4. Global project tools used across multiple phases

| Tool / capability | Type | State | Primary use | Main phases |
|---|---|---|---|---|
| GitHub | Plugin + repository platform | ACTIVE_NOW | canonical source of truth, PRs, CI evidence, governance | P00-P24 |
| Linear | Plugin / project management | ACTIVE_NOW | milestones, task coordination, dependency/status mirror | P00-P24 |
| GitHub Actions | Automation | ACTIVE_NOW | Governance Verify, CI, Branch Hygiene, later build/release automation | P00-P24 |
| Task Contracts / Locks / Evidence | Project-native governance | ACTIVE_NOW | scope, authority, concurrency and closure evidence | P00-P24 |
| Figma | Plugin + skills | ACTIVE_NOW / phase-triggered | architecture diagrams, design system, UX, design-to-code | P02, P23 |
| Google Drive / Docs / Sheets / Slides | Plugin + skills | ACTIVE_NOW | controlled collaboration, reports, evidence packs, exports | P00-P24 |
| Slack | Plugin | ACTIVE_NOW | team coordination / operational communication | P00-P24, especially P22 |
| Notion | Plugin | ACTIVE_NOW / optional | research synthesis / knowledge capture; GitHub stays canonical | P01-P24 |
| Gmail | Plugin | ACTIVE_NOW / governed | project email, later notifications | P00-P24 |
| Google Calendar | Plugin | ACTIVE_NOW | review gates, scheduling, operations coordination | P00-P24 |
| Dropbox | Plugin | ACTIVE_NOW / auxiliary | artifact exchange / secondary storage | P00-P24 |
| Adobe | Plugin | ACTIVE_NOW / auxiliary | PDF/document/media review and production | P01-P24 |
| Canva / Gamma | Plugins | ACTIVE_NOW / auxiliary | stakeholder reporting/presentations | P01-P24 |
| Context7 | Plugin | ACTIVE_NOW | current library/API documentation | P02-P24 |
| Exa | Plugin | ACTIVE_NOW | research/news/paper/web discovery | P01, P10, P11, P12, P14, P17 |
| Wolfram | Plugin | ACTIVE_NOW | exact math/statistics/quant validation | P08, P14, P15, P17 |
| Legal Data Hunter | Plugin | ACTIVE_NOW | regulatory/legal primary-source discovery | P01-D/E, P03, P24 |
| Blockscout | Plugin | ACTIVE_NOW | EVM on-chain research/evidence | P01, P10, P12 |
| TinyFish | Plugin | ACTIVE_NOW / conditional | browser interaction when static research is insufficient | P01-P24 |
| OpenAI Developers | Plugin | ACTIVE_NOW | OpenAI API/agent implementation guidance | P02-F, P04, P14, P23 |
| Codex Security | Plugin | ACTIVE_NOW | security review/scanning/investigation | P03, P04, P24 |
| PostHog | Plugin | ACTIVE_NOW / architecture-dependent | product/LLM analytics if selected | P22, P23 |
| Vercel | Plugin + skills | ACTIVE_NOW / candidate runtime | deployment/hosting/workflow/observability evaluation | P02, P04, P22, P23 |
| Neon | Plugin + skills | ACTIVE_NOW / candidate runtime | Postgres/branch DB/functions/storage evaluation | P02, P04, P06 |
| Supabase | Plugin + skills | ACTIVE_NOW / alternative runtime | Postgres/Auth/Realtime/Storage evaluation | P02, P03, P04, P06 |
| Plugin Management | Skill/tool | ACTIVE_NOW | installed-state, capability and permission governance | P00-P24 |
| Semrush | Plugin | CONDITIONAL | public product/SEO research only if needed | P23 |
| Runway / Higgsfield | Plugins | CONDITIONAL | optional demos/media/onboarding visuals | P23 |
| Sentry skill | CONDITIONAL | error/event inspection if configured/selected | P22 |

## 5. Roadmap phase-by-phase tooling map

### P00 — Charter & Governance

**Roadmap use:** establish source of truth, governance, task/evidence/lock contracts, Linear, tool access and closure rules.

| Tool / capability | Use in P00 | State/action |
|---|---|---|
| GitHub | canonical repository and engineering truth | ACTIVE_NOW |
| Linear | project/milestone/task management | ACTIVE_NOW |
| GitHub Actions | Governance Verify and Branch Hygiene | ACTIVE_NOW |
| Task Contracts / Locks / Evidence | governed execution model | ACTIVE_NOW |
| GitHub Secret Protection / Push Protection | baseline secret defense | ACTIVE_NOW |
| Google Drive / Slack / Gmail / Calendar | collaboration and project operations | ACTIVE_NOW |
| Plugin Management | validate installed connectors/permissions | ACTIVE_NOW |
| TOOLCHAIN-MATRIX | plugin/skill/access authority | CANONICAL |
| Agent A0 / A10 | governance/orchestration and evidence | ACTIVE governance roles |

### P01 — Market / Provider / Compliance Research

**Roadmap use:** market universe, providers, brokers/exchanges, compliance, cost/license/data rights, primary/backup strategy and baseline selection.

| Tool / capability | Use in P01 | State/action |
|---|---|---|
| Exa / native web research | provider/news/research discovery | ACTIVE_NOW |
| Legal Data Hunter | regulations, licensing, jurisdiction evidence | ACTIVE_NOW |
| Blockscout | on-chain research evidence | ACTIVE_NOW |
| Wolfram | quantitative cross-checks where useful | ACTIVE_NOW |
| TinyFish | interactive provider/regulatory web workflows when required | CONDITIONAL |
| Google Sheets / Drive | scorecards and controlled research artifacts | ACTIVE_NOW |
| CCXT | crypto exchange API abstraction candidate | ADOPT_CANDIDATE |
| yfinance | research/context data only | USE_CANDIDATE |
| OpenBB | provider abstraction reference | REFERENCE |
| Market-data provider scorecards | provider selection evidence | CANONICAL P01-B |
| Broker/exchange scorecards | execution-provider selection evidence | CANONICAL P01-C |
| Legal/compliance matrix | eligibility and market/data rights | CANONICAL P01-D |
| OSS Registry | future finance/quant libraries | CANONICAL |
| Frontend Registry | future UI stack candidates | CANONICAL |
| Agent Registry | future agent frameworks | CANONICAL |
| Automation Registry | future workflow engines | CANONICAL |
| Master Tooling Registry | unified capability index | CANONICAL |
| Human Gate | Owner jurisdiction / commercial terms where required | HUMAN_GATE |

### P02 — Master Architecture

**Roadmap use:** module boundaries, data flow, signal/risk/execution architecture, agent authority, environments/network/DR and capacity.

| Tool / capability | Use in P02 | State/action |
|---|---|---|
| ADR | major architecture decisions | BASELINE_STANDARD |
| C4-style diagrams | context/container/module architecture | BASELINE_STANDARD |
| Figma diagram skills / Mermaid-class diagrams | architecture visualization | ACTIVE_NOW |
| OpenAPI | API contract architecture | BASELINE_STANDARD |
| AsyncAPI | event/stream contract architecture | BASELINE_STANDARD |
| JSON Schema / typed contracts | machine-boundary schemas | BASELINE_STANDARD |
| OpenTelemetry | telemetry architecture | ADOPT_CANDIDATE |
| OpenTofu | IaC architecture candidate | ADOPT_CANDIDATE |
| NTP/chrony-class time discipline | event-time correctness | BASELINE_STANDARD |
| Temporal | durable workflow architecture candidate | ADOPT_CANDIDATE |
| Vercel / Neon / Supabase | hosting/backend topology evaluation | CANDIDATES |
| OpenAI Agents SDK | primary lightweight orchestration candidate | ADOPT_CANDIDATE, especially P02-F |
| Microsoft Agent Framework | orchestration alternative | ALTERNATIVE |
| LangGraph | stateful/checkpoint workflow candidate | USE_CANDIDATE |
| PydanticAI | typed Python specialist-agent candidate | USE_CANDIDATE |
| MCP / A2A | interoperability evaluation | CONDITIONAL |
| TradingAgents / FinRobot | finance-agent architecture patterns | ADAPT_REFERENCE |
| CrewAI / Semantic Kernel | collaboration/orchestration patterns | REFERENCE |

### P03 — Security & Identity

**Roadmap use:** threat model, RBAC/MFA/session/device policy, secrets/KMS, private admin, audit integrity and supply-chain security.

| Tool / capability | Use in P03 | State/action |
|---|---|---|
| Open Policy Agent (OPA) | policy-as-code / centralized authorization candidate | ADOPT_CANDIDATE |
| Vault or selected cloud KMS/Secret Manager | secrets and privileged access | ADOPT/USE_CANDIDATE + LICENSE_REVIEW |
| GitHub Secret Protection | repository secret scanning | ACTIVE_NOW |
| Codex Security | security analysis | ACTIVE_NOW |
| Syft | SBOM generation candidate | ADOPT_CANDIDATE |
| CycloneDX | SBOM format/analysis | ADOPT_CANDIDATE |
| SLSA-class provenance | supply-chain provenance standard | BASELINE_STANDARD |
| Better Auth | frontend auth/session/2FA/passkey candidate | P03 review before P23 adoption |
| Supabase Auth / other auth provider | architecture alternative | CONDITIONAL |
| Promptfoo | prompt/tool abuse and injection red-team candidate | EVAL_CANDIDATE |
| Inspect AI | reproducible model/agent security evals | EVAL_CANDIDATE |
| MCP/A2A security rules | identity/auth/tool-boundary threat review | CONDITIONAL |
| Legal Data Hunter | legal/security/compliance research support | ACTIVE_NOW |

### P04 — Engineering Foundation

**Roadmap use:** runtime/version baseline, CI/CD, configuration, mocks, testing harness, SBOM/license/dependency policy and reproducible builds.

| Tool / capability | Use in P04 | State/action |
|---|---|---|
| GitHub Actions | CI/CD foundation | ACTIVE_NOW |
| Context7 | exact current library/API docs | ACTIVE_NOW |
| OpenAPI / AsyncAPI / JSON Schema | contract tests and generation | BASELINE_STANDARD |
| OpenTofu | IaC implementation if selected | ADOPT_CANDIDATE |
| GHCR / GitHub Packages-class registry | container/package artifacts | USE_CANDIDATE |
| Schema-validated config | config-as-code | BASELINE_STANDARD |
| dev/test/staging/prod separation | environment policy | BASELINE_STANDARD |
| Syft + CycloneDX | SBOM generation/review | ADOPT_CANDIDATE |
| Cosign | artifact signing | ADOPT_CANDIDATE |
| SLSA | build provenance | BASELINE_STANDARD |
| OPA | policy enforcement if selected | ADOPT_CANDIDATE |
| OpenFeature | feature-flag standard candidate | USE_CANDIDATE |
| deterministic fixtures/mocks/clocks | test foundation | BASELINE_STANDARD |
| Temporal / Kestra / Trigger.dev | workflow/background-job selection as architecture requires | CANDIDATES |
| OpenAI Agents SDK / LangGraph / PydanticAI | exact agent runtime/version selection after P02-F | DEFERRED_TO_SELECTION |
| OSS dependencies | exact pin/license/SBOM/CVE review | PHASE_GATE |

### P05 — Real-Time Data

**Roadmap use:** Crypto/Forex adapters, normalization, event streaming, heartbeat, failover, time semantics and load/latency validation.

| Tool / capability | Use in P05 | State/action |
|---|---|---|
| CCXT | crypto adapter abstraction candidate | ADOPT_CANDIDATE |
| Provider-native APIs/WebSockets | authoritative venue behavior | PHASE_SELECTION |
| AsyncAPI | event/stream contract | BASELINE_STANDARD |
| JSON Schema | canonical market event validation | BASELINE_STANDARD |
| OpenTelemetry | ingestion latency/error/freshness traces | ADOPT_CANDIDATE |
| NTP/chrony | timestamp discipline | BASELINE_STANDARD |
| Dagster | ingestion/data workflow candidate where appropriate | ADOPT_CANDIDATE |
| Prefect / Airflow | alternative pipeline orchestrators | ALTERNATIVE |
| Kestra | event/schedule operations if distinct need exists | USE_CANDIDATE |
| OpenLineage | pipeline lineage candidate | ADOPT_CANDIDATE |
| data-quality framework | early freshness/schema checks | USE_CANDIDATE |
| k6-class tooling | throughput/load/soak benchmark later in phase | USE_CANDIDATE + LICENSE_REVIEW |

### P06 — Historical Data & Feature Store

**Roadmap use:** raw archive, backfill, historical queries, dataset versioning, macro vintage, features and replay interfaces.

| Tool / capability | Use in P06 | State/action |
|---|---|---|
| Apache Arrow | in-memory columnar data interchange | ADOPT_CANDIDATE |
| Apache Parquet | historical analytical storage format | ADOPT_CANDIDATE |
| OpenLineage | dataset/pipeline lineage | ADOPT_CANDIDATE |
| Great Expectations / Soda-class | data-quality framework | USE_CANDIDATE |
| Dagster | backfill/assets/features pipeline orchestration | ADOPT_CANDIDATE |
| Prefect / Airflow | alternatives to Dagster | ALTERNATIVE |
| Feast | feature-store candidate | USE_CANDIDATE |
| Neon/Supabase/selected DB | metadata/query store candidate | ARCHITECTURE_DEPENDENT |
| object storage | immutable raw/archive datasets | PHASE_SELECTION |
| deterministic replay engine | core project capability | PROJECT_CORE |
| deterministic synthetic fixtures | historical/replay tests | BASELINE_STANDARD |

### P07 — Data Quality & Provenance

**Roadmap use:** missing/duplicate/stale/outlier/sequence checks, cross-provider validation, provenance/confidence, quarantine and fail-closed routing.

| Tool / capability | Use in P07 | State/action |
|---|---|---|
| Great Expectations / Soda-class | schema/completeness/quality checks | USE_CANDIDATE |
| OpenLineage | provenance / upstream-downstream lineage | ADOPT_CANDIDATE |
| OpenTelemetry | freshness/error/quality telemetry | ADOPT_CANDIDATE |
| Provider scorecards / cross-provider feeds | validation evidence | CANONICAL INPUT |
| A2 Data / Data Quality specialist agent | anomaly triage/evidence | GOVERNED AGENT |
| Dagster data checks | pipeline quality gates if Dagster selected | CONDITIONAL |
| quarantine/dead-letter pattern | fail-closed invalid data | BASELINE_STANDARD |

### P08 — Technical Intelligence

**Roadmap use:** technical feature families, regime models, independence/correlation audit and validation.

| Tool / capability | Use in P08 | State/action |
|---|---|---|
| Microsoft Qlib | quant/ML research benchmark/candidate | ADOPT_CANDIDATE |
| Machine Learning for Trading | feature/validation reference | REFERENCE |
| VectorBT | exploratory vectorized research | LICENSE_RISK / REFERENCE until reviewed |
| Wolfram | independent numerical/statistical checks | ACTIVE_NOW |
| Python scientific stack | indicators/models/statistics | PHASE_SELECTION |
| A4 Quant / Technical specialists | evidence generation | GOVERNED AGENTS |
| MLflow | optional early experiment tracking if justified | DEFER/ADOPT later |
| common evidence contract | no direct trading output | BASELINE_STANDARD |

### P09 — Volume / Order Flow / Liquidity

**Roadmap use:** Delta/CVD, volume profile, order book, spread/depth, liquidity heatmap, OI/funding/liquidation and proxy confidence.

| Tool / capability | Use in P09 | State/action |
|---|---|---|
| exchange-native order-book/trade APIs | primary crypto microstructure data | PHASE_SELECTION |
| broker/futures/ECN proxy feeds | Forex volume proxy context | PHASE_SELECTION |
| CCXT | selected exchange abstraction where semantics are preserved | CANDIDATE |
| Arrow/Parquet | microstructure data storage/analysis | if selected |
| A3/A4 Order-Flow/Liquidity specialist | analysis/evidence | GOVERNED AGENT |
| OpenTelemetry | latency/backpressure/data gaps | standard instrumentation |

### P10 — Fundamental / Macro / Event Intelligence

**Roadmap use:** official macro sources, revisions/vintages, surprise engine, rates/yields, oil/gold and crypto fundamentals/on-chain.

| Tool / capability | Use in P10 | State/action |
|---|---|---|
| Fed/FRED/ALFRED/BLS/BEA/CFTC | official US macro sources | OFFICIAL_FIRST |
| ECB/Eurostat, BoE, BoJ | official regional macro | OFFICIAL_FIRST |
| BIS/IMF/World Bank | global macro | OFFICIAL_FIRST |
| EIA/OPEC/IEA | oil/energy context | OFFICIAL_FIRST |
| WGC/LBMA | gold context | OFFICIAL_FIRST |
| Blockscout | EVM on-chain evidence | ACTIVE_NOW |
| Exa | discovery/supporting research | ACTIVE_NOW |
| TinyFish | browser interaction if official site workflow requires | CONDITIONAL |
| Legal Data Hunter | regulation/document discovery | ACTIVE_NOW |
| A3 Macro/Fundamental/On-chain specialists | synthesis with provenance | GOVERNED AGENTS |
| Dagster/automation runtime | scheduled official-data ingestion if selected | PHASE_DEPENDENT |

### P11 — News & Sentiment

**Roadmap use:** news ingestion, dedupe, entity mapping, sentiment, importance, reliability, rumor control and decay.

| Tool / capability | Use in P11 | State/action |
|---|---|---|
| Exa | news/research discovery | ACTIVE_NOW |
| licensed news provider(s) | production ingestion | P01/P11 SELECTION |
| official announcements | primary evidence | OFFICIAL_FIRST |
| TinyFish | interactive browser extraction if required | CONDITIONAL |
| A3 News/Sentiment specialist | evidence synthesis | GOVERNED AGENT |
| Promptfoo / Inspect AI | adversarial prompt/news evaluation | EVAL_CANDIDATE |
| n8n | bounded external notification/integration only if selected | CONDITIONAL + LICENSE_REVIEW |

### P12 — Market Memory & Knowledge Graph

**Roadmap use:** correlations, lead/lag, event studies, historical analogs, seasonality and attribution.

| Tool / capability | Use in P12 | State/action |
|---|---|---|
| Qlib / Python scientific stack | research on relationships/regimes | CANDIDATE |
| Blockscout | on-chain entity/evidence context | ACTIVE_NOW |
| Exa | historical event/source discovery | ACTIVE_NOW |
| Parquet/Arrow | historical analytical datasets | if selected |
| deterministic replay | validation of historical relationships | PROJECT_CORE |
| A3/A4 Historical Analog specialist | analog search/evidence | GOVERNED AGENT |
| lineage/provenance metadata | prevent causality/attribution ambiguity | BASELINE_STANDARD |

### P13 — Timing & Opportunity

**Roadmap use:** sessions, opportunity scanner/ranking, no-trade windows, expiry/no-chase and scenarios.

| Tool / capability | Use in P13 | State/action |
|---|---|---|
| project event/session/calendar service | trading-session truth | PROJECT_CAPABILITY |
| Qlib / Python models | ranking/scoring research | CANDIDATE |
| MLflow | experiment tracking if model-based ranking is used | ADOPT_CANDIDATE |
| A3/A4 Opportunity specialists | ranking evidence | GOVERNED AGENTS |
| deterministic feature/data contracts | repeatable timing decisions | BASELINE_STANDARD |

### P14 — Signal / Probability / Explainability

**Roadmap use:** evidence fusion, calibrated probability, uncertainty, TP/Stop probability, Persian explanations and red-team challenge.

| Tool / capability | Use in P14 | State/action |
|---|---|---|
| Qlib / scikit-learn-class tooling | probability/scoring candidates | CANDIDATE |
| FinRL | experimental challenger only | USE_CANDIDATE |
| MLflow | experiment/evaluation tracking | ADOPT_CANDIDATE |
| Feast | feature serving consistency if needed | USE_CANDIDATE |
| Wolfram | calibration/statistical cross-check | ACTIVE_NOW |
| OpenAI Agents SDK / selected agent runtime | governed reasoning/explanation orchestration | only after P02/P04 selection |
| Promptfoo / Inspect AI | agent/model eval and red-team | EVAL_CANDIDATE |
| TradingAgents / FinRobot patterns | challenge/debate/verification reference | ADAPT_REFERENCE |
| model/agent provenance envelope | source/data/model/code traceability | BASELINE_STANDARD |

### P15 — Risk & Portfolio

**Roadmap use:** sizing, asset/strategy/portfolio limits, leverage, drawdown/risk-of-ruin, counterparty and defensive modes.

| Tool / capability | Use in P15 | State/action |
|---|---|---|
| Wolfram / Python statistical stack | risk calculations/cross-checks | ACTIVE/CANDIDATE |
| Qlib portfolio concepts | research benchmark/reference | CANDIDATE |
| A5 Risk Agent | independent risk veto | CANONICAL AGENT |
| OPA | centralized risk/policy rule evaluation if selected | CANDIDATE |
| OpenTelemetry | risk decision latency/errors | STANDARD |
| evidence/audit store | immutable risk decisions | BASELINE_STANDARD |

### P16 — Pre-Trade Risk Firewall

**Roadmap use:** final freshness, price drift, duplicate, size/leverage, liquidity, health and daily-loss gates.

| Tool / capability | Use in P16 | State/action |
|---|---|---|
| A5 Risk Agent | independent veto | CANONICAL |
| A8 Security / A9 Operations | security/system-health gates | CANONICAL |
| OPA / deterministic rules engine | policy enforcement candidate | ADOPT_CANDIDATE |
| JSON Schema / typed contracts | signal/order-plan validation | BASELINE_STANDARD |
| idempotency store/keys | duplicate prevention | PROJECT_CORE |
| OpenTelemetry | gate latency/status telemetry | STANDARD |
| Human Gate | required overrides/critical changes where policy says so | HUMAN_GATE |

### P17 — Backtesting / Strategy Factory

**Roadmap use:** deterministic backtests, realistic execution costs, anti-leakage, OOS, Walk-Forward, Monte Carlo, capacity and registries.

| Tool / capability | Use in P17 | State/action |
|---|---|---|
| Microsoft Qlib | research/backtest/ML candidate | ADOPT_CANDIDATE |
| QuantConnect LEAN | event/execution lifecycle benchmark | REFERENCE |
| NautilusTrader | event-driven/backtest/execution candidate | USE_CANDIDATE + LGPL review |
| VectorBT | exploratory sweeps | LICENSE_RISK |
| Freqtrade | strategy/protection reference | LICENSE_RISK |
| Machine Learning for Trading | research/validation reference | REFERENCE |
| FinRL | experimental RL challengers | USE_CANDIDATE |
| MLflow | experiment/model tracking | ADOPT_CANDIDATE |
| Feast | feature-store candidate if needed | USE_CANDIDATE |
| Dagster | backtest/evaluation pipeline orchestration | ADOPT_CANDIDATE |
| Promptfoo / Inspect AI | agent/model eval where applicable | EVAL_CANDIDATE |
| deterministic replay | backtest correctness/reproducibility | PROJECT_CORE |
| Wolfram | statistical validation | ACTIVE_NOW |

### P18 — Continuous Demo Learning

**Roadmap use:** demo trading, journal/outcomes, dataset curation, experiments, retraining, champion/challenger, drift and promotion governance.

| Tool / capability | Use in P18 | State/action |
|---|---|---|
| MLflow | experiment/model lifecycle | ADOPT_CANDIDATE |
| Dagster | training/retraining pipeline orchestration | ADOPT_CANDIDATE |
| Temporal | long-running gated promotion workflows if selected | ADOPT_CANDIDATE |
| Feast | feature consistency if needed | USE_CANDIDATE |
| FinRL | sandbox challenger research | USE_CANDIDATE |
| A7 Learning Agent | outcomes/drift/challenger coordination | CANONICAL AGENT |
| A10 Evidence | model/strategy promotion evidence | CANONICAL AGENT |
| Human Gate | automatic live promotion remains forbidden | HUMAN_GATE |

### P19 — Shadow / Replay / Digital Twin

**Roadmap use:** shadow decisions, raw/decision/incident replay, digital twin fills/slippage and paper/live drift.

| Tool / capability | Use in P19 | State/action |
|---|---|---|
| deterministic replay engine | primary replay capability | PROJECT_CORE |
| NautilusTrader / LEAN patterns | execution simulation reference | CANDIDATE/REFERENCE |
| Parquet/Arrow | replay datasets | if selected |
| OpenTelemetry | shadow/live comparison traces | STANDARD |
| MLflow | model/version comparison evidence | if selected |
| A10 Evidence | replay/determinism evidence | CANONICAL |

### P20 — Execution & OMS

**Roadmap use:** broker/exchange adapters, OMS lifecycle, idempotency, retry/recovery, reconciliation and execution-quality metrics.

| Tool / capability | Use in P20 | State/action |
|---|---|---|
| CCXT | crypto execution adapter candidate | ADOPT_CANDIDATE after venue validation |
| NautilusTrader | event-driven OMS/execution candidate/reference | USE_CANDIDATE + LGPL review |
| LEAN | OMS/execution lifecycle reference | REFERENCE |
| broker/exchange native SDK/API | authoritative production semantics | PHASE_SELECTION |
| Temporal | durable order/reconciliation workflows if selected | ADOPT_CANDIDATE |
| JSON Schema / typed contracts | order/fill/reconciliation contracts | BASELINE_STANDARD |
| OpenTelemetry | execution latency/failure traces | STANDARD |
| A6 Execution Agent | governed execution/reconciliation role | CANONICAL |
| A5/A8 vetoes | cannot be bypassed | CANONICAL |

### P21 — Position Management

**Roadmap use:** TP/SL, partial close, break-even/trailing/dynamic exits and broker reconciliation.

| Tool / capability | Use in P21 | State/action |
|---|---|---|
| broker/exchange native APIs | authoritative position/order state | PHASE_SELECTED |
| CCXT / selected adapter | crypto adapter if validated | CANDIDATE |
| Temporal | durable position-management workflow if appropriate | CONDITIONAL |
| deterministic state machine | position lifecycle | PROJECT_CORE |
| A5 Risk / A6 Execution | risk/position action governance | CANONICAL AGENTS |
| OpenTelemetry | lifecycle/reconciliation telemetry | STANDARD |

### P22 — Operations / Diagnostics / Recovery

**Roadmap use:** metrics/logs/traces, diagnostics, self-healing, backup/restore, DR and incident/postmortem management.

| Tool / capability | Use in P22 | State/action |
|---|---|---|
| OpenTelemetry | canonical telemetry standard | ADOPT/STANDARD |
| Grafana-class backend | dashboards/metrics if selected | CONDITIONAL |
| Sentry | error tracking candidate | CONDITIONAL |
| PostHog | product/LLM analytics where appropriate | CONDITIONAL |
| Vercel Observability | if Vercel selected | CONDITIONAL |
| Temporal | incident/recovery/approval workflows | ADOPT_CANDIDATE |
| Kestra | event/schedule/ops automation | USE_CANDIDATE |
| n8n | bounded external notifications/integrations | USE_CANDIDATE + LICENSE_REVIEW |
| Windmill | internal ops workflows/scripts | CONDITIONAL + LICENSE_REVIEW |
| k6 | load/stress/soak | USE_CANDIDATE + LICENSE_REVIEW |
| Toxiproxy/project failure harness | dependency/network fault injection | USE_CANDIDATE |
| Chaos Mesh | Kubernetes chaos only if K8s selected | CONDITIONAL |
| Runbooks / incident playbooks | diagnostics/recovery procedures | BASELINE_STANDARD |
| FinOps telemetry | cost/usage monitoring | BASELINE_STANDARD |
| A9 Operations | operations/incident authority | CANONICAL |
| A10 Evidence | incident/postmortem evidence | CANONICAL |

### P23 — UX / Team / Notifications

**Roadmap use:** Persian RTL product, dashboards/markets/trades/research/reports/system/settings, collaboration and notifications.

| Tool / capability | Use in P23 | State/action |
|---|---|---|
| Next.js + React + TypeScript | app framework candidate direction | ADOPT_CANDIDATE |
| shadcn/ui | product design-system primitives | ADOPT_CANDIDATE |
| Better Auth | auth/security UX | ADOPT_CANDIDATE after P03 |
| TradingView Lightweight Charts | financial charts | ADOPT_CANDIDATE |
| TanStack Table | data grids | ADOPT_CANDIDATE |
| TanStack Query | server-state/cache | ADOPT_CANDIDATE |
| React Hook Form | forms | ADOPT_CANDIDATE |
| Zod | frontend/schema validation | ADOPT_CANDIDATE |
| Tremor | KPI/dashboard/report primitives | USE_CANDIDATE |
| Motion | restrained animation | USE_CANDIDATE |
| Lucide | icons | USE_CANDIDATE + license verify |
| Figma + Figma skills | design source of truth/design-to-code | ACTIVE_NOW |
| Vercel skills | Next.js/bootstrap/shadcn/deployment verification if selected | AUTHORIZED_WHEN_TRIGGERED |
| OpenFeature | feature flags | USE_CANDIDATE |
| PostHog | product analytics/experiments if selected | CONDITIONAL |
| n8n / Gmail / Slack | notification/integration paths | CONDITIONAL |
| Canva / Gamma / Adobe | reporting/onboarding/stakeholder artifacts | AUXILIARY |
| Semrush | public SEO only if public surface exists | CONDITIONAL |
| Runway / Higgsfield | optional demo/media assets | CONDITIONAL |
| browser/E2E/visual regression tooling | critical flow/UI validation | BASELINE_STANDARD |
| accessibility/WCAG tooling | accessibility validation | BASELINE_STANDARD |

### P24 — Controlled Production

**Roadmap use:** Manual Live → Semi-Auto → Micro-Capital → Canary → Controlled Auto under Owner gate.

| Tool / capability | Use in P24 | State/action |
|---|---|---|
| Human/Owner Gate | G13 live approval | HUMAN_GATE |
| A5 Risk / A8 Security / A9 Operations / A10 Evidence | independent production safety/evidence | CANONICAL |
| OPA / deterministic policy engine | enforce production rules if selected | CANDIDATE |
| OpenTelemetry | full production telemetry | STANDARD |
| k6 / load tooling | final capacity validation | CANDIDATE |
| fault-injection / Chaos Mesh if relevant | recovery/chaos validation | CONDITIONAL |
| deterministic replay | production incident/recovery validation | PROJECT_CORE |
| Cosign / SLSA / SBOM | release integrity | P04-selected controls |
| Runbooks / DR / backup restore | final readiness evidence | BASELINE_STANDARD |
| broker/exchange sandbox/testnet | final controlled validation before capital | REQUIRED WHERE AVAILABLE |
| kill-switches | strategy/asset/market/broker/global halt | PROJECT_CORE |
| Live Trading | only after G13 Owner approval | DISABLED UNTIL HUMAN_GATE |
| Auto Trading | only controlled, after explicit gates | DISABLED UNTIL HUMAN_GATE |

## 6. Named repository inventory and main roadmap use

### Finance / quant / trading repositories

| Repository | Classification | Main roadmap use |
|---|---|---|
| `microsoft/qlib` | ADOPT_CANDIDATE | P08, P13, P14, P17 |
| `QuantConnect/Lean` | REFERENCE | P17, P19, P20 |
| `nautechsystems/nautilus_trader` | USE_CANDIDATE | P17, P19, P20 |
| `AI4Finance-Foundation/FinRL` | USE_CANDIDATE | P14, P17, P18 |
| `ccxt/ccxt` | ADOPT_CANDIDATE | P05, P09, P20, P21 |
| `freqtrade/freqtrade` | LICENSE_RISK / REFERENCE | P17 |
| `polakowo/vectorbt` | LICENSE_RISK | P08, P17 |
| `ranaroussi/yfinance` | RESEARCH_ONLY | P01, early research |
| `stefan-jansen/machine-learning-for-trading` | REFERENCE | P08, P14, P17 |
| OpenBB/OpenBQ transition | REFERENCE | P01 provider abstraction research |

### Frontend repositories

| Repository | Classification | Main roadmap use |
|---|---|---|
| `vercel/next.js` | ADOPT_CANDIDATE | P23 |
| `shadcn-ui/ui` | ADOPT_CANDIDATE | P23 |
| `better-auth/better-auth` | ADOPT_CANDIDATE | P03, P23 |
| `tradingview/lightweight-charts` | ADOPT_CANDIDATE | P23 |
| `TanStack/table` | ADOPT_CANDIDATE | P23 |
| `TanStack/query` | ADOPT_CANDIDATE | P23 |
| `react-hook-form/react-hook-form` | ADOPT_CANDIDATE | P23 |
| `colinhacks/zod` | ADOPT_CANDIDATE | P04, P23 |
| `motiondivision/motion` | USE_CANDIDATE | P23 |
| `tremorlabs/tremor` | USE_CANDIDATE | P23 |
| `lucide-icons/lucide` | USE_CANDIDATE / license verify | P23 |

### Agent / AI repositories and protocols

| Repository / protocol | Classification | Main roadmap use |
|---|---|---|
| OpenAI Agents SDK | ADOPT_CANDIDATE | P02-F, P04, P14, P22, P23 |
| Microsoft Agent Framework | ALTERNATIVE | P02-F |
| LangGraph | USE_CANDIDATE | P02-F, P04 |
| PydanticAI | USE_CANDIDATE | P02-F, P04, P14 |
| CrewAI | REFERENCE | P02-F |
| Semantic Kernel | REFERENCE | P02-F |
| TradingAgents | ADAPT_REFERENCE | P02-F, P14 |
| FinRobot | ADAPT_REFERENCE | P02-F, P14, P17 |
| MCP | INTEROP_CANDIDATE | P02-F, P03, P04 |
| A2A | INTEROP_CANDIDATE | P02-F, P03, P04 |
| Promptfoo | EVAL_CANDIDATE | P03, P14, P17, P24 |
| Inspect AI | EVAL_CANDIDATE | P03, P14, P17, P24 |
| Phoenix | OBSERVABILITY_CANDIDATE | P22 |
| Langfuse | OBSERVABILITY_CANDIDATE | P22 |

### Automation repositories

| Repository | Classification | Main roadmap use |
|---|---|---|
| GitHub Actions | EXISTING_CANONICAL | P00-P24 |
| Temporal | ADOPT_CANDIDATE | P02, P04, P18, P20, P22 |
| Dagster | ADOPT_CANDIDATE | P05, P06, P17, P18 |
| Kestra | USE_CANDIDATE | P04, P22 |
| n8n | USE_CANDIDATE + LICENSE_REVIEW | P22, P23 |
| Prefect | ALTERNATIVE | P05, P06 |
| Airflow | REFERENCE / ALTERNATIVE | P05, P06 |
| Trigger.dev | SPECIALIST_CANDIDATE | P04, P23 |
| Windmill | SPECIALIST + LICENSE_REVIEW | P22 |

## 7. Standards / infrastructure / security / data / ML inventory

| Tool / standard | State | Roadmap use |
|---|---|---|
| OpenAPI | BASELINE_STANDARD | P02, P04, service contracts thereafter |
| AsyncAPI | BASELINE_STANDARD | P02, P05, event-driven phases thereafter |
| JSON Schema | BASELINE_STANDARD | P02, P04, P05+ |
| OpenTelemetry | ADOPT/STANDARD | P02, P05+, P22-P24 |
| OPA | ADOPT_CANDIDATE | P03, P04, P15, P16, P24 |
| OpenTofu | ADOPT_CANDIDATE | P02, P04 |
| Vault / cloud KMS/Secret Manager | CANDIDATE / LICENSE_REVIEW | P03, P04 |
| OpenLineage | ADOPT_CANDIDATE | P05-P07 |
| Great Expectations / Soda-class | USE_CANDIDATE | P05-P07 |
| Apache Arrow | ADOPT_CANDIDATE | P06+ |
| Apache Parquet | ADOPT_CANDIDATE | P06+ |
| MLflow | ADOPT_CANDIDATE | P13/P14, P17, P18, P19 |
| Feast | USE_CANDIDATE | P06, P14, P17, P18 |
| OpenFeature | USE_CANDIDATE | P04, P23 |
| Syft | ADOPT_CANDIDATE | P03, P04 |
| CycloneDX | ADOPT_CANDIDATE | P03, P04 |
| Cosign | ADOPT_CANDIDATE | P04, P24 |
| SLSA-class provenance | BASELINE_STANDARD | P04, P24 |
| GHCR / GitHub Packages | USE_CANDIDATE | P04 |
| NTP / chrony-class | BASELINE_STANDARD | P02, P05 |
| k6-class | USE_CANDIDATE + LICENSE_REVIEW | P05, P22, P24 |
| Toxiproxy/project failure harness | USE_CANDIDATE | P22, P24 |
| Chaos Mesh | CONDITIONAL | P22, P24 if Kubernetes selected |
| ADR | BASELINE_STANDARD | P02-P24 major decisions |
| C4-style architecture | BASELINE_STANDARD | P02 and architecture changes |
| Runbooks / Playbooks | BASELINE_STANDARD | P22, P24 |
| FinOps telemetry | BASELINE_STANDARD | P04, P22+ |
| deterministic replay | PROJECT_CORE | P06, P17, P19, P24 |
| synthetic deterministic fixtures | BASELINE_STANDARD | P04, P06+ |

## 8. Skills and where they are triggered

| Skill family | Main roadmap use |
|---|---|
| Figma Design-to-Code / Generate Design / Generate Library / Generate Diagram | P02 diagrams, P23 design system/UI |
| Google Drive / Docs / Sheets / Slides / Comments | P00-P24 collaboration/evidence/reporting |
| Vercel Next.js / Bootstrap / React Best Practices / shadcn | P04/P23 if Vercel/Next.js path selected |
| Vercel AI SDK / AI Gateway / AI Elements | P02-F/P04/P14/P23 if selected |
| Vercel Workflow / Queues / Cron / Functions | P04/P22/P23 if Vercel selected |
| Vercel Deployments / CI-CD / Verification / Investigation / Observability | P04/P22/P24 |
| Vercel Firewall / Sandbox | P03/P22 if Vercel selected |
| Vercel Flags | P04/P23 |
| Neon Postgres / Functions / Object Storage / AI Gateway | P02/P04/P06 and AI gateway evaluation |
| Supabase / Postgres Best Practices | P02/P03/P04/P06 alternative backend evaluation |
| Sentry | P22 error/incident inspection if configured |
| Plugin Management | P00-P24 capability/access governance |

## 9. Automatic-use rule

At the start of each roadmap phase, A0 must:

1. read this document and the Master Tooling Registry;
2. select the tools mapped to the current phase;
3. re-check current health/version/license/security/cost;
4. compare overlapping candidates;
5. add only justified tools to the phase Task Contract;
6. install/configure only after the relevant roadmap/security/dependency gates permit it;
7. mark each candidate as `SELECT`, `PILOT`, `DEFER`, `REJECT`, or `NOT_APPLICABLE`;
8. record evidence and rollback/exit strategy.

**The Owner does not need to remind the project which registered tool belongs to which phase.**

## 10. Anti-sprawl and authority rules

- Registered does not mean installed.
- Connected plugin does not mean production dependency.
- GitHub/Linear/Figma/Drive-style project tools do not automatically become runtime dependencies.
- Prefer one primary tool per overlapping capability with a documented fallback.
- Human/Owner gates cannot be auto-approved by an Agent or Automation.
- A5 Risk and A8 Security vetoes cannot be bypassed.
- Live Trading and unrestricted Auto Trading remain disabled until their explicit roadmap gates and Owner approval.

## 11. Current project position

As of 2026-10-03:

- Tooling arsenal: `READY / PASS`.
- Active broad runtime build: not yet authorized.
- Current roadmap phase: P01.
- Next canonical workstream: P01-E — Cost / Licensing / Data Rights.
- Production technology selections: not implied by this document.
- Runtime installations from this documentation task: none.


## 12. Security tooling overlay

Canonical source:
- `docs/03-research/SECURITY-TOOLING-REGISTRY.md`
- `docs/00-governance/SECURITY-TOOLING-BASELINE.md`
- Task: `FIN-P01-WS-001`
- Linear: `HOS-152`

### P03 — Security & Identity
- GitHub CodeQL — primary SAST candidate.
- Trivy — broad vulnerability / misconfiguration / secret / SBOM scan candidate.
- Semgrep — NEXUS-specific custom security-rule candidate.
- Syft + CycloneDX — SBOM.
- OPA — policy-as-code.
- Secret Manager/KMS or governed Vault-class solution — secrets/key lifecycle.
- Promptfoo + Inspect AI — agent/LLM prompt and tool-abuse evaluation.
- Codex Security — assisted review.

### P04 — Engineering Foundation
- CodeQL/selected SAST -> CI security gate.
- Trivy -> dependency/image/config scan.
- Syft/CycloneDX -> SBOM generation and evidence.
- Grype -> optional independent SBOM vulnerability verification.
- Cosign + SLSA-class provenance -> artifact signing/provenance.
- OPA -> deterministic policy gate when selected.
- Semgrep -> custom rules where justified.

### P22 — Operations / Diagnostics / Recovery
- Trivy -> governed image/artifact/runtime-adjacent checks where selected.
- Falco -> runtime threat detection only if architecture/topology benefits.
- security incident runbooks, evidence, alerting and credential-revocation procedures.

### P23 — UX / Team / Notifications
- OWASP ZAP -> authorized API/web DAST and attack-surface validation.
- authentication/session/header/cookie/CSP validation according to selected architecture.

### P24 — Controlled Production
- SAST/CVE/SBOM/signing/provenance/DAST/agent-security/runtime/recovery evidence.
- independent A8 Security verification.
- unresolved Critical security state or A8 veto blocks production eligibility.

Anti-overlap:
- CodeQL primary SAST; Semgrep custom rules.
- Trivy primary broad scanner; Grype optional independent check.
- Falco conditional.
- one primary secrets manager and one primary policy engine unless measured evidence justifies otherwise.
