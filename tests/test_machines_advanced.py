"""The advanced models kept in the RNA analyzer: CFG folding and the TM hairpin scan."""

import unittest

from tests import _paths  # noqa: F401

from engine.errors import EngineError
from engine.advanced import fold_spec, hairpin_scan_spec


class Advanced(unittest.TestCase):
    def test_fold(self):
        r = fold_spec("GGGAAAUCC")
        self.assertEqual(r["structure"], "(((...)))")
        self.assertEqual(r["derivation"][0]["form"], "S")
        self.assertEqual(r["derivation"][-1]["form"].replace(" ", ""), "GGGAAAUCC")
        self.assertEqual(r["pair_types"][2]["type"], "wobble")
        self.assertFalse(r["pseudoknot"])
        self.assertEqual(r["dp_table"][0][-1], 3)

    def test_fold_limits(self):
        with self.assertRaises(EngineError):
            fold_spec("A" * 201)
        with self.assertRaises(EngineError):
            fold_spec("AUGX")
        with self.assertRaises(EngineError):
            fold_spec("")
        self.assertIsNone(fold_spec("A" * 100)["dp_table"])

    def test_hairpin_scan(self):
        r = hairpin_scan_spec("CCCGCGCAAA", 4, 6)
        self.assertEqual([(h["start"], h["end"]) for h in r["hits"]], [(2, 6), (3, 7)])
        with self.assertRaises(EngineError):
            hairpin_scan_spec("AUGC", 6, 4)


if __name__ == "__main__":
    unittest.main()
