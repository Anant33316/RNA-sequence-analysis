"""HTTP API tests (in-process ASGI; same middleware/routing as uvicorn)."""

import os
import tempfile
import unittest

from tests import _paths  # noqa: F401

_TMP = tempfile.TemporaryDirectory()
os.environ["RNA_TOC_DB"] = os.path.join(_TMP.name, "history-test.db")

from api.app import app  # noqa: E402
from tests.asgi_client import request, multipart  # noqa: E402


def get(url):
    return request(app, "GET", url)


def post(url, body):
    return request(app, "POST", url, json=body)


def example(key):
    return get(f"/api/examples/{key}").json()["automaton"]


class Basics(unittest.TestCase):
    def test_health(self):
        r = get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertIn("default-src 'self'", r.headers["content-security-policy"])
        self.assertEqual(r.headers["cache-control"], "no-store")

    def test_frontend_served(self):
        r = get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("<!doctype html>", r.text.lower())

    def test_unknown_and_wrong_method(self):
        self.assertEqual(get("/api/does-not-exist").status_code, 404)
        r = get("/api/automata/run")
        self.assertEqual(r.status_code, 405)
        self.assertEqual(r.json()["error"]["code"], "method_not_allowed")
        self.assertEqual(get("/api/examples/nope").status_code, 404)


class Malformed(unittest.TestCase):
    def test_invalid_json(self):
        r = request(app, "POST", "/api/automata/run", data=b"{not json", headers={"content-type": "application/json"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"]["code"], "invalid_json")

    def test_wrong_content_type(self):
        r = request(app, "POST", "/api/automata/run", data=b"{}", headers={"content-type": "text/plain"})
        self.assertEqual(r.status_code, 415)

    def test_schema_violation(self):
        r = post("/api/automata/run", {"automaton": {"type": "DFA"}})
        self.assertEqual(r.status_code, 422)
        err = r.json()["error"]
        self.assertEqual(err["code"], "validation_error")
        self.assertTrue(err["details"])
        r = post("/api/automata/run", {"automaton": dict(example("aug_dfa"), type="PDA")})
        self.assertEqual(r.status_code, 422)

    def test_semantic_error_has_field(self):
        spec = example("aug_dfa")
        spec["transitions"][0]["to"] = "nowhere"
        r = post("/api/automata/run", {"automaton": spec, "input": "AUG"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"]["field"], "automaton.transitions[0].to")

    def test_body_too_large(self):
        big = b'{"text": "' + b"A" * (4 * 1024 * 1024) + b'"}'
        r = request(app, "POST", "/api/rna/analyze", data=big, headers={"content-type": "application/json"})
        self.assertEqual(r.status_code, 413)

    def test_semantic_too_large(self):
        r = post("/api/advanced/fold", {"sequence": "A" * 300})
        self.assertEqual(r.status_code, 413)
        self.assertEqual(r.json()["error"]["code"], "too_large")


class Endpoints(unittest.TestCase):
    def test_examples_listing(self):
        ids = [e["id"] for e in get("/api/examples").json()["examples"]]
        self.assertIn("aug_dfa", ids)
        self.assertIn("eps_cycle", ids)

    def test_run_validate_convert_minimize(self):
        aug, enfa = example("aug_dfa"), example("altstart_enfa")
        self.assertTrue(post("/api/automata/run", {"automaton": aug, "input": "CAUG"}).json()["accepted"])
        self.assertEqual(post("/api/automata/validate", {"automaton": aug}).json()["facts"]["state_count"], 4)
        r = post("/api/automata/epsilon-eliminate", {"automaton": enfa})
        self.assertEqual(r.status_code, 200)
        dfa = post("/api/automata/subset", {"automaton": enfa}).json()["dfa"]
        self.assertTrue(post("/api/automata/equivalence", {"a": enfa, "b": dfa}).json()["equivalent"])
        self.assertEqual(post("/api/automata/minimize", {"automaton": example("redundant_dfa")}).json()["counts"]["minimized"], 2)
        r = post("/api/automata/minimize", {"automaton": enfa})
        self.assertEqual(r.status_code, 400)

    def test_equivalence_bounded_compare(self):
        aug = example("aug_dfa")
        r = post("/api/automata/equivalence", {"a": aug, "b": example("aug_buggy_dfa")}).json()
        self.assertEqual(r["counterexample_text"], "AAUG")
        r = post("/api/automata/bounded-test", {"a": aug, "b": example("aug_suffix_dfa"), "max_length": 4}).json()
        self.assertFalse(r["disagreement_found"])
        r = post("/api/automata/bounded-test", {"a": aug, "b": aug, "max_length": 13})
        self.assertEqual(r.status_code, 422)
        r = post("/api/automata/compare", {"a": aug, "b": example("aug_suffix_dfa"), "input": "AAUG"}).json()
        self.assertTrue(r["runs"]["agree"])

    def test_removed_endpoints_are_gone(self):
        # Closure Properties, Moore & Mealy and the Grammars/LBA/TM page were removed
        self.assertEqual(get("/api/machines/examples").status_code, 404)
        for path in ["/api/automata/closure", "/api/machines/run", "/api/machines/convert",
                     "/api/advanced/tm", "/api/advanced/lba", "/api/advanced/pumping"]:
            self.assertEqual(post(path, {}).status_code, 404, path)

    def test_rna_and_advanced(self):
        r = post("/api/rna/analyze", {"text": ">x\nCCCAUGGCUACGUAAGGG", "motifs": [{"pattern": "GG"}]}).json()
        self.assertTrue(r["valid"])
        self.assertEqual(len(r["orfs"]), 1)
        bad = post("/api/rna/analyze", {"text": "AUGQ"}).json()
        self.assertFalse(bad["valid"])
        self.assertEqual(post("/api/rna/analyze", {"text": "  "}).status_code, 400)
        self.assertEqual(post("/api/rna/orf-trace", {"sequence": "AUGUAA", "frame": 0}).json()["orfs"][0]["end"], 6)
        self.assertEqual(post("/api/rna/orf-trace", {"sequence": "AUGUAA", "frame": 3}).status_code, 422)
        self.assertEqual(post("/api/motif/compile", {"pattern": "A(U|G)"}).status_code, 200)
        self.assertEqual(post("/api/motif/compile", {"pattern": "A(U"}).status_code, 400)
        self.assertEqual(post("/api/advanced/fold", {"sequence": "GGGAAAUCC"}).json()["structure"], "(((...)))")
        self.assertEqual(post("/api/advanced/hairpins", {"sequence": "CCCGCGCAAA"}).json()["count"], 2)

    def test_motif_library(self):
        r = get("/api/rna/motifs").json()
        self.assertEqual(r["limits"]["max_sequence"], 100000)


class Upload(unittest.TestCase):
    def up(self, name, content):
        body, ctype = multipart({"file": (name, content, "text/plain")})
        return request(app, "POST", "/api/rna/upload", data=body, headers={"content-type": ctype})

    def test_fasta_upload(self):
        r = self.up("demo.fasta", b">a one\nAUGG\nUAA\n>b\nGGNN\n")
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertEqual(j["record_count"], 2)
        self.assertEqual(j["records"][1]["invalid_count"], 2)

    def test_rejections(self):
        self.assertEqual(self.up("x.exe", b"AUG").json()["error"]["code"], "unsupported_file")
        self.assertEqual(self.up("x.fasta", b"AU\x00G").json()["error"]["code"], "unsupported_file")
        self.assertEqual(self.up("x.txt", b"\xff\xfeA").json()["error"]["code"], "unsupported_file")
        self.assertEqual(self.up("x.txt", b"A" * (2 * 1024 * 1024 + 10)).status_code, 413)
        self.assertEqual(self.up("x.fasta", b">a\n>b\nAUG").status_code, 400)
        r = request(app, "POST", "/api/rna/upload", json={"text": "AUG"})
        self.assertEqual(r.status_code, 415)


class History(unittest.TestCase):
    def test_crud(self):
        request(app, "DELETE", "/api/history")
        r = post("/api/rna/analyze", {"text": "AUGGCUUAA", "save": True}).json()
        hid = r["history_id"]
        self.assertIsInstance(hid, int)
        post("/api/automata/equivalence", {"a": example("aug_dfa"), "b": example("aug_buggy_dfa"), "save": True})
        entries = get("/api/history").json()["entries"]
        self.assertEqual([e["kind"] for e in entries], ["equivalence", "rna"])
        self.assertEqual(get(f"/api/history/{hid}").json()["payload"]["text"], "AUGGCUUAA")
        self.assertEqual(len(get("/api/history?kind=rna").json()["entries"]), 1)
        self.assertEqual(request(app, "DELETE", f"/api/history/{hid}").status_code, 204)
        self.assertEqual(get(f"/api/history/{hid}").status_code, 404)
        self.assertEqual(request(app, "DELETE", "/api/history").json()["deleted"], 1)
        self.assertEqual(get("/api/history?limit=abc").status_code, 400)


if __name__ == "__main__":
    unittest.main()
