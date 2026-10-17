# P18-E — Controlled Retraining

State: IN_PROGRESS  
Task: `FIN-P18-WE-001`

Controlled Retraining consumes canonical dataset and experiment identities through an injected offline deterministic trainer. Every request binds dataset, experiment, base model, code, trainer identity/version, seed and canonical parameters. The returned artifact is validated against the request lineage and becomes a **candidate only**.

P18-E cannot select a Champion or promote a model. P18-F owns Champion/Challenger. Automatic live promotion is forbidden; Live/Auto Trading remain disabled.
