# config

Schema-governed **non-secret** configuration area.

Canonical P04-D files:
- `environment-config.schema.json` — machine-readable environment contract;
- `config-policy.json` — precedence, override, isolation and safety policy;
- `base.json` — non-secret defaults;
- `environments/*.json` — logical environment overlays;
- `runtime-overrides.example.json` — approved low-risk override shape only.

Rules:
- raw API keys, tokens, passwords, signing/private keys and broker/exchange credentials are forbidden;
- secret handles use `secret://<environment>/<domain>/<name>@<version-or-alias>`;
- runtime override cannot change safety, execution or credential authority;
- all environments are `CONTRACT_ONLY` in P04-D;
- CANARY/LIVE remain disabled and unprovisioned;
- country/location is not an authorization input.

Validation is enforced by the required `governance` CI context.
