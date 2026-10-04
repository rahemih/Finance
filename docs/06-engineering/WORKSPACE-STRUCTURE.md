# NEXUS QUANT — Repository / Workspace Structure

STATE = P04-A IMPLEMENTATION
TASK = `FIN-P04-WA-001`
LINEAR = `HOS-172`
ARCHITECTURE_BASELINE = `FROZEN_G2`
SECURITY_GATE = `G3_SECURITY_BASELINE = PASS`

## 1. Decision

NEXUS QUANT uses **one governed polyglot monorepo**.

Why:
- private team scope is <=10 users;
- governance, evidence and cross-domain contracts benefit from one Source of Truth;
- TypeScript/application and Python/quant workloads can coexist without forcing premature service/repository splits;
- FROZEN_G2 requires logical domain isolation, not one repository or service per domain;
- strong physical-isolation candidates may be extracted later only when latency, security, availability or operational evidence justifies it.

This is a **modular-core-first** structure. Directory boundaries are ownership and dependency boundaries, not automatic microservices.

## 2. Canonical top-level layout

```text
/
├─ apps/          deployable composition roots / user-facing or process entrypoints
├─ packages/      provider-neutral reusable production modules
├─ adapters/      external provider/vendor SDK boundaries
├─ quant/         governed production-grade quant/statistical Python modules
├─ research/      experiments/notebooks/exploration; never a production dependency
├─ config/        schema-governed non-secret configuration
├─ infra/         infrastructure/deployment definitions selected by later tasks
├─ tests/         cross-workspace integration/contract/replay/security harnesses
├─ contracts/     repository governance contracts and canonical task schemas
├─ docs/          roadmap, architecture, security, engineering and evidence
├─ scripts/       repository/governance automation
└─ .github/       GitHub workflows, templates and repository automation
```

Build output, caches, local environments, downloaded datasets and secrets are not canonical source directories.

## 3. Zone responsibilities

### `apps/`

Composition roots only.

Future examples may include:
- Persian web application;
- control/API process;
- background worker;
- physically isolated execution or agent process if later architecture evidence requires it.

Rules:
- apps wire modules together;
- business authority stays in owning packages/domains;
- apps do not become a dumping ground for reusable domain logic;
- UX/API entrypoints cannot import broker/provider SDKs except through explicitly authorized adapter composition.

### `packages/`

Provider-neutral reusable production code.

Reserved internal package families:
- `contracts` — machine-boundary schemas/types and compatibility rules;
- `core` — modular domain/application logic aligned with D01–D18;
- `platform` — generic runtime abstractions such as clock, IDs, persistence ports and queue abstractions;
- `security` — authorization/security-context interfaces and policy integration points;
- `observability` — telemetry/audit/evidence interfaces.

Exact package names and language-specific workspace files are P04-B scope.

### `adapters/`

All provider/vendor-specific translation ends here.

Examples later:
- market-data providers;
- broker/exchange execution;
- macro/news/on-chain providers;
- model/LLM/tool providers;
- databases/object stores/queues when implementation-specific adapters are required.

Rules:
- vendor SDK imports are allowed here, not in core domain logic;
- adapters implement provider-neutral ports/contracts;
- provider symbols/order IDs remain outside provider-neutral intent/domain contracts;
- execution adapters cannot bypass Risk or Pre-Trade Firewall.

### `quant/`

Production-grade Python quant/statistical/model implementation boundary.

Rules:
- may consume canonical contracts and validated data interfaces;
- cannot directly call broker/exchange APIs;
- cannot self-promote models to Live;
- no research notebook becomes a production dependency merely by residing in the repository.

### `research/`

Exploration only:
- notebooks;
- experiments;
- benchmarks;
- prototypes;
- temporary analysis.

Hard rule:

> Production paths (`apps/`, `packages/`, `adapters/`, `quant/`) MUST NOT import from `research/`.

Promotion from research requires a governed task that moves validated logic into a production zone with tests, provenance and review.

### `config/`

Non-secret configuration contract area.

Rules:
- secret **references/handles** only;
- raw API keys, tokens, passwords, signing keys or broker credentials are forbidden;
- environment-specific configuration must be schema validated in P04-D;
- environment inheritance must never silently widen authority.

### `infra/`

Infrastructure/deployment definitions.

Rules:
- provider selection is not implied by this directory;
- IaC selection belongs to P04/P22 tasks;
- no hidden production credentials;
- environment topology must preserve P03 separation.

### `tests/`

Cross-workspace test harness:
- contract;
- integration;
- replay;
- security;
- deterministic fixtures;
- failure/recovery tests.

Unit tests should remain colocated with owning code when the selected language ecosystem benefits from that convention.

### Existing governed zones

`contracts/`, `docs/`, `scripts/`, and `.github/` remain canonical repository-control zones and are not application-runtime packages.

## 4. Dependency direction

Allowed high-level direction:

```text
apps
 ├─> packages
 ├─> adapters
 └─> quant (through explicit contracts where justified)

adapters
 ├─> packages/contracts
 ├─> packages/core ports
 ├─> packages/platform
 ├─> packages/security
 └─> packages/observability

quant
 ├─> packages/contracts
 └─> provider-neutral data/model interfaces

packages/core
 ├─> packages/contracts
 └─> pure/provider-neutral internal modules

packages/security / packages/observability / packages/platform
 └─> packages/contracts (or lower-level pure utilities)

research
 └─> may consume governed production interfaces for experiments

tests
 └─> may consume any testable governed zone
```

Production dependency cycles across domain ownership boundaries are forbidden.

## 5. FROZEN_G2 invariants preserved by structure

The workspace layout must preserve:

1. Provider details stop at adapters.
2. Strategy/Quant/Signal cannot directly submit broker orders.
3. Execution cannot override A5 Risk or Firewall rejection.
4. Learning/research cannot activate a Live model.
5. Agent runtime cannot directly mutate provider/broker state outside governed domain APIs.
6. UX cannot talk directly to brokers/providers/secrets.
7. One domain cannot write another domain's authoritative state through shared tables as a hidden API.
8. Critical unknown state remains fail closed.
9. A5 Risk and A8 Security veto remain non-bypassable.
10. Country/location is not embedded as a structural dependency.

## 6. Domain placement rule

D01–D18 remain **logical domains** from FROZEN_G2.

Default placement:
- domain/application logic → `packages/core/`;
- cross-domain schemas → `packages/contracts/`;
- vendor/provider implementation → `adapters/`;
- process/deployment composition → `apps/`;
- production quant algorithms → `quant/`;
- exploratory work → `research/`.

A later task may physically extract a domain without changing its authority model.

Strong future extraction candidates remain:
- Market Data Adapters;
- Execution/OMS;
- Agent Control Plane;
- Application API/UX.

Risk + Firewall remain logically independent even if initially hosted in the same process.

## 7. Generated files and build artifacts

Rules:
- source-controlled generated files require an explicit reproducible generator and ownership rule;
- transient build output belongs in ignored directories such as ecosystem-specific `dist/`, `build/`, caches or virtual environments;
- release artifacts belong in an artifact registry/evidence system selected later, not committed to source;
- generated evidence must reference source commit and tool/version once P04-C/F/H activate those controls.

## 8. Secrets and local state

Forbidden in Git:
- `.env` with real secrets;
- broker/exchange API keys;
- signing/private keys;
- database passwords/tokens;
- model-provider credentials;
- raw credential exports;
- production account dumps.

Local development templates may contain **names/placeholders only** once P04-D defines the config contract.

## 9. Testing / evidence placement

- code-local unit tests: alongside owning module according to language convention selected P04-B;
- cross-package integration/contract/security/replay tests: `tests/`;
- canonical phase evidence: `docs/14-evidence/`;
- machine-readable architecture/engineering baselines: appropriate phase-owned `docs/` folder.

Test code must not become runtime authority.

## 10. Naming and ownership

- directory names: lowercase kebab-case where a multiword name is required;
- package/module identifiers: selected language conventions in P04-B;
- one authoritative owner per domain state;
- CODEOWNERS/reviewer enforcement may be added in P04-C if justified by team size and GitHub support.

## 11. Physical service extraction criteria

Create a separately deployable process/service only when at least one is evidenced:
- independent security/credential boundary;
- continuous streaming/fault isolation;
- materially different scaling/runtime requirements;
- independent availability/recovery objective;
- deployment cadence/failure blast radius justifies separation.

A directory is not evidence for a microservice.

## 12. P04-B handoff

P04-B must select exact:
- Node.js runtime;
- TypeScript version;
- Python runtime;
- JS/TS package manager/workspace mechanism;
- Python dependency/virtual-environment manager;
- lockfile policy;
- upgrade cadence and compatibility policy;
- reproducible local environment mechanism.

P04-A intentionally does not select those versions.

## 13. Validation

P04-A passes when:
- one canonical workspace decision exists;
- machine-readable manifest matches this document;
- top-level production/research/adapter boundaries are materialized;
- no forbidden FROZEN_G2 coupling is introduced;
- no dependency/runtime installation is falsely claimed;
- Governance Verify passes.

## 14. Safety

Production dependencies installed by P04-A: NONE  
Production accounts/credentials: NONE  
Market/broker connections: NONE  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED
