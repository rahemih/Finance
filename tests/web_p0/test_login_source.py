"""PAGE-001 preliminary SOURCE contract tests: not browser/security E2E acceptance."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = (ROOT / "apps/web/src/components/auth/login-preview.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "apps/web/src/app/auth/login/login-preview.css").read_text(encoding="utf-8")
PAGE = (ROOT / "apps/web/src/app/auth/login/page.tsx").read_text(encoding="utf-8")
STATES = (ROOT / "apps/web/src/lib/auth/login-state.ts").read_text(encoding="utf-8")
REGISTRY = json.loads((ROOT / "apps/web/contracts/login-visual-scenarios.json").read_text(encoding="utf-8"))

class LoginSourceContracts(unittest.TestCase):
    def test_ten_native_doc_image_refs_not_assumed_approved(self):
        self.assertEqual(len(REGISTRY["scenarios"]), 10)
        self.assertEqual([s["screenshotId"] for s in REGISTRY["scenarios"]],
                         [f"001-{n:02d}" for n in range(1, 11)])
        self.assertEqual({s["viewportWidthPx"] for s in REGISTRY["scenarios"]}, {360, 768, 1440})
        self.assertEqual(len({s["sourceInlineObjectId"] for s in REGISTRY["scenarios"]}), 10)
        self.assertFalse(REGISTRY["ownerBaselineApproved"])
        self.assertTrue(all(s["baselineSHA256"] is None and
                            s["ownerReviewStatus"] == "REVIEW_REQUIRED" and
                            s["visualTest"] == "NOT_RUN" for s in REGISTRY["scenarios"]))

    def test_no_credentials_or_auth_connection(self):
        self.assertIn("<fieldset", COMPONENT)
        self.assertIn("disabled>", COMPONENT)
        self.assertIn("event.preventDefault()", COMPONENT)
        for forbidden in ("fetch(", "localStorage", "sessionStorage", "document.cookie",
                          "XMLHttpRequest", "WebSocket(", "navigator.credentials"):
            self.assertNotIn(forbidden, COMPONENT + STATES)
        self.assertIn("AUTH_RUNTIME_ENABLED = false", STATES)
        self.assertIn("SESSION_AUTHORITY = false", STATES)
        self.assertIn("return false;", STATES)
        self.assertIn('visualState="DEFAULT"', PAGE)

    def test_accessibility_and_critical_viewports(self):
        for marker in ('<main', '<h1', '<form', 'role="status"', 'role="alert"',
                       'aria-describedby=', 'lang', 'dir="rtl"'):
            if marker == 'lang':
                continue  # provided by upstream App Router layout PR #497
            self.assertIn(marker, COMPONENT)
        for width in ("360px", "768px", "1024px"):
            self.assertIn(width, CSS)
        self.assertIn("min-height: 44px", CSS)
        self.assertIn("prefers-reduced-motion", CSS)
        self.assertIn("var(--nq-background", CSS)

if __name__ == "__main__":
    unittest.main()
