# Finance — Canonical Toolchain / Plugin / Skill / Access Matrix

State: `CANONICAL`  
Owner: `Hossein Rahemi`  
Operational authority: `A0 — Governance / Orchestrator`  
Task: `FIN-P00-WD-001`  
Effective date: `2026-10-03`

## 1. Purpose

This document defines which external ChatGPT plugins/connectors and skills are approved for project work, what they may be used for, and the boundaries that prevent project-management tooling from becoming an uncontrolled production dependency.

The matrix governs **development, research, project management, design, evidence, security review, and operational support**. It does not authorize live trading, broker execution, exchange withdrawals, model promotion, or bypass of Risk/Security/Governance gates.

## 2. Source-of-truth hierarchy

1. GitHub `main` + merged commit + CI evidence
2. Canonical governance documents and Task Contracts
3. Runtime/deployment evidence
4. Linear operational state when consistent with GitHub
5. External research/plugin output as supporting evidence only

External plugins may provide evidence and research, but they do not override canonical GitHub state.

## 3. Plugin and connector matrix

| Tool | State | Class | Primary project use | Production dependency? | Default authority |
|---|---|---|---|---|---|
| GitHub | ACTIVE | CORE | Repository, PR, CI, evidence, governance | YES for engineering source-of-truth | Governed read/write |
| Linear | ACTIVE | CORE | Project planning, milestones, dependencies, task coordination | NO | Governed read/write |
| Figma | ACTIVE | ENGINEERING/DESIGN | UX, design system, diagrams, design-to-code | NO | Governed design read/write |
| Google Drive | ACTIVE | COLLABORATION | Docs/Sheets/Slides, project artifacts, backups/export support | NO | Governed read/write |
| Slack | ACTIVE | COLLABORATION | Team communication and operational coordination | NO | Governed read/write |
| Vercel | ACTIVE | ENGINEERING/OPS | App deployment, observability, workflows, frontend/backend hosting evaluation | Only if architecture later selects it | Governed; no implicit production mutation |
| Neon | ACTIVE | ENGINEERING/DATA | Postgres, branch databases, functions/storage evaluation | Only if architecture later selects it | Governed; branch-first |
| Context7 | ACTIVE | ENGINEERING/RESEARCH | Current library/API documentation and code examples | NO | Read-only research |
| OpenAI Developers | ACTIVE | AI ENGINEERING | OpenAI API setup and implementation guidance | Only if architecture selects OpenAI runtime | Governed |
| PostHog | ACTIVE | OBSERVABILITY/PRODUCT | Product analytics, experiments, logs, LLM analytics | Only if architecture selects it | Governed |
| Codex Security | ACTIVE | SECURITY | Security scans, analysis and investigation | NO | Security analysis; no gate bypass |
| Blockscout Blockchain Data | ACTIVE | DOMAIN INTELLIGENCE | EVM on-chain data, wallets, transactions, tokens, contracts and ABI evidence | NO | Read-only intelligence |
| Exa | ACTIVE | DOMAIN INTELLIGENCE | Financial/news/research-paper/web discovery and evidence gathering | NO | Read-only research |
| Wolfram | ACTIVE | QUANT/VALIDATION | Exact mathematics, statistics, symbolic/numerical validation | NO | Read-only computation |
| Legal Data Hunter | ACTIVE | COMPLIANCE/RESEARCH | Laws, cases, regulatory documents and jurisdiction research | NO | Read-only legal research |
| Gmail | ACTIVE | COLLABORATION | Project email workflows and later notification-support operations | NO | Governed; explicit send actions |
| Google Calendar | ACTIVE | COLLABORATION | Project scheduling and operational coordination | NO | Governed |
| Dropbox | ACTIVE | AUXILIARY | File exchange and secondary artifact storage | NO | Governed |
| Adobe | ACTIVE | AUXILIARY | PDF/document/media workflows | NO | Governed |
| Canva | ACTIVE | AUXILIARY | Presentation/design collateral when useful | NO | Governed |
| Semrush | AVAILABLE/INSTALLED | NON-CORE | Web/SEO research if a future public surface requires it | NO | Use only when task requires |
| Runway | AVAILABLE/INSTALLED | NON-CORE | Optional media generation | NO | Use only when task requires |

### Runtime separation rule

A ChatGPT plugin being `ACTIVE` does **not** mean it is selected as a production provider. Production providers for market data, brokers, exchanges, databases, observability, news, macro data, or execution must be selected by the relevant roadmap task and architecture/risk/security gates.

## 3A. Verified installed useful-plugin inventory

The following installed plugins were independently re-checked on 2026-10-03 and are considered useful to this project, either as baseline tools or as conditional tools for a specific roadmap task.

### Tier A — Core governance / engineering / project operations

| Plugin | Verified | Role in Finance |
|---|---|---|
| GitHub | installed / ACTIVE | Canonical repository, PR, CI, governance and evidence |
| Linear | installed / ACTIVE | Project planning, milestones, dependencies, execution tracking |
| Figma | installed / ACTIVE | UX, diagrams, design system and design-to-code |
| Google Drive | installed / ACTIVE | Docs/Sheets/Slides, evidence packs, exports and controlled backups |
| Slack | installed / ACTIVE | Team coordination and operational communication |
| Context7 | installed / ACTIVE | Current library/API documentation for implementation accuracy |
| OpenAI Developers | installed / ACTIVE | OpenAI API/agent implementation guidance |
| Codex Security | installed / ACTIVE | Security analysis, scanning and investigation |

### Tier B — Engineering / data / runtime candidates

These are useful, but **not selected production dependencies merely because they are installed**.

| Plugin | Verified | Role in Finance |
|---|---|---|
| Vercel | installed / ACTIVE | Deployment, workflow, observability and application hosting evaluation |
| Neon | installed / ACTIVE | Postgres, branching, functions, storage and backend evaluation |
| Supabase | installed / ACTIVE | Alternative Postgres/backend/auth/realtime/storage evaluation |
| PostHog | installed / ACTIVE | Product analytics, experiments, logs and LLM analytics |
| TinyFish | installed / ACTIVE | User-directed browser workflows and web interaction when static research is insufficient |

### Tier C — Market / quant / legal intelligence

| Plugin | Verified | Role in Finance |
|---|---|---|
| Blockscout Blockchain Data | installed / ACTIVE | EVM on-chain intelligence |
| Exa | installed / ACTIVE | Research, financial/news discovery and papers |
| Wolfram | installed / ACTIVE | Exact mathematics/statistics and Quant cross-checking |
| Legal Data Hunter | installed / ACTIVE | Regulatory/legal primary-document discovery and compliance research |

### Tier D — Collaboration / knowledge / reporting

| Plugin | Verified | Role in Finance |
|---|---|---|
| Notion | installed / ACTIVE | Research synthesis and knowledge capture when useful; GitHub remains canonical |
| Gmail | installed / ACTIVE | Project email workflows and later notification support |
| Google Calendar | installed / ACTIVE | Scheduling, review gates and operational coordination |
| Dropbox | installed / ACTIVE | Secondary artifact exchange/storage |
| Adobe | installed / ACTIVE | PDF/document/media production and review |
| Canva | installed / ACTIVE | Presentations and visual communication |
| Gamma | installed / ACTIVE | Project reports, presentations and stakeholder summaries |

### Tier E — Conditional / non-core installed tools

These are useful only for specific scoped tasks and must not be treated as baseline runtime dependencies.

| Plugin | Verified | Permitted project use |
|---|---|---|
| Semrush | installed / ACTIVE | SEO/traffic research only if a public documentation/product surface is later introduced |
| Runway | installed / ACTIVE | Optional media generation for demos, onboarding or documentation |
| Higgsfield | installed / ACTIVE | Optional branded visuals/media/prototypes |

### Selection rule

If two installed plugins overlap, the relevant architecture/task must select one based on requirements, cost, security, data residency, reliability, operability and exit strategy. Installation status is never an architecture decision.

For example:
- `Neon` and `Supabase` are both useful candidates; no production database/backend has been selected yet.
- `Google Drive`, `Dropbox` and `Notion` can all store project material, but only GitHub canonical governance artifacts define engineering truth.
- `Exa`, `TinyFish` and native web research have different roles; browser automation should be used only when interaction is required.

## 4. Skill matrix

Skills do not require a separate always-on installation toggle. They are **AUTHORIZED_FOR_USE_WHEN_TRIGGERED** and must be loaded/invoked only when the relevant task calls for them.

| Skill family | State | Use |
|---|---|---|
| Vercel AI SDK | AUTHORIZED_WHEN_TRIGGERED | Structured output, tools, agents, streaming, embeddings |
| Vercel AI Gateway | AUTHORIZED_WHEN_TRIGGERED | Model routing/failover/cost control evaluation |
| Vercel Workflow | AUTHORIZED_WHEN_TRIGGERED | Durable workflows, retry/pause/resume orchestration |
| Vercel Cron Jobs | AUTHORIZED_WHEN_TRIGGERED | Scheduled tasks when Vercel is selected |
| Vercel Deployments / CI-CD | AUTHORIZED_WHEN_TRIGGERED | Deployment and promotion workflows |
| Vercel Observability | AUTHORIZED_WHEN_TRIGGERED | Logs, traces, metrics, OpenTelemetry |
| Vercel Firewall | AUTHORIZED_WHEN_TRIGGERED | WAF, DDoS/rate-limit controls |
| Vercel Verification | AUTHORIZED_WHEN_TRIGGERED | End-to-end flow verification |
| Vercel Investigation Mode | AUTHORIZED_WHEN_TRIGGERED | Structured incident/debug triage |
| Vercel Environment Variables | AUTHORIZED_WHEN_TRIGGERED | Environment/secrets configuration guidance |
| Neon Postgres | AUTHORIZED_WHEN_TRIGGERED | Database architecture, branching, pooling, migrations |
| Neon Functions | AUTHORIZED_WHEN_TRIGGERED | Long-running APIs, SSE/WebSocket/webhook workloads |
| Neon Object Storage | AUTHORIZED_WHEN_TRIGGERED | S3-compatible file/object storage evaluation |
| Figma Design-to-Code | AUTHORIZED_WHEN_TRIGGERED | Production implementation from Figma |
| Figma Generate Design | AUTHORIZED_WHEN_TRIGGERED | Application screens/views into Figma |
| Figma Generate Library | AUTHORIZED_WHEN_TRIGGERED | Tokens, variables, component/design systems |
| Figma Generate Diagram | AUTHORIZED_WHEN_TRIGGERED | Architecture, ERD, flow, sequence, state diagrams |
| Google Drive | AUTHORIZED_WHEN_TRIGGERED | Connected Docs/Sheets/Slides/Drive workflows |
| Sentry | CONDITIONAL | Read-only error/issue inspection after `SENTRY_AUTH_TOKEN` is configured |
| Plugin Management | AUTHORIZED_WHEN_TRIGGERED | Plugin discovery, connection status and permission governance |

## 4A. Expanded skill inventory

The following skill families are present and useful to Finance. They are **not always-on services**; they are loaded only when a task trigger matches.

### Vercel skills — authorized when relevant

High-value project skills include:
- `agent-browser` and `agent-browser-verify` — browser-based UI/runtime verification;
- `ai-sdk`, `ai-gateway`, `ai-elements`, `ai-generation-persistence` — AI runtime and model-routing patterns;
- `auth`, `env-vars` — identity/configuration guidance;
- `bootstrap`, `nextjs`, `shadcn`, `react-best-practices` — application foundation and UI quality;
- `cron-jobs`, `vercel-functions`, `vercel-queues`, `workflow` — scheduled, serverless, asynchronous and durable workloads;
- `deployments-cicd`, `verification`, `investigation-mode`, `observability` — deployment, validation, incident triage and telemetry;
- `vercel-firewall`, `vercel-sandbox` — WAF/DDoS and isolated execution guidance;
- `vercel-flags` — staged rollout/feature-flag patterns;
- `vercel-services`, `vercel-storage` — service/storage architecture when Vercel is selected.

Other Vercel skills remain available but are used only when a concrete task requires them.

### Neon skills — authorized when relevant

- `neon`
- `neon-postgres`
- `neon-functions`
- `neon-object-storage`
- `neon-ai-gateway`

These are evaluation/implementation aids only until an architecture task selects Neon.

### Supabase skills — authorized when relevant

- `supabase`
- `supabase-postgres-best-practices`

These are useful for database, Auth, Realtime, Edge Functions, Storage, RLS and Postgres optimization. Supabase remains an architecture candidate, not a selected production dependency.

### Figma skills — authorized when relevant

- `figma-code-connect`
- `figma-create-new-file`
- `figma-design-to-code`
- `figma-generate-design`
- `figma-generate-diagram`
- `figma-generate-library`
- `figma-use`

Additional Figma motion/shader/Slides/SwiftUI skills remain task-specific.

### Google Drive skills — authorized when relevant

- `google-drive`
- `google-docs`
- `google-sheets`
- `google-slides`
- `google-drive-comments`

### Sentry skill — conditional

- `sentry` is available for read-only issue/event inspection when `SENTRY_AUTH_TOKEN` is configured.
- Sentry itself is not currently declared a connected baseline production dependency.

### Plugin Management skill

- `plugin-management` is authorized for discovery, installed-state verification, dependency inspection and permission governance.
- It may not silently elevate a plugin to blanket Full Access.

### Skill governance rule

A skill may improve implementation quality, but it never expands an agent's authority. The effective permission set is the intersection of:

`Task Contract ∩ Agent Registry ∩ Toolchain Matrix ∩ Environment Policy ∩ Risk/Security/Owner Gates`.

## 5. Agent-to-tool routing

| Agent | Preferred tool families | Boundary |
|---|---|---|
| A0 Governance / Orchestrator | GitHub, Linear, Drive, Slack | Cannot bypass gates or Risk/Security |
| A1 Architecture | GitHub, Context7, Exa, Figma diagrams, Vercel/Neon docs | No live orders |
| A2 Data | GitHub, Context7, Neon, Exa, Blockscout | No trade execution |
| A3 Market Intelligence | Exa, Blockscout, Wolfram, Legal Data Hunter | Intelligence only; no execution |
| A4 Quant | Wolfram, GitHub, Context7, Exa | Cannot self-promote model/strategy to Live |
| A5 Risk | GitHub, Wolfram, Exa, Legal Data Hunter | Risk veto; cannot alter own ceilings |
| A6 Execution | GitHub, Context7, infrastructure tools selected later | Cannot override Risk/Firewall |
| A7 Learning | GitHub, Wolfram, PostHog where relevant | No auto-promotion to Live |
| A8 Security | Codex Security, GitHub, Vercel Firewall, security evidence tools | No trade decision authority |
| A9 Operations | GitHub, Vercel/Neon/PostHog/Sentry when selected/configured | No risk-policy changes |
| A10 Evidence & Audit | GitHub, Linear, Drive, Exa/LDH for evidence | Cannot implement and self-approve critical change |

## 6. Access policy

### Read actions

Read-only research and documentation lookups may be performed automatically when relevant to an authorized task.

### Write actions

Writes to GitHub, Linear, Figma, Drive, Slack, infrastructure or other connected systems must:
- be directly tied to the active Task Contract;
- remain inside declared write scope;
- preserve audit evidence;
- not bypass required status checks, rulesets, Risk, Security, or Owner Gates.

### High-impact actions

The following remain prohibited without their explicit roadmap gate and Owner authority:
- enable Live Trading;
- enable unrestricted Auto Trading;
- increase risk/leverage ceilings outside approved policy;
- rotate or alter production broker/exchange credentials;
- add withdrawal permissions;
- auto-promote a model or strategy to Live;
- disable Risk Engine, Pre-Trade Firewall, security controls, audit logging or kill switches.

## 7. Least-privilege policy

- Do not set all plugins to blanket `Full Access` merely for convenience.
- Prefer read-only access where the task is research/analysis.
- Use write access only for governed project-management or engineering tasks.
- Never store API keys, passwords, broker credentials, private keys, seed phrases or withdrawal-capable credentials in GitHub docs, Linear issues, chat documents, or evidence comments.
- Trading API credentials must eventually be separated by environment and must not include withdrawal authority.
- Every critical external action must be attributable and auditable.

## 8. Research-evidence policy

Research tools such as Exa, Blockscout, Wolfram and Legal Data Hunter are supporting sources. Their outputs must retain:
- source/provenance;
- retrieval timestamp when relevant;
- market/jurisdiction/network context;
- confidence/limitations;
- distinction between primary evidence and derived interpretation.

For macro/fundamental data, official-first source policy remains mandatory. A search plugin does not replace Fed/FRED/ALFRED, BLS, BEA, CFTC, ECB/Eurostat, BoE, BoJ, BIS, IMF, World Bank, EIA/OPEC/IEA, WGC/LBMA or exchange-native evidence when those primary sources are available.

## 9. Security and compliance rules

- Legal Data Hunter provides research support, not autonomous legal authority.
- Blockscout data is on-chain evidence and must not be treated as identity proof without independent evidence.
- Wolfram calculations can validate mathematics/statistics but do not by themselves validate data provenance or trading edge.
- Exa discovery results require source-quality assessment.
- Codex Security/Strix-style security tooling may identify findings, but remediation and closure still require repository evidence and appropriate gates.
- Security agent A8 and Risk agent A5 retain independent veto authority in their domains.

## 10. Deferred / task-specific tools

Do not add plugins merely because they exist. New tools are added when they provide a concrete capability not already covered, materially improve accuracy/reliability, and pass security/governance review.

Examples that remain task-specific rather than baseline dependencies:
- additional market-data vendors;
- broker/exchange connectors;
- dedicated observability vendors;
- dedicated message/notification services;
- alternative databases/data warehouses;
- marketing/CRM tools.

## 11. Verified project-specific additions

Verified on 2026-10-03:

- `Blockscout Blockchain Data = installed / ACTIVE`
- `Exa = installed / ACTIVE`
- `Wolfram = installed / ACTIVE`
- `Legal Data Hunter = installed / ACTIVE`

These four tools are approved for immediate project **research/analysis** use within the boundaries above.

## 12. Canonical evidence

- Linear issue: `HOS-104`
- Implementation PR: `#8`
- Implementation merge SHA: `64b79dc053e63c1bc82e5894c041aad3f1fe626b`
- PR Governance run: `37113173645` = SUCCESS
- Post-merge Governance run: `37113198691` = SUCCESS

## 13. Change control

Changes to this matrix require a governed Task Contract and PR. Tool availability may change independently at the platform level; when that occurs, CURRENT-STATE and Linear must be reconciled rather than silently assuming continued access.


## Agent runtime and interoperability candidate policy

Task `FIN-P01-WG-001` records agent-runtime candidates separately from ChatGPT plugins/connectors.

Candidate families:
- OpenAI Agents SDK — primary orchestration candidate for later P02-F evaluation;
- Microsoft Agent Framework — production/polyglot alternative candidate;
- LangGraph — durable/stateful workflow candidate;
- PydanticAI — typed Python specialist candidate;
- TradingAgents / FinRobot — finance-domain patterns to adapt, not trading authority;
- MCP / A2A — interoperability candidates;
- Promptfoo / Inspect AI — agent evaluation/red-team candidates;
- Phoenix / Langfuse — observability candidates subject to exact license/privacy review.

These are not ACTIVE production tools merely because they are listed. The effective authority remains:

`Task Contract ∩ Agent Registry ∩ Toolchain Matrix ∩ Risk/Security Policy ∩ Human/Owner Gates`.

No framework capability may broaden tool permissions or trading authority.
