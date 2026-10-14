# P15-D — Portfolio / Correlation Exposure

State: CANONICAL_COMPLETE  
Task: `FIN-P15-WD-001`

P15-D evaluates portfolio-level concentration after P15-C.

It uses explicit governed limits for:
- gross exposure in bps of NAV;
- absolute net exposure in bps of NAV;
- absolute correlation threshold in milli-correlation;
- maximum gross exposure of a connected correlated cluster.

All distinct asset pairs require explicit correlation input. Unknown correlation fails closed.

`PORTFOLIO_ELIGIBLE` is not leverage approval and is not execution approval.

P15-E..P15-I = NOT_STARTED.  
P16 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.


## Canonical closure evidence

- PR #309 = MERGED;
- implementation head = `1e102bcd8d69cafa6d7c3a4241f59b981d720feb`;
- Governance = `38527337401` / SUCCESS;
- artifact = `sha256:a942f9df87da82feb12cc9152d698b8398b6e734114605b36773e368ff273209`;
- implementation merge = `f0c763a7da1d1d2989de7da125e5fd04729a9c38`;
- `FIN-P15-WD-001` = CANONICAL_COMPLETE;
- lock = RELEASED;
- P15-E = READY_NOT_STARTED;
- P15-F..P15-I = NOT_STARTED;
- P16 = NOT_STARTED.
