# Branch Hygiene Historical Archive — FIN-P18-WI-001-R02

State: CANONICAL_COMPLETE after governed merge

## Problem

Branch Hygiene issue #233 reported more than the configured warning threshold of non-canonical branches. The remaining branches all carried unique commits relative to `main`, so force-deleting them would violate the repository's fail-safe hygiene policy.

## Resolution

Historical unique branches are governed by `config/governance/branch-hygiene-archive.json`.

An archive entry is valid only when both:
- the branch name matches exactly; and
- the current branch head SHA matches exactly.

A moved or reused branch immediately leaves archive scope and returns to the active Branch Hygiene audit.

Archived branches are excluded only from active/stale warning counts. They are not granted execution authority and they are not protected from normal safe cleanup when GitHub proves a branch is fully merged or has `ahead_by=0`.

## Audit semantics

Branch Hygiene now reports:
- total non-canonical branch count;
- exact-SHA archived historical count;
- active/unclassified non-canonical count;
- archive SHA drift;
- stale active branches.

Only active/unclassified branches count toward the warning threshold.

The audit now also runs after every push to `main`, so a clean inventory closes the automated #233 report immediately instead of waiting for the daily schedule.

## Safety

No unique historical branch is force-deleted by this repair.
No branch contents are rewritten.
P19 remains NOT_STARTED.
LIVE_TRADING and AUTO_TRADING remain DISABLED.
