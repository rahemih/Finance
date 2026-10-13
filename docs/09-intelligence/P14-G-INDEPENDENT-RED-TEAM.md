# P14-G — Independent Red-Team Challenge

State: IMPLEMENTATION_ACTIVE  
Task: `FIN-P14-WG-001`  
Linear: BLOCKED_FREE_ISSUE_LIMIT

## Objective

Challenge canonical P14 analytical outputs independently before the final signal contract is formed.

## Inputs

- P14-B `WeightedFusionResult`
- P14-D `ProbabilityUncertaintyQualification`
- P14-E `TPStopOutcomeProbability`
- P14-F `PersianSignalExplanation`

The challenge verifies exact lineage across these objects and never rewrites upstream numeric values.

## Dispositions

- `CLEAR`: no governed challenge finding.
- `CAUTION`: analytical output is coherent but contains a governed weakness such as opposing evidence, expired evidence exclusion, limited sample support, or TP-first probability not exceeding Stop-first probability.
- `REJECT`: blocked/insufficient upstream state or insufficient calibration/outcome support.

The final LONG/SHORT/WAIT/NO_TRADE action remains owned by P14-H.

## Linear synchronization

The workspace free issue limit prevented creation of the expected P14-G Linear issue. GitHub remains canonical; Linear reconciliation is required when workspace capacity becomes available.

## Boundaries

P14-G does not mutate probability or uncertainty and does not create the final signal action.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.
