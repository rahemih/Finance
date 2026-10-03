# Specialist Agent Catalog

Specialists are temporary bounded workers. They never replace A0–A10.

| Specialist | Parent | Purpose |
|---|---|---|
| crypto | A3 | Crypto market structure and evidence synthesis |
| forex | A3 | FX market structure and evidence synthesis |
| technical | A3 | Technical evidence family |
| trend | A3 | Trend/regime evidence |
| momentum | A3 | Momentum evidence |
| order_flow | A3 | Order-flow evidence |
| liquidity | A3 | Liquidity/spread/depth evidence |
| macro | A3 | Macro and rates evidence |
| fundamental | A3 | Fundamental evidence |
| news | A3 | News/event evidence |
| sentiment | A3 | Sentiment evidence |
| on_chain | A3 | On-chain evidence |
| historical_analog | A3 | Historical analog evidence |
| quant_research | A4 | Quantitative research |
| backtest_validation | A4 | Backtest integrity and leakage review |
| model_validation | A4 | Model validation |
| calibration | A4 | Probability/calibration review |
| risk_red_team | A5 | Independent risk challenge |
| execution_review | A6 | Execution-system review |
| security_red_team | A8 | Security/adversarial review |
| data_quality | A2 | Data quality/freshness/lineage review |
| ux | A1 | Human-facing UX architecture review |
| performance | A9 | Performance/latency review |
| documentation | A10 | Documentation/evidence completeness |
| cost_finops | A9 | Cost/usage efficiency review |

Every spawn requires an active Task Contract, bounded inputs/tools/budget, traceable parent identity and an explicit termination condition.
