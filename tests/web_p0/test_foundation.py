"""Source-only, deterministic WEB-P0 preliminary contract tests; not a Next build."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "apps" / "web"
CONFIG = json.loads((ROOT / "config/ux/design-system.json").read_text(encoding="utf-8"))
IA = json.loads((ROOT / "config/ux/information-architecture.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((WEB / "contracts/web-p0-pages.json").read_text(encoding="utf-8"))
CSS = (WEB / "src/styles/tokens.css").read_text(encoding="utf-8")
SOURCE = (WEB / "src/lib/web-p0-contract.ts").read_text(encoding="utf-8")
LAYOUT = (WEB / "src/app/layout.tsx").read_text(encoding="utf-8")
BIDI = (WEB / "src/components/financial-island.tsx").read_text(encoding="utf-8")

class FoundationContractTests(unittest.TestCase):
    def test_page_registry_matches_p0_workstream_counts(self):
        rows = MANIFEST["pages"]
        self.assertEqual(len(rows), 34)
        self.assertEqual(MANIFEST["pageCount"], 34)
        self.assertEqual(MANIFEST["reportedScreenshotInventoryCount"], 212)
        self.assertEqual(len({p["pageId"] for p in rows}), 34)
        self.assertEqual(len({p["proposedRoute"] for p in rows}), 34)
        self.assertEqual(
            {w: sum(p["workstream"] == w for p in rows) for w in ("P0-A","P0-B","P0-C","P0-D","P0-E","P0-F")},
            {"P0-A":8,"P0-B":3,"P0-C":10,"P0-D":4,"P0-E":8,"P0-F":1}
        )
        self.assertTrue(all(p["routeApproval"] == "PROPOSED" and p["visualBaselineStatus"] == "REVIEW_REQUIRED" and p["implementationStatus"] == "NOT_IMPLEMENTED" for p in rows))
        self.assertEqual(MANIFEST["ownerApprovedBaselineCount"], 0)

    def test_p23_canonical_root_surfaces_are_preserved(self):
        canon = {p["route"] for p in IA["surfaces"]}
        self.assertEqual(len(canon), 11)
        # WEB-P1/P2 root surfaces are not fabricated as implemented pages.
        proposed = {p["proposedRoute"] for p in MANIFEST["pages"]}
        self.assertTrue({"/dashboard","/markets","/opportunities","/trades","/portfolio","/demo","/system","/settings/security"}.issubset(proposed))
        self.assertEqual(canon, {"/dashboard", "/markets", "/opportunities", "/trades", "/portfolio", "/demo", "/research", "/reports", "/system", "/settings", "/glossary"})
        self.assertNotIn("/research", proposed)
        self.assertNotIn("/reports", proposed)

    def test_canonical_theme_tokens(self):
        dark, light = CONFIG["themes"]["dark"], CONFIG["themes"]["light"]
        for theme, values in (("dark",dark),("light",light)):
            for name,token in (("background","background"),("surface","surface"),("text","text"),("muted_text","muted-text"),("border","border"),("focus","focus")):
                self.assertIn(f"--nq-{token}: {values[name]};", CSS)
        self.assertIn("--nq-space-1: 4px;", CSS)
        self.assertIn("--nq-space-8: 64px;", CSS)

    def test_safety_disabled_by_default_and_no_provider_connection(self):
        for key in ("LIVE_TRADING","AUTO_TRADING","BROWSER_BROKER_CONNECTION","BROWSER_ORDER_SUBMISSION","BROWSER_RISK_OVERRIDE","BASELINES_APPROVED"):
            self.assertRegex(SOURCE, rf"\b{key}: false\b")
        self.assertIn("return false;", SOURCE)
        self.assertNotRegex(SOURCE, r"fetch\s*\(|axios\b|WebSocket\s*\(|localStorage\b")

    def test_rtl_ltr_semantics(self):
        self.assertIn('lang="fa" dir="rtl"', LAYOUT)
        self.assertIn('dir="ltr"', BIDI)
        self.assertIn("unicode-bidi: isolate", CSS)
        self.assertIn('fontFamily: \'"Noto Sans Arabic", sans-serif\'', LAYOUT)

if __name__ == "__main__":
    unittest.main()
