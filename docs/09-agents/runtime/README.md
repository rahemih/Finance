# NEXUS QUANT — Agent Runtime Preflight

State: PRE_RUNTIME_ENGINEERING  
Task: `FIN-P01-WG-003`  
Runtime authority: `P02-F`  
Production framework: DEFERRED  
Runtime installation: NOT PERFORMED

## Purpose

Freeze the last engineering decisions that can be made before runtime implementation. This package is intentionally framework-neutral and does not activate any main-roadmap phase.

## Package

- `A0-A10-RUNTIME-ADAPTER-SPEC.md`
- `SPECIALIST-LIFECYCLE-SPEC.md`
- `STATE-CHECKPOINT-RESUME-SPEC.md`
- `VETO-AND-MESSAGE-GATES.md`
- `RUNTIME-SECURITY-SPEC.md`
- `OBSERVABILITY-EVALUATION-HARNESS.md`
- `P02-F-IMPLEMENTATION-SEQUENCE.md`
- `runtime-preflight.json`

## Non-negotiable boundaries

A0–A10 authority remains canonical. A5 risk and A8 security vetoes cannot be bypassed. Specialists are temporary and bounded. External content is data, not instruction. Memory is not evidence. Runtime implementation, framework selection and dependency installation remain deferred until the P02-F entry gate is actually satisfied.
