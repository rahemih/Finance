# AR-0 — Tool Build-vs-Buy ADR Plan

State: `TO_BE_DECIDED_BY_ADR`  
Task: `FIN-P08-WJ-003`

## Purpose

AR-0 does **not** choose one universal research or backtesting framework. Tool choice is deferred to a governed ADR/technology spike before AR-1 implementation.

The future ADR must decide which capabilities should be repository-native and which may use an external open-source component while preserving NEXUS QUANT governance.

## Capability layers to evaluate

The ADR must evaluate at least three potentially different layers:

1. research / feature experimentation;
2. statistical robustness and validation utilities;
3. future event-driven simulation/backtesting interoperability.

One library does not have to own all three layers.

## Required evaluation dimensions

Each candidate is evaluated without a hard-coded composite score against:

- license compatibility and zero/low recurring-cost preference;
- deterministic/reproducible operation;
- point-in-time and vintage-aware data support;
- immutable dataset/version references;
- Python/runtime compatibility with the repository baseline;
- ability to run without notebook-hidden state;
- machine-readable inputs/outputs and artifact export;
- testability and CI suitability;
- support for cross-asset/time-series research;
- statistical/robustness extensibility;
- event-driven simulation interoperability where relevant;
- maintenance activity and security posture;
- dependency/supply-chain cost;
- vendor lock-in risk;
- performance characteristics measured on governed representative workloads;
- migration/rollback feasibility.

## Decision process

The AR-1 technology spike must:

1. define representative governed workloads;
2. shortlist open-source or repository-native candidates;
3. reproduce the same workloads on each serious candidate;
4. record evidence, limitations, dependency/license/security impacts;
5. issue an ADR selecting one or more layers or a repository-native build;
6. record rejected alternatives and rollback path.

Any numerical benchmark acceptance threshold without measured basis remains `TO_BE_CALIBRATED`.

## Hard boundaries

The ADR cannot:

- change Master Roadmap gate authority;
- authorize Demo/Shadow/Live/Auto trading;
- convert research evidence into production validation;
- create BUY/SELL or Risk approval authority;
- require production secrets/credentials for the research harness baseline.
