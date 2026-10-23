"""Optional end-to-end browser smoke test.

Starts the real server (uvicorn) on a free port, opens every page in
headless Chromium via Playwright, performs one key interaction per page and
fails on any JavaScript error. Skipped automatically when Playwright or a
Chromium build is not installed (pip install playwright && playwright install chromium).
"""

import os
import socket
import tempfile
import threading
import time
import unittest

from tests import _paths  # noqa: F401

try:
    from playwright.sync_api import sync_playwright
    HAVE_PW = True
except ImportError:  # pragma: no cover
    HAVE_PW = False


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PAGES = [
    ("#/", "text=Read RNA the way an automaton does", None),
    ("#/rna", "text=RNA analyzer", "text=Analyze sequence"),
    ("#/playground?example=altstart_enfa", "text=Active set", ".player >> text=Step"),
    ("#/convert", "text=Construction steps", None),
    ("#/minimize", "text=Pair table", None),
    ("#/verify", "text=Verification lab", "text=Prove or refute equivalence"),
    ("#/history", "text=History", None),
    ("#/learn", "text=Proof versus evidence", None),
]


@unittest.skipUnless(HAVE_PW, "playwright not installed")
class BrowserSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import uvicorn
        cls.tmp = tempfile.TemporaryDirectory()
        cls.old_db = os.environ.get("RNA_TOC_DB")
        os.environ["RNA_TOC_DB"] = os.path.join(cls.tmp.name, "e2e.db")
        from api.app import app
        cls.port = _free_port()
        cls.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=cls.port, log_level="warning"))
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        for _ in range(100):
            if cls.server.started:
                break
            time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(timeout=5)
        if cls.old_db is None:
            os.environ.pop("RNA_TOC_DB", None)
        else:
            os.environ["RNA_TOC_DB"] = cls.old_db
        cls.tmp.cleanup()

    def test_every_page(self):
        try:
            pw = sync_playwright().start()
            browser = pw.chromium.launch()
        except Exception as exc:  # no browser binary installed
            self.skipTest(f"Chromium not available: {exc}")
        errors = []
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            for url, expect, click in PAGES:
                page.goto(f"http://127.0.0.1:{self.port}/{url}")
                if click:
                    page.locator(click).first.click(timeout=10000)
                page.locator(expect).first.wait_for(timeout=10000)
            self.assertEqual(errors, [])
        finally:
            browser.close()
            pw.stop()


if __name__ == "__main__":
    unittest.main()
