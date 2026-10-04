# NEXUS QUANT — CI/CD Foundation

STATE = P04-C CANONICAL_BASELINE
TASK = `FIN-P04-WC-001`
LINEAR = `HOS-174`
DATE = 2026-10-04

## 1. Objective

Create an enforced, reproducible CI/CD foundation before configuration, test-harness and market-system work.

P04-C does not deploy NEXUS QUANT. It makes the existing protected-main required status check `governance` an aggregate engineering gate.

## 2. Enforcement decision

Repository ruleset:

- ruleset: `Protect main`
- ruleset ID: `24412077`
- enforcement: `active`
- target: default branch
- required status context: `governance`
- strict required checks: enabled
- merge method: squash
- linear history: required

P04-C intentionally keeps the context name `governance` so the existing active ruleset continues enforcing the job without requiring an administrative ruleset mutation.

The required `governance` job now fails if any P04-C foundation gate fails.

## 3. Aggregate required gates

The required job performs:

1. immutable-SHA checkout;
2. canonical governance baseline verification;
3. PR branch-name verification;
4. exact Node.js runtime setup;
5. exact pnpm activation and frozen lockfile verification;
6. exact Python runtime setup;
7. exact uv setup and locked sync;
8. foundation lint/syntax validation;
9. typecheck-readiness validation;
10. CI foundation unit self-checks;
11. forward Task Contract schema validation;
12. workflow/supply-chain security validation;
13. promotion-disabled fail-closed validation;
14. deterministic foundation manifest build twice + byte comparison;
15. artifact upload.

## 4. Exact CI runtime

Inherited from P04-B:

- Node.js: `24.21.0`
- pnpm: `11.28.4`
- Python: `3.14.8`
- uv: `0.12.23`

TypeScript `7.0.2` remains the approved compiler baseline but no product TypeScript source exists yet.

## 5. Typecheck-readiness semantics

P04-C does **not** falsely claim a product static typecheck while product source does not exist.

The readiness gate scans production zones:

- `apps/`
- `packages/`
- `adapters/`
- `quant/`

If a production `.ts/.tsx/.mts/.cts/.py` source file appears before the corresponding governed typecheck configuration is introduced, the required CI gate fails.

Therefore product code cannot silently enter the repository under a meaningless green “typecheck” placeholder.

A later owning implementation task must configure the real compiler/typechecker before product source is admitted.

## 6. Contract validation strategy

Historical contracts are not retroactively rewritten by P04-C.

Forward policy:

- every JSON file must remain syntactically valid;
- any changed/new `contracts/tasks/*.json` file is validated against the structural constraints of `contracts/schemas/task-contract.schema.json`;
- P04-C's own Task Contract must conform;
- existing historical contracts that are untouched are not silently mutated inside this workstream.

This creates forward enforcement without widening scope into historical governance repair.

## 7. Workflow supply-chain hardening

P03-F requires immutable action pins for trusted workflows.

Canonical action pins used by P04-C:

- `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` — release v7.0.1
- `actions/setup-node@820762786026740c76f36085b0efc47a31fe5020` — release v7.0.0
- `actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97` — release v7.0.0
- `actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` — release v7.0.1
- `actions/github-script@3a2844b7e9c422d3c10d287c895573f7108da1b3` — release v9.0.0 commit
- `astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7` — release v10.2.0

The security gate rejects mutable tag references in repository workflows.

## 8. Least privilege

Governance/Foundation CI:
- `contents: read` only;
- checkout uses `persist-credentials: false`;
- no deployment permission;
- no `id-token: write`;
- no secrets are supplied.

Branch Hygiene retains only the permissions required for its repository branch/issue maintenance:
- `contents: write`
- `issues: write`
- `pull-requests: read`

No broker, vault, signing or production credential is present.

## 9. Dependency verification

JavaScript/TypeScript foundation:

```text
corepack enable
corepack prepare pnpm@11.28.4 --activate
pnpm install --frozen-lockfile --ignore-scripts
```

Python foundation:

```text
uv sync --locked --no-install-project
```

These commands must not mutate committed lockfiles.

P04-F later adds full SCA/SBOM/license enforcement.

## 10. Foundation build evidence

P04-C builds a deterministic JSON manifest containing:

- source commit SHA;
- sorted SHA-256 digests of canonical engineering foundation inputs;
- no timestamp;
- no machine-specific absolute path.

CI builds the manifest twice and requires byte-for-byte equality.

This validates CI artifact mechanics. Full clean-machine/reproducible product-build evidence remains P04-H scope.

## 11. Artifact policy

The foundation manifest is uploaded as a short-retention GitHub Actions artifact for CI evidence.

It is not a production release artifact, deployment bundle or signed production artifact.

Signing/SBOM/provenance enforcement belongs to P04-F/P04-H.

## 12. Promotion policy

P04-C promotion state:

`DISABLED_PENDING_P04_D`

Rules:
- no GitHub environment is referenced by P04-C;
- no deployment permission is granted;
- no OIDC deployment identity is granted;
- no workflow may enable CANARY/LIVE/AUTO_TRADING;
- any unexpected promotion/deployment capability causes the security/promotion check to fail.

P04-D defines configuration/environment contracts. Production progression remains controlled by later roadmap gates.

## 13. Failure behavior

Any required foundation gate failure:

- fails the `governance` status context;
- protected main remains unmergeable under the active ruleset;
- no promotion or fallback path bypasses the failure.

## 14. Safety

Production deployment: NONE  
Production environments created by P04-C: NONE  
Production application dependencies added by P04-C: NONE  
Credentials/accounts/funding/orders: NONE  
CANARY: DISABLED  
LIVE_TRADING: DISABLED  
AUTO_TRADING: DISABLED

## 15. Next

After canonical closure only:

`P04-D — Config / Environment Contract`

P04-D is not started by this task.


## 16. Closure evidence

Implementation:
- PR: `#98` = MERGED
- final PR head SHA: `9b314a437215ff579dee6329cdbbb1e6186ee130`
- required Governance/Foundation CI run: `37203479883` = SUCCESS
- PR foundation artifact: `11303622136`
- PR artifact digest: `sha256:60071ec2269c78b6c2eb58b50fc6248532c90ea7f7e35b8fbef66d837022cc13`
- implementation merge SHA: `c8b47ef563afe58f8746550c8cb70773e4cc1e04`
- post-merge Governance/Foundation CI: `37203519383` = SUCCESS
- post-merge Branch Hygiene: `37203519378` = SUCCESS
- post-merge foundation artifact: `11303617311`
- post-merge artifact digest: `sha256:8cb44cd5ec62cefac90cbe11efb5eb6ff720d051f3218e329f1c84d91f66cd6e`

Enforcement:
- `Protect main` ruleset `24412077` = ACTIVE
- required context `governance` = aggregate P04-C CI gate
- immutable third-party action pins = PASS
- promotion state = `DISABLED_PENDING_P04_D`

Closure:
- `FIN-P04-WC-001 = CANONICAL_COMPLETE`
- `LOCK-FIN-P04-WC-001-01 = RELEASED`
- next workstream = `P04-D — Config / Environment Contract`
- P04-D = `NOT_STARTED`
