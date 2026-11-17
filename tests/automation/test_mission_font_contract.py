"""Contract checks for user-supplied Iranian Sans loading, no font redistribution."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "apps" / "agent-mission-control"
SERVER = ROOT / "scripts" / "automation" / "mission_control_server.py"


class PersonalFontContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = (WEB / "font-control.js").read_text(encoding="utf-8")
        cls.html = (WEB / "index.html").read_text(encoding="utf-8")
        cls.css = (WEB / "styles.css").read_text(encoding="utf-8")
        cls.server = SERVER.read_text(encoding="utf-8")

    def test_control_is_reachable_and_loaded_from_same_origin(self):
        self.assertIn('<script src="font-control.js" defer></script>', self.html)
        self.assertIn('"/font-control.js": "font-control.js"', self.server)
        self.assertIn('id="font-upload-button"', self.html)
        self.assertIn('id="font-upload-input"', self.html)

    def test_font_is_private_and_persistent(self):
        for token in ("indexedDB.open", "objectStore(STORE).put", "FontFace(", "document.fonts.add", "file.arrayBuffer()"):
            self.assertIn(token, self.js)
        for forbidden in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "localStorage.setItem"):
            self.assertNotIn(forbidden, self.js)
        self.assertIn("MAX_BYTES=1024*1024", self.js)

    def test_font_is_applied_without_committing_binary(self):
        self.assertIn("--nq-personal-font", self.js)
        self.assertIn("var(--nq-personal-font,'NQ Iranian Sans')", self.css)
        self.assertFalse((WEB / "Iranian Sans.ttf").exists())
        self.assertFalse((WEB / "iranian-sans.ttf").exists())

    def test_no_sensitive_api_changes_for_font(self):
        self.assertNotIn('"/api/events":', self.server.split("ASSETS =",1)[1].split("}",1)[0])
        self.assertIn('"DEMO_ONLY"', self.server)


if __name__ == "__main__":
    unittest.main()
