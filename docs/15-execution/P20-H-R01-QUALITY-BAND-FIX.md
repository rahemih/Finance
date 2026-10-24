# P20-H R01 — Execution-quality fill-band threshold repair

Task: `FIN-P20-WH-001-R01`  
State: IN_PROGRESS

P20-I G11 evidence exposed an impossible degraded-band condition in P20-H fill-ratio classification.

The prior expression made even a perfect 1,000,000 PPM fill ratio degraded under the canonical 950,000 PPM hard minimum and 80% degraded trigger.

The repaired degraded boundary is computed from the remaining headroom between the hard minimum and ideal fill:

`threshold = min_fill_ratio_ppm + (PPM - min_fill_ratio_ppm) * (100 - degraded_trigger_percent) / 100`

For the canonical policy this is 960,000 PPM:
- below 950,000 => REFERENCE_FAIL;
- 950,000..960,000 => DEGRADED_REFERENCE;
- above 960,000, subject to other metrics => eligible for WITHIN_REFERENCE_BUDGET.

No hard limit or G11 requirement is relaxed.
