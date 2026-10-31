"""P0-B preview safety/route source test, not visual browser acceptance."""
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
WEB=ROOT/"apps"/"web"
class MonitoringPreviewSource(unittest.TestCase):
 def test_screens_present_but_not_approved_in_canonical_manifest(self):
  master=json.loads((WEB/"contracts/web-p0-pages.json").read_text())
  self.assertEqual(master["ownerApprovedBaselineCount"],0)
  self.assertEqual(master["pageCount"],34)
  for p in master["pages"]:self.assertEqual(p["implementationStatus"],"NOT_IMPLEMENTED")
  previews=json.loads((WEB/"contracts/monitoring-preview-states.json").read_text())
  self.assertEqual({p["pageId"] for p in previews["pages"]},{"010","079","084"})
  self.assertEqual(sum(p["referenceCount"] for p in previews["pages"]),20)
 def test_response_pages_do_not_grant_authority(self):
  for name in ("dashboard/page.tsx","system/page.tsx","system/alerts/page.tsx"):
   s=(WEB/"src/app"/name).read_text()
   self.assertIn("robots",s)
   self.assertIn("index: false",s)
  s=(WEB/"src/components/monitoring/monitoring-preview.tsx").read_text()
  for forbidden in ("fetch(","localStorage","WebSocket(","<button","<form","sessionStorage","document.cookie"):
   self.assertNotIn(forbidden,s)
  for state in ("وضعیت سلامت سامانه نامعلوم است","تعداد هشدارهای واقعی نامعلوم است","هیچ معامله‌ای مجاز نیست"):
   self.assertIn(state,s)
if __name__=="__main__":unittest.main()
