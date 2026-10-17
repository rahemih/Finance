# P18-E — Controlled Retraining

State: CANONICAL_COMPLETE  
Task: `FIN-P18-WE-001`

Controlled Retraining consumes canonical dataset and experiment identities through an injected offline deterministic trainer. Every request binds dataset, experiment, base model, code, trainer identity/version, seed and canonical parameters. The returned artifact is validated against the request lineage and becomes a **candidate only**.

P18-E cannot select a Champion or promote a model. P18-F owns Champion/Challenger. Automatic live promotion is forbidden; Live/Auto Trading remain disabled.


## Canonical closure

PR #369 merged at `0acd470bd7c49c37174c62d53a5efb9bdc68a7b0`; Governance `39021866808` SUCCESS; artifact `sha256:28bee0e74f500e84f4c71ac744ffa7903eaabca3b4e59dfc190a313897a2f302`. P18-F READY_NOT_STARTED.
