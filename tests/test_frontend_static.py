"""Static checks for the no-build frontend (web/).

* every relative ES-module import points to an existing file
* every route in app.js has a view module exporting render()
* every module parses (uses Node.js if it is installed; skipped otherwise)
* no innerHTML assignments (all DOM is built with textContent)
"""

import re
import shutil
import subprocess
import unittest
from pathlib import Path

from tests._paths import ROOT

WEB = Path(ROOT) / "web"
JS = sorted((WEB / "js").rglob("*.js"))


class FrontendStatic(unittest.TestCase):
    def test_imports_resolve(self):
        pattern = re.compile(r'''(?:import\s[^'"]*?from\s*|import\()\s*["'](\.{1,2}/[^"']+)["']''')
        for f in JS:
            for rel in pattern.findall(f.read_text(encoding="utf-8")):
                self.assertTrue((f.parent / rel).resolve().exists(), f"{f.name}: import {rel} not found")

    def test_routes_have_views(self):
        app = (WEB / "js" / "app.js").read_text(encoding="utf-8")
        views = re.findall(r'import\("\./views/([\w-]+)\.js"\)', app)
        self.assertGreaterEqual(len(views), 8)
        for v in views:
            src = (WEB / "js" / "views" / f"{v}.js").read_text(encoding="utf-8")
            self.assertIn("export async function render", src, v)

    def test_removed_pages_absent(self):
        # Closure Properties, Moore & Mealy and Grammars/LBA/TM were removed: no route, view or sidebar link
        app = (WEB / "js" / "app.js").read_text(encoding="utf-8")
        html = (WEB / "index.html").read_text(encoding="utf-8")
        for name in ["closure", "machines", "advanced"]:
            self.assertNotIn(f"views/{name}.js", app)
            self.assertFalse((WEB / "js" / "views" / f"{name}.js").exists(), name)
            self.assertNotIn(f'href="#/{name}"', html)

    def test_index_assets_exist(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        for ref in re.findall(r'(?:src|href)="([^"#:]+)"', html):
            self.assertTrue((WEB / ref).exists(), ref)

    def test_no_inner_html(self):
        for f in JS:
            self.assertIsNone(re.search(r"\.(innerHTML|outerHTML)\s*[+]?=|insertAdjacentHTML", f.read_text(encoding="utf-8")),
                              f.name)

    @unittest.skipUnless(shutil.which("node"), "Node.js not installed")
    def test_modules_parse(self):
        for f in JS:
            out = subprocess.run(["node", "--experimental-default-type=module", "--check", str(f)],
                                 capture_output=True, text=True)
            if "bad option" in out.stderr:
                self.skipTest("this Node version cannot syntax-check ES modules")
            self.assertEqual(out.returncode, 0, f"{f.name}: {out.stderr}")


if __name__ == "__main__":
    unittest.main()
