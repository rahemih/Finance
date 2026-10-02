import os
import re
import sys

branch = os.environ.get("PR_HEAD_REF", "").strip()

if not branch:
    print("BRANCH_NAME_CHECK=SKIP")
    sys.exit(0)

allowed = [
    re.compile(
        r"^(feat|fix|docs|chore|research|security|perf|test|refactor|bootstrap)/"
        r"FIN-P\d{2}-W[A-Z]-\d{3}(?:-R\d{2})?-[a-z0-9][a-z0-9-]{0,79}$"
    ),
    re.compile(r"^dependabot/.+$"),
]

if any(pattern.fullmatch(branch) for pattern in allowed):
    print(f"BRANCH_NAME_CHECK=PASS branch={branch}")
    sys.exit(0)

print("BRANCH_NAME_CHECK=FAIL")
print(f"INVALID_BRANCH={branch}")
print("Expected: <type>/FIN-PXX-WY-NNN-<slug> (or approved automation prefix)")
sys.exit(1)
