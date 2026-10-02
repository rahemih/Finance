# Agent Registry

Core agents are governance roles, not unrestricted autonomous identities.

| Agent | Role | Key authority | Explicitly forbidden |
|---|---|---|---|
| A0 | Governance / Orchestrator | Guard, routing, locks, phase coordination | Bypass gates |
| A1 | Architecture | Interfaces and architecture contracts | Live orders |
| A2 | Data | Feeds, storage, data quality | Trade execution |
| A3 | Market Intelligence | Technical/macro/order-flow/memory analysis | Live execution |
| A4 | Quant | Backtest/models/strategies/validation | Self-promote to Live |
| A5 | Risk | Risk decisions and veto | Modify own ceilings; send broker orders |
| A6 | Execution | OMS, adapters, reconciliation | Override Risk/Firewall |
| A7 | Learning | Demo/training/drift | Auto-promote to Live |
| A8 | Security | Security, access, secrets governance | Trade decisions |
| A9 | Operations | Infrastructure, backup, observability | Risk-policy changes |
| A10 | Evidence & Audit | Evidence, docs, closure validation | Implement-and-self-approve critical change |

Specialist agents are spawned on demand for Crypto, Forex, Trend, Momentum, Order Flow, Macro, News, Backtest, Red Team, Security, UX, Performance, Documentation and Cost.

Every agent contract must define Role, Authority, Inputs, Outputs, Read, Write, Forbidden, Tools, Plugins, Skills, Trigger, Escalation, Failure Behavior and Audit requirements.
