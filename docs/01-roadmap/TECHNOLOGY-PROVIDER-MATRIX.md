# Finance / NEXUS QUANT — Technology & Provider Candidate Matrix

STATE = GOVERNED_COMPANION  
TASK = `FIN-P00-WE-001`  
PRODUCTION_SELECTIONS = NOT_YET_AUTHORIZED

## 1. Purpose

This matrix records **candidate** technologies, providers and official sources that later phases must evaluate. Listing a candidate does not select it.

Before a candidate becomes a production dependency, the responsible roadmap task must document:
- requirements fit;
- reliability / SLA / failure modes;
- security and credential model;
- regional and legal availability;
- licensing/data rights;
- pricing and exit cost;
- rate limits/capacity;
- backup/failover strategy;
- test/sandbox support;
- observability and operational burden;
- migration/portability plan.

Current commercial availability, price and jurisdiction support must be revalidated at selection time.

## 2. Application / runtime candidates

| Capability | Candidate baseline | Alternatives / notes | Selection phase | State |
|---|---|---|---|---|
| Web application | TypeScript + React + Next.js | other React frameworks only with clear benefit | P02/P04/P23 | TBD |
| Core API/services | TypeScript/Node.js where operationally simple | Python service where Quant/data library ecosystem materially helps | P02/P04 | TBD |
| Quant/research | Python | NumPy, pandas/Polars, SciPy, statsmodels, scikit-learn; exact stack selected by benchmark | P02/P04/P17 | TBD |
| Validation schemas | JSON Schema / typed contracts | Pydantic/Zod/OpenAPI/AsyncAPI as appropriate | P02/P04 | TBD |
| API style | REST for control-plane; streaming/event protocols for market paths | gRPC/WebSocket/SSE based on latency and tooling needs | P02 | TBD |
| Frontend styling/components | CSS/Tailwind + accessible component primitives | shadcn/ui candidate; Figma design system remains source for UX intent | P23 | TBD |
| Package/workspace | exact tool selected in P04 | monorepo preferred if it minimizes private-team complexity | P04 | TBD |

## 3. Database / storage candidates

| Data class | Candidates | Evaluation focus | Phase | State |
|---|---|---|---|---|
| Relational control-plane | PostgreSQL | correctness, migrations, HA, backup, branching, portability | P02/P04 | TBD |
| Managed Postgres candidate | Neon | branch-first workflows, compute/storage separation, operations | P02/P04 | CANDIDATE |
| Managed Postgres/backend candidate | Supabase | Postgres, Auth, Realtime, Storage, Edge Functions, RLS | P02/P04 | CANDIDATE |
| High-volume analytical/time-series | PostgreSQL extensions, ClickHouse-class analytical store, dedicated TSDB if justified | ingest/query profile, compression, retention, operations | P02/P06 | TBD |
| Cache / ephemeral state | Redis-compatible service | latency, HA, persistence expectations | P02/P04 | TBD |
| Raw object archive | S3-compatible object storage | immutability/versioning/lifecycle/egress/restore | P02/P06 | TBD |
| Feature store | build on versioned DB/object storage first | adopt dedicated product only if complexity is justified | P06 | TBD |
| Graph / market memory | relational graph modeling first; graph DB only if demonstrated need | query patterns, replay/versioning, ops complexity | P12 | TBD |

**Rule:** Neon and Supabase are both installed ChatGPT tools, but neither is selected production infrastructure.

## 4. Messaging / streaming / workflow candidates

| Capability | Candidates | Selection criteria | Phase |
|---|---|---|---|
| Internal event streaming | in-process/modular queue first; NATS/Redpanda/Kafka-class only if measured need | throughput, ordering, replay, ops cost | P02/P05 |
| Durable jobs/workflows | application job queue, Temporal-class workflow, Vercel Workflow if platform chosen | crash safety, retries, visibility, portability | P02/P04/P22 |
| Scheduled jobs | system scheduler / managed cron / Vercel Cron if selected | reliability, drift, auditability | P04/P22 |
| Task queue/cache | Redis-compatible queue candidates | idempotency, retries, delayed jobs | P04 |

Avoid introducing distributed infrastructure before load/availability requirements prove it necessary.

## 5. Real-time / historical market-data candidates

Candidate names below are **research targets**, not approved providers.

### Crypto

Potential categories to evaluate:
- exchange-native WebSocket/REST APIs for venue-specific truth;
- major exchanges such as Binance, Coinbase, Kraken and other regionally eligible venues;
- aggregator/data vendors such as Kaiko, CoinAPI, Amberdata-class or equivalent;
- CCXT/CCXT Pro as an adapter abstraction candidate where exchange-native behavior remains inspectable.

Evaluate:
- trades, L1/L2/L3 depth;
- spot/perpetual/futures;
- funding/open interest/liquidations;
- timestamps/sequence IDs;
- historical depth availability;
- redistribution/storage rights;
- sandbox/testnet behavior;
- regional eligibility.

### Forex / context markets

Candidate categories:
- broker-native APIs such as OANDA-class or other eligible broker APIs;
- institutional/market-data vendors such as Polygon/Massive, Twelve Data, Tiingo, Databento-class or equivalent;
- futures/exchange-derived proxies for centralized volume context;
- context feeds for DXY, yields, indices, commodities where license permits.

Forex evaluation must explicitly label whether volume is:
- broker-specific;
- tick volume;
- futures-derived proxy;
- ECN-specific;
- aggregated proxy.

No provider is allowed to imply consolidated global Spot FX volume.

## 6. Official macro / fundamental source baseline

Official-first sources are preferred whenever available.

| Domain | Primary official sources / source classes | Phase |
|---|---|---|
| United States macro | Federal Reserve, FRED/ALFRED, BLS, BEA, CFTC, U.S. Treasury where relevant | P10 |
| Euro area | ECB, Eurostat | P10 |
| United Kingdom | Bank of England, ONS where relevant | P10 |
| Japan | Bank of Japan, official statistics sources | P10 |
| Global macro | BIS, IMF, World Bank | P10 |
| Oil / energy | EIA, OPEC, IEA | P10 |
| Gold | World Gold Council, LBMA, exchange/market data where licensed | P10 |
| Crypto protocol/on-chain | exchange-native/protocol-native sources plus validated on-chain evidence | P10 |
| EVM on-chain research support | Blockscout plugin/data | P01/P10/P12 |

For economic releases, store:
- expected/forecast when legitimately sourced;
- first released value;
- previous value as known at release time;
- later revisions;
- source timestamp and retrieval timestamp.

## 7. News / research candidates

| Capability | Candidate/source class | Rule |
|---|---|---|
| Web/research discovery | Exa, native web research | discovery only; evaluate source quality |
| Interactive browser workflow | TinyFish | use when website interaction is actually needed |
| Financial news providers | licensed provider(s) selected in P01/P11 | redistribution/use rights required |
| Official announcements | central banks, statistical agencies, regulators, exchanges, issuers | preferred primary evidence |
| Legal/regulatory research | Legal Data Hunter + official registries | LDH supports discovery; official text wins when available |

Rumor/social sources can provide context but cannot independently trigger a trade.

## 8. Quant / ML / model lifecycle candidates

| Capability | Candidate class | Phase | State |
|---|---|---|---|
| Numerical/statistical validation | Python scientific stack; Wolfram for independent exact cross-checks | P08/P14/P17 | CANDIDATE |
| Traditional ML | scikit-learn-class tooling | P14/P17 | TBD |
| Gradient boosting | XGBoost/LightGBM-class if justified | P14/P17 | TBD |
| Deep learning | PyTorch-class only if simpler models are insufficient | P14/P17 | DEFER_BY_DEFAULT |
| Experiment tracking | MLflow-class or equivalent; PostHog is not a model registry substitute | P17/P18 | TBD |
| Model registry | dedicated registry or governed database/object artifacts | P17 | TBD |
| LLM integration | OpenAI or alternative providers behind controlled interface/gateway | P02/P14/P23 | TBD |
| LLM routing | direct SDK or gateway such as Vercel AI Gateway/Neon AI Gateway if architecture selects it | P02/P04 | TBD |

Principle: use the simplest model that demonstrates robust out-of-sample value.

## 9. Backtesting / simulation candidates

The project may evaluate:
- a custom deterministic event-driven backtest core;
- established open-source engines where they preserve data provenance and execution realism;
- vectorized research libraries for exploratory analysis only;
- broker/exchange sandbox simulators;
- deterministic replay from canonical raw data.

Selection criteria:
- no hidden lookahead;
- event-time correctness;
- partial fills;
- fees/spread/funding;
- latency/slippage;
- capacity/liquidity assumptions;
- reproducible random seeds;
- traceability to dataset and strategy versions.

## 10. Observability / operations candidates

| Capability | Candidates | Rule |
|---|---|---|
| Logs / metrics / traces | OpenTelemetry-first instrumentation; selected backend later | telemetry should remain portable |
| Product / LLM analytics | PostHog if selected | not a substitute for trading audit logs |
| App/platform observability | Vercel Observability if Vercel selected | architecture-dependent |
| Error tracking | Sentry candidate; skill requires configured token | optional until selected |
| Dashboards | Grafana-class or managed equivalent | selected by P22 |
| Alert delivery | in-app + email baseline; optional Slack/Telegram/push | escalation policy in P23 |

Trading/audit records must not depend solely on a third-party product analytics platform.

## 11. Security candidates

| Capability | Candidate class / tool | Notes |
|---|---|---|
| Secret scanning | GitHub Secret Protection / Push Protection | already active for repository |
| Code/security analysis | Codex Security plus CI scanners selected in P03/P04 | findings require evidence-backed closure |
| Dependency/CVE | GitHub/native scanners and SBOM tooling | policy defined P03/P04 |
| Secrets vault/KMS | cloud/vendor-neutral secret manager selected after architecture | no plaintext repo secrets |
| WAF/DDoS | hosting/provider controls; Vercel Firewall if Vercel selected | P03/P22 |
| Private admin | VPN/private network/device controls as justified | P03 |
| Audit integrity | append-only/tamper-evident approach | P03/P22 |

## 12. Execution provider selection criteria

Any broker/exchange selected for Demo/Shadow/Live must be scored on:
- legal/regional eligibility;
- demo/sandbox parity;
- stable API and documented order lifecycle;
- client order IDs/idempotency;
- order/fill/reject/cancel event quality;
- reconciliation endpoints;
- rate-limit transparency;
- maintenance/outage history;
- symbol metadata;
- margin/leverage controls;
- API-key permission granularity;
- withdrawal permission can be absent/disabled;
- operational support and incident visibility.

Smart routing/multi-broker execution is deferred until a single path is proven.

## 13. Hosting / deployment candidates

The architecture phase should compare:
- Vercel for application/UI/serverless/workflow-oriented parts;
- conventional cloud/VPS/container deployment for persistent streaming and market-data services;
- managed Postgres via Neon/Supabase or another provider;
- hybrid placement when 24/7 WebSocket/long-running services require different characteristics from UI/API workloads.

Kubernetes is not a default. Adopt only when measured operational/scale requirements justify its complexity.

## 14. Provider decision record template

Each production selection must record:

```text
Capability:
Selected provider/technology:
Decision date:
Task/ADR:
Environment(s):
Primary / backup:
Why selected:
Alternatives evaluated:
Security findings:
Regional/legal findings:
Data/license findings:
Cost assumptions:
Rate/capacity limits:
Failure modes:
Exit/migration plan:
Revalidation trigger:
```

## 15. Current selection state

At `FIN-P00-WE-001`:
- no production market-data provider is selected;
- no live broker/exchange is selected;
- no production database/backend is selected;
- no production hosting topology is selected;
- no production LLM provider is selected as trading authority;
- no real-capital credentials exist by roadmap authorization;
- LIVE_TRADING remains DISABLED;
- AUTO_TRADING remains DISABLED.


## 16. Governed open-source repository registry

Wave-1 open-source finance/quant/trading candidates are tracked in:

- `docs/03-research/OPEN-SOURCE-REPOSITORY-DEPENDENCY-REGISTRY.md`
- `docs/03-research/open-source-repository-dependency-registry.json`
- Task: `FIN-P01-WR-001`
- Linear: `HOS-110`

The registry distinguishes direct adoption candidates from bounded-use candidates, architecture/reference projects and license-risk projects.

Current notable classifications:
- Microsoft Qlib: `ADOPT_CANDIDATE`
- CCXT: `ADOPT_CANDIDATE`
- NautilusTrader: `USE_CANDIDATE` with LGPL review
- FinRL: `USE_CANDIDATE` for experimental RL
- QuantConnect LEAN: `REFERENCE`
- Machine Learning for Trading: `REFERENCE`
- Freqtrade: `LICENSE_RISK` / GPL-3.0
- VectorBT: `LICENSE_RISK` pending exact license-term review
- yfinance: `USE_CANDIDATE` for research only, not production market-data backbone
- OpenBB: `REFERENCE` during stewardship transition

These labels are research classifications only. They do not authorize installation, production use, market-data rights, broker connectivity or live execution.


## 17. Frontend UI/UX and excellence baseline

The governed frontend repository registry and non-library quality baseline are tracked in:

- `docs/03-research/FRONTEND-UI-UX-REPOSITORY-REGISTRY.md`
- `docs/03-research/frontend-ui-ux-repository-registry.json`
- `docs/03-research/FRONTEND-EXCELLENCE-BASELINE.md`
- Task: `FIN-P01-WU-001`
- Linear: `HOS-112`

This baseline covers:
- design system / Figma / design tokens;
- RTL Persian and LTR financial islands;
- performance budgets, SSR/streaming/caching/realtime strategy;
- accessibility and visualization rules;
- visual regression, E2E, contract and performance testing;
- frontend observability;
- feature flags;
- mock/contract-first development;
- internationalization/timezone/number formatting;
- PWA/offline candidate behavior;
- personalization;
- security UX;
- font/asset optimization;
- component preview and engineering productivity.

No runtime dependency or production technology is selected by this section. Exact implementation remains governed by P02/P03/P04/P22/P23/P24.


## 18. Agent frameworks, ready agents and interoperability

Governed candidate registry:

- `docs/03-research/AGENT-FRAMEWORK-READY-AGENT-REGISTRY.md`
- `docs/03-research/agent-framework-ready-agent-registry.json`
- `docs/09-agents/AGENT-GOVERNANCE-INTEGRATION.md`
- Task: `FIN-P01-WG-001`
- Linear: `HOS-113`

Current research direction:
- OpenAI Agents SDK: `ADOPT_CANDIDATE` for lightweight orchestration, handoffs, guardrails and tracing.
- Microsoft Agent Framework: `ALTERNATIVE_CANDIDATE`.
- LangGraph: `USE_CANDIDATE` for durable/stateful workflows where justified.
- PydanticAI: `USE_CANDIDATE` for typed Python specialist agents.
- TradingAgents and FinRobot: `ADAPT_REFERENCE` for financial multi-agent patterns; no direct execution authority.
- MCP and A2A: `INTEROP_CANDIDATE`.
- Promptfoo and Inspect AI: `EVAL_CANDIDATE`.
- Phoenix and Langfuse: observability candidates requiring exact license/privacy review.

Final framework selection and authority implementation are deferred to P02-F/P04. Listing does not authorize package installation, model credentials, broker connectivity, Live Trading or Auto Trading.


## 19. Automation and orchestration

Governed registry:
- `docs/03-research/AUTOMATION-ORCHESTRATION-REGISTRY.md`
- `docs/03-research/automation-orchestration-registry.json`
- `docs/00-governance/AUTOMATION-GOVERNANCE.md`
- Task: `FIN-P01-WO-001`
- Linear: `HOS-116`

Research direction:
- GitHub Actions: existing canonical CI/governance automation.
- Temporal: `ADOPT_CANDIDATE` for critical durable workflows.
- Dagster: `ADOPT_CANDIDATE` for data/quant/ML pipelines.
- Kestra: `USE_CANDIDATE` for event/schedule/operations workflows.
- n8n: `USE_CANDIDATE` for external integrations, subject to license/security review.
- Prefect: `ALTERNATIVE_CANDIDATE`.
- Airflow: `REFERENCE / ALTERNATIVE_CANDIDATE`.
- Trigger.dev: `SPECIALIST_CANDIDATE`.
- Windmill: `SPECIALIST_CANDIDATE` with license review.

No runtime installation or production selection is authorized by this registry. Final choices belong to P02/P04 and the owning implementation phases.


## 20. Project capability & tooling master registry

Canonical master index:
- `docs/03-research/PROJECT-CAPABILITY-TOOLING-MASTER-REGISTRY.md`
- `docs/03-research/project-capability-tooling-master-registry.json`
- `docs/00-governance/PHASE-TOOLING-ACTIVATION-POLICY.md`
- `docs/02-current-state/BUILD-READINESS-CHECKLIST.md`
- Task: `FIN-P01-WM-001`
- Linear: `HOS-118`

This index unifies the project capability arsenal across:
- plugins/connectors/skills;
- open-source repositories;
- frontend/UI/UX;
- agents and interoperability;
- automation/orchestration;
- standards/contracts;
- policy-as-code;
- infrastructure-as-code;
- secrets/IAM/KMS;
- observability;
- data quality/lineage/formats/replay;
- ML lifecycle/model registry/feature store;
- software supply-chain/SBOM/signing/provenance;
- feature flags/configuration;
- load/failure/chaos testing;
- runbooks, incident response, FinOps and evidence.

The Phase Tooling Activation Policy requires A0 to automatically re-evaluate applicable registered capabilities at the start of their owning roadmap phase. This does not authorize premature installation or production selection.
