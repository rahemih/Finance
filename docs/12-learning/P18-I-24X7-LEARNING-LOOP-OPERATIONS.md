# P18-I — 24/7 Learning Loop Operations

State: IN_PROGRESS  
Task: `FIN-P18-WI-001`

P18-I provides the deterministic operating contract for the permanent continuous Demo learning loop.

The enforced ordered stages are:

1. Observe / Analyze
2. Demo Trade
3. Outcome
4. Journal
5. Dataset
6. Experiment
7. Retrain / Validate
8. Challenger
9. Promotion Governance

Every completed stage carries content-addressed evidence and stages must form an exact prefix; skipping ahead fails closed. Checkpoints form a hash chain and support deterministic resume.

Operational guards include cadence, market-data staleness, consecutive-failure threshold and system-state safe hold/halt. Controlled Retraining may be automated inside P18-E. Promotion only routes to P18-H governance; automatic Live promotion is forbidden.

A completed loop is explicitly `CYCLE_COMPLETE_DEMO_ONLY`. P19 remains unstarted.
