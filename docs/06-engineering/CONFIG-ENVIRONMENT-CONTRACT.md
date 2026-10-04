# NEXUS QUANT — Config / Environment Contract

STATE = P04-D CANONICAL_BASELINE
TASK = `FIN-P04-WD-001`
LINEAR = `HOS-175`
DATE = 2026-10-04

## 1. Purpose

P04-D defines how NEXUS QUANT represents configuration and logical environments without storing raw secrets or activating any deployment/trading environment.

Canonical configuration is:
- schema governed;
- deterministic;
- non-secret;
- environment isolated;
- fail closed on unknown/invalid state;
- unable to silently widen execution or credential authority.

## 2. Logical environments

The canonical environment set is exactly:

`DEV / TEST / RESEARCH / DEMO / SHADOW / CANARY / LIVE`

These are logical security/configuration domains, not claims that infrastructure exists.

In P04-D every environment has:

`provisioning_state = CONTRACT_ONLY`

No real GitHub Environment, cloud environment, broker account, secret namespace or runtime deployment is provisioned here.

## 3. Configuration precedence

Lowest to highest:

1. `config/base.json`
2. `config/environments/<environment>.json`
3. approved **non-secret** runtime override
4. opaque secret-handle resolution outside canonical config

Secret resolution is not a JSON merge layer. A secret reference is resolved by a future trusted secret boundary into process memory/capability context; the raw value never becomes canonical config.

## 4. Runtime override boundary

Runtime overrides may change only:
- `settings.log_level`
- `settings.clock_mode`
- `settings.data_mode`

They cannot modify:
- environment identity;
- provisioning state;
- authority ceiling;
- safety flags;
- execution mode;
- external order submission;
- credential authority;
- secret namespace or references.

Unknown override paths fail closed.

## 5. Secret-reference contract

Canonical config stores handles only:

`secret://<environment>/<domain>/<name>@<version-or-alias>`

Examples:
- `secret://dev/market-data/provider-a@current`
- `secret://demo/execution/provider-demo@current`

These are examples only; P04-D provisions no secret.

Rules:
- the environment segment must equal the owning environment;
- DEV/TEST/RESEARCH/DEMO/SHADOW cannot reference CANARY/LIVE namespaces;
- raw API keys, passwords, bearer tokens, client secrets, private keys and broker credentials are forbidden;
- secrets never enter Task Contracts, evidence, logs or canonical config.

## 6. Environment authority ceilings

| Environment | Ceiling | Active execution in P04-D | Credential authority |
|---|---|---|---|
| DEV | SIMULATED_ONLY | DISABLED | unprovisioned |
| TEST | SIMULATED_ONLY | DISABLED | unprovisioned |
| RESEARCH | SIMULATED_ONLY | DISABLED | unprovisioned |
| DEMO | DEMO_ONLY | DISABLED | unprovisioned |
| SHADOW | SHADOW_ONLY | DISABLED | unprovisioned |
| CANARY | CANARY_DISABLED | DISABLED | unprovisioned |
| LIVE | LIVE_DISABLED | DISABLED | unprovisioned |

An authority ceiling is a maximum future capability, not current authorization.

## 7. SHADOW

SHADOW may later consume external read-only market/execution observations, but:
- external order submission = false;
- trading credentials = absent;
- account mutation = absent;
- live execution = absent.

## 8. CANARY and LIVE

P04-D deliberately models CANARY/LIVE while keeping them inert.

Mandatory state:
- `authority_provisioned = false`
- `active_mode = DISABLED`
- `external_order_submission = false`
- `live_trading = false`
- `auto_trading = false`

A config edit alone can never activate them. Future Human Gates, account/provider readiness, Risk/Security gates and deployment controls remain required.

## 9. Location neutrality

Country, IP geolocation, network location or physical location is **not** part of the authorization contract.

P04-D contains no country-specific environment binding.

Compliance/jurisdiction decisions may be evaluated by future governed compliance logic, but location is never a substitute for identity, Risk, Security or Human Gate authorization.

## 10. Versioning and compatibility

Each config artifact carries:
- schema version;
- config version;
- environment identity where applicable.

Unknown schema/config versions fail closed until an explicit compatibility/migration task updates the consumer contract.

## 11. Invalid configuration

Fail closed on:
- unknown environment;
- missing required field;
- extra high-risk field;
- secret namespace mismatch;
- raw secret-like material;
- authority widening;
- CANARY/LIVE enable attempt;
- SHADOW order-submission enable attempt;
- unknown runtime override path.

No fallback silently changes environment or authority.

## 12. CI enforcement

The required `governance` CI context validates:
- all config JSON;
- schema/policy alignment;
- exact environment inventory;
- namespace isolation;
- no raw secret-like content;
- override allowlist;
- safety invariants.

Therefore config drift blocks merge.

## 13. Safety

Real environment provisioned by P04-D: NONE  
Secret manager/KMS/vault provisioned: NONE  
Raw secrets: NONE  
Broker/exchange credentials: NONE  
External order submission: DISABLED  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

## 14. Next

After canonical closure only:

`P04-E — Test Harness`

P04-E is not started by this task.


## 15. Closure evidence

Implementation:
- PR: `#100` = MERGED
- final PR head SHA: `77a023e4b1656b494fb95681371e5722ec1a8340`
- required Governance/Foundation CI: `37204268124` = SUCCESS
- PR foundation artifact: `11304032820`
- PR artifact digest: `sha256:89b1d58c5ab1df91d1334b43327ecb27e704dcbe7b857e804cd8f17cdc8d02ef`
- implementation merge SHA: `36aa699b87f69546e18d99e4500336ab8ba06d55`
- post-merge Governance/Foundation CI: `37204313153` = SUCCESS
- post-merge Branch Hygiene: `37204313208` = SUCCESS
- post-merge foundation artifact: `11304077294`
- post-merge artifact digest: `sha256:8e8d2af0b3b6107c1837d8e98b2cd7dfcc2b472189e2d2719e08f3303529bdec`

Closure:
- `FIN-P04-WD-001 = CANONICAL_COMPLETE`
- `LOCK-FIN-P04-WD-001-01 = RELEASED`
- next workstream = `P04-E — Test Harness`
- P04-E = `NOT_STARTED`
