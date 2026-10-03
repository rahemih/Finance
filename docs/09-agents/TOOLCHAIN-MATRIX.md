# Finance — Canonical Toolchain / Plugin / Skill / Access Matrix

State: `ACTIVE`  
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

## 12. Change control

Changes to this matrix require a governed Task Contract and PR. Tool availability may change independently at the platform level; when that occurs, CURRENT-STATE and Linear must be reconciled rather than silently assuming continued access.
