"""RNA analysis: parsing, validation, composition, codons, ORFs, motifs."""

import random
import unittest

from tests import _paths  # noqa: F401

from engine.errors import EngineError
from engine.rna import (analyze_sequence, parse_sequence_text, normalize_sequence, orf_trace, compile_motif_spec,
                        GENETIC_CODE, MAX_SEQUENCE_LENGTH)


class Parsing(unittest.TestCase):
    def test_empty(self):
        for text in ["", "   ", "\n\n"]:
            with self.assertRaises(EngineError) as cm:
                analyze_sequence(text)
            self.assertEqual(cm.exception.code, "empty")

    def test_raw_multiline(self):
        r = analyze_sequence("AUG GCU\nUAA\n")
        self.assertTrue(r["valid"])
        self.assertEqual(r["sequence"], "AUGGCUUAA")
        self.assertEqual(r["format"], "raw")

    def test_fasta_records(self):
        text = ">seq1 first\nAUGG\nCUUAA\n; comment\n>seq2\nGGGG\n"
        r = analyze_sequence(text, record_index=1)
        self.assertEqual(r["record_id"], "seq2")
        self.assertEqual(r["sequence"], "GGGG")
        self.assertEqual([x["id"] for x in r["records"]], ["seq1", "seq2"])
        with self.assertRaises(EngineError):
            analyze_sequence(text, record_index=5)

    def test_malformed_fasta(self):
        with self.assertRaises(EngineError):
            parse_sequence_text(">a\n>b\nAUG")           # record without sequence
        with self.assertRaises(EngineError):
            parse_sequence_text("AUG\n>late header\nAUG")

    def test_invalid_characters_explained_with_positions(self):
        r = analyze_sequence("AUGNXT-5", convert_t=False)
        self.assertFalse(r["valid"])
        by = {i["char"]: i for i in r["validation"]["invalid"]}
        self.assertEqual(by["N"]["positions"], [3])
        self.assertIn("IUPAC", by["N"]["reason"])
        self.assertIn("not a nucleotide", by["X"]["reason"])
        self.assertIn("DNA", by["T"]["reason"])
        self.assertIn("gap", by["-"]["reason"])
        self.assertIn("digit", by["5"]["reason"])
        self.assertEqual(r["validation"]["invalid_count"], 5)
        self.assertIn("position 3", r["error"])

    def test_t_conversion_and_lowercase(self):
        n = normalize_sequence("atgc", True)
        self.assertEqual(n["sequence"], "AUGC")
        self.assertTrue(any("T (thymine" in w for w in n["warnings"]))
        self.assertTrue(any("lowercase" in w for w in n["warnings"]))

    def test_size_limits(self):
        rng = random.Random(0)
        big = "".join(rng.choice("ACGU") for _ in range(MAX_SEQUENCE_LENGTH))
        r = analyze_sequence(big)                       # largest permitted input works
        self.assertEqual(r["length"], MAX_SEQUENCE_LENGTH)
        with self.assertRaises(EngineError) as cm:
            analyze_sequence(big + "A")
        self.assertEqual(cm.exception.code, "too_large")


class Composition(unittest.TestCase):
    def test_counts_and_percentages(self):
        r = analyze_sequence("AAGC")
        self.assertEqual(r["composition"]["counts"], {"A": 2, "C": 1, "G": 1, "U": 0})
        self.assertEqual(r["composition"]["percent"]["A"], 50.0)
        self.assertEqual(r["composition"]["gc_percent"], 50.0)

    def test_single_base(self):
        r = analyze_sequence("G")
        self.assertEqual(r["length"], 1)
        self.assertEqual(r["frames"][0]["codon_count"], 0)
        self.assertEqual(r["frames"][0]["trailing_bases"], 1)
        self.assertEqual(r["frames"][2]["codon_count"], 0)

    def test_incomplete_codons(self):
        r = analyze_sequence("AUGGCUUA")      # 8 nt
        self.assertEqual(r["frames"][0]["codon_count"], 2)
        self.assertEqual(r["frames"][0]["trailing_bases"], 2)
        self.assertEqual(r["frames"][1]["codon_count"], 2)
        self.assertEqual(r["frames"][1]["trailing_bases"], 1)
        self.assertEqual(r["frames"][2]["codon_count"], 2)
        self.assertEqual(r["frames"][2]["trailing_bases"], 0)
        self.assertTrue(r["warnings"])


class Features(unittest.TestCase):
    def test_start_stop_positions_all_frames(self):
        r = analyze_sequence("AUGAUGUAAUGA")
        starts = [(c["pos"], c["frame"]) for c in r["codon_positions"]["start"]]
        stops = [(c["pos"], c["frame"], c["codon"]) for c in r["codon_positions"]["stop"]]
        # A U G A U G U A A U G A: AUG at 0, 3 and 8 (frame 2)
        self.assertEqual(starts, [(0, 0), (3, 0), (8, 2)])
        self.assertEqual(stops, [(1, 1, "UGA"), (6, 0, "UAA"), (9, 0, "UGA")])

    def test_orfs_and_translation(self):
        r = analyze_sequence("CCCAUGGCUACGUAAGGGUGACCC")
        self.assertEqual(len(r["orfs"]), 1)
        orf = r["orfs"][0]
        self.assertEqual((orf["frame"], orf["start"], orf["end"]), (0, 3, 15))
        self.assertEqual(orf["translation"], "MAT*")

    def test_orf_min_length_filter(self):
        seq = "AUGUAA" + "AUGGCUGCUGCUUAA"
        self.assertEqual(len(analyze_sequence(seq)["orfs"]), 2)
        self.assertEqual(len(analyze_sequence(seq, min_orf_codons=3)["orfs"]), 1)

    def test_orf_without_stop_is_not_reported(self):
        self.assertEqual(analyze_sequence("AUGGCUGCU")["orfs"], [])

    def test_overlapping_and_repeated_motifs(self):
        r = analyze_sequence("AAUAAAUAAA", custom_motifs=[{"name": "AA", "pattern": "AA"}])
        m = {x["name"]: x for x in r["motifs"]}
        self.assertEqual([(x["start"], x["end"]) for x in m["Poly(A) signal hexamer"]["matches"]], [(0, 6), (4, 10)])
        self.assertEqual([x["start"] for x in m["AA"]["matches"]], [0, 3, 4, 7, 8])   # overlapping
        r = analyze_sequence("GGGGG")
        gc = next(x for x in r["motifs"] if x["id"] == "gc4")
        self.assertEqual([x["start"] for x in gc["matches"]], [0, 1])   # overlapping windows

    def test_custom_motif_errors(self):
        with self.assertRaises(EngineError):
            analyze_sequence("AUG", custom_motifs=[{"pattern": "(AU"}])
        with self.assertRaises(EngineError):
            analyze_sequence("AUG", custom_motifs=[{"pattern": "A"}] * 6)

    def test_language_properties_come_from_automata(self):
        r = analyze_sequence("GUGA")
        props = {p["language"]: p["accepted"] for p in r["language_properties"]}
        self.assertFalse(props["contains AUG"])
        self.assertTrue(props["contains AUG | GUG | UUG"])
        self.assertTrue(props["even length"])
        self.assertTrue(props["¬ contains AUG"])

    def test_transducers(self):
        r = analyze_sequence("AUGC")
        self.assertEqual(r["transducers"]["complement"], "UACG")
        self.assertEqual(r["transducers"]["reverse_complement"], "GCAU")
        self.assertEqual(r["transducers"]["ry"], "RYRY")
        self.assertEqual(r["transducers"]["codon_boundaries"], "1001")

    def test_orf_trace(self):
        t = orf_trace("CCCAUGGCUACGUAAGGG", 0)
        self.assertEqual([s["action"] for s in t["steps"]], ["skip", "start", "extend", "extend", "accept", "skip"])
        self.assertEqual(t["orfs"], [{"start": 3, "end": 15, "sequence": "AUGGCUACGUAA"}])

    def test_genetic_code(self):
        self.assertEqual(len(GENETIC_CODE), 64)
        self.assertEqual(sorted(c for c, a in GENETIC_CODE.items() if a == "*"), ["UAA", "UAG", "UGA"])
        for codon, aa in {"AUG": "M", "UGG": "W", "UUU": "F", "GGC": "G", "AAA": "K", "CAU": "H"}.items():
            self.assertEqual(GENETIC_CODE[codon], aa)

    def test_motif_pipeline(self):
        r = compile_motif_spec("AUG")
        self.assertEqual(r["counts"]["dfa"], 4)
        self.assertTrue(any(t["symbol"] == "ε" for t in r["nfa"]["transitions"]))
        with self.assertRaises(EngineError):
            compile_motif_spec("AU)")


if __name__ == "__main__":
    unittest.main()
