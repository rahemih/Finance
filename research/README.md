# research

Exploration, notebooks, prototypes, benchmarks and temporary experiments.

Production code MUST NOT import from this directory. Promotion requires a governed task that moves validated logic into a production zone with tests and provenance.

## Governance

`research/governance/` contains versioned Alpha Research Fast Track governance, schemas and policy artifacts. These artifacts govern research execution but remain inside the research zone: production code MUST NOT import them as runtime dependencies.

AR-0 freezes the generic protocol. AR-1+ implementation or candidate experiments require their own governed Task Contracts and cannot infer production validation, BUY/SELL, Risk or execution authority from the presence of these files.
