from pathlib import Path
import sys

REQUIRED = [
    "README.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    ".github/CODEOWNERS",
    ".github/pull_request_template.md",
    "docs/00-governance/PROJECT-CHARTER.md",
    "docs/00-governance/GOVERNANCE.md",
    "docs/00-governance/CHANGE-CONTROL.md",
    "docs/00-governance/OWNER-GATES.md",
    "docs/01-roadmap/MASTER-ROADMAP-v2.0.md",
    "docs/02-current-state/CURRENT-STATE.md",
    "docs/09-agents/AGENT-REGISTRY.md",
    "docs/13-tasks/TASK-CATALOG.md",
    "docs/14-evidence/EVIDENCE-STANDARD.md",
    "contracts/schemas/task-contract.schema.json",
]

missing = [p for p in REQUIRED if not Path(p).is_file()]
if missing:
    print("GOVERNANCE_VERIFY=FAIL")
    for p in missing:
        print(f"MISSING={p}")
    sys.exit(1)

roadmap = Path("docs/01-roadmap/MASTER-ROADMAP-v2.0.md").read_text(encoding="utf-8")
markers = [
    "ROADMAP_STATE = FROZEN",
    "DIRECT_ROADMAP_MUTATION = FORBIDDEN",
    "LIVE_TRADING = DISABLED",
    "AUTO_TRADING = DISABLED",
]
absent = [m for m in markers if m not in roadmap]
if absent:
    print("GOVERNANCE_VERIFY=FAIL")
    for m in absent:
        print(f"MISSING_MARKER={m}")
    sys.exit(1)

print("GOVERNANCE_VERIFY=PASS")
