# P20-H R01 — Execution-quality fill-band threshold repair

Task: `FIN-P20-WH-001-R01`  
State: CANONICAL_COMPLETE

P20-I G11 evidence exposed an impossible degraded-band condition in P20-H fill-ratio classification.

The prior expression made even a perfect 1,000,000 PPM fill ratio degraded under the canonical 950,000 PPM hard minimum and 80% degraded trigger.

The repaired degraded boundary is computed from the remaining headroom between the hard minimum and ideal fill:

`threshold = min_fill_ratio_ppm + (PPM - min_fill_ratio_ppm) * (100 - degraded_trigger_percent) / 100`

For the canonical policy this is 960,000 PPM:
- below 950,000 => REFERENCE_FAIL;
- 950,000..960,000 => DEGRADED_REFERENCE;
- above 960,000, subject to other metrics => eligible for WITHIN_REFERENCE_BUDGET.

No hard limit or G11 requirement is relaxed.


## Canonical closure evidence

- PR #428 = MERGED;
- repair head = `c1cc83298a1d02ecc71c44b219b37675c2c88862`;
- PR Governance = `40087774732` / SUCCESS;
- PR artifact = `12557384142` / `sha256:f1134de97e4a92551e780bb73fdc0baacbc687baa1b1290d51440c9c4315ac07`;
- merge SHA = `73c83b8a6bf0ab73d1a1dd79a4bd2eaa23a6bebe`;
- post-merge Governance = `40087893174` / SUCCESS;
- post-merge artifact = `12556869865` / `sha256:c24857d9c9b6fecfcdb3b7938ff6b2b979069c6af2d2c9840d3fec55b512a22d`;
- post-merge Branch Hygiene = `40087893199` / SUCCESS;
- lock = RELEASED;
- P20-I = UNBLOCKED / IN_PROGRESS;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED.

The repair changes only degraded-band classification geometry. It does not relax the hard minimum fill threshold, latency/slippage thresholds, G11 requirements or any Live/Auto boundary.
