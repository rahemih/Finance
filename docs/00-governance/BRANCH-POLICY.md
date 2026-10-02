# Branch Policy

## Goals

Keep the repository easy to audit and prevent abandoned branches from accumulating without risking deletion of unfinished work.

## Canonical branch

`main` is the only long-lived canonical branch.

## Allowed task branch pattern

Normal human-created work branches must use:

`<type>/<TASK-ID>-<slug>`

Allowed types:

- `feat`
- `fix`
- `docs`
- `chore`
- `research`
- `security`
- `perf`
- `test`
- `refactor`
- `bootstrap`

Example:

`chore/FIN-P00-WB-001-branch-hygiene`

Repair tasks use the repair Task ID:

`fix/FIN-P08-WC-003-R01-correct-signal-window`

Approved automation prefixes such as `dependabot/` are exempt.

## Lifecycle

1. Create a branch from current canonical `main`.
2. Keep one governed task per branch unless the Task Contract explicitly allows otherwise.
3. Open a pull request before the branch becomes long-lived.
4. After a PR is merged, the branch is deleted automatically.
5. Unmerged branches are never deleted automatically only because they are old.
6. A daily audit reports branches with no open PR whose tip commit is older than 30 days.
7. A branch-count warning is raised when non-canonical branches exceed 12.

## Safety

Automatic deletion is allowed only for the head branch of a same-repository pull request that GitHub reports as merged.

The automation must never delete:

- `main`
- a branch from a fork
- an unmerged PR branch
- an unmerged branch merely because it is stale

## Repository settings

GitHub's repository-level option **Automatically delete head branches** should also be enabled as defense in depth when Owner/admin settings are completed.

Branch protection / Ruleset for `main` remains a repository-admin setting and is tracked separately.
