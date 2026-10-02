# Contributing

Finance / NEXUS QUANT is a governance-first private-team project.

## Workflow

1. Read `docs/02-current-state/CURRENT-STATE.md`.
2. Confirm the task exists in `docs/13-tasks/TASK-CATALOG.md`.
3. Confirm a valid Task Contract exists.
4. Run Fresh Live Guard and check locks/dependencies.
5. Work on a task-scoped branch.
6. Add tests/evidence appropriate to the risk.
7. Open a Pull Request using the template.
8. Do not consider work complete until merge and post-merge closure.

## Branch naming

Canonical branch: `main`.

Human-created task branches must use:

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

Approved automation prefixes such as `dependabot/` are exempt.

Merged branches are deleted automatically. Unmerged stale branches are reported but never auto-deleted only because of age.

See `docs/00-governance/BRANCH-POLICY.md`.

## Commits

Use concise Conventional Commit-style messages where practical.

## Prohibited

- Direct production secrets
- Unreviewed live-trading changes
- Bypassing the Risk Engine / Pre-Trade Firewall
- Editing the frozen Master Roadmap directly
- Force-pushing canonical branches
