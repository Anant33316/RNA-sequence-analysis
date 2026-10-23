"""Regression tests: behaviour of the ORIGINAL submission that must not change."""

import itertools
import os
import subprocess
import sys
import unittest

from tests import _paths  # noqa: F401
from tests._paths import ROOT

from module1_dfa.dfa_basics import build_substring_dfa, build_even_length_dfa, build_orf_dfa
from module1_dfa.closure_properties import product_construction, complement
from module1_dfa.minimization import minimize, build_redundant_dfa
from module1_dfa.regular_vs_nonregular import pumping_lemma_counterexample, is_in_language as gncn
from module2_nfa.nfa_epsilon import build_altstart_epsilon_nfa
from module2_nfa.epsilon_elimination import eliminate_epsilon
from module2_nfa.subset_construction_equivalence import subset_construction, dfa_accepts, random_test_strings
from module2_nfa.moore_mealy import build_complement_mealy, build_codon_boundary_mealy, build_ry_moore
from automata.dfa_nfa import find_orfs
from automata.regex_motif import compile_motif, dfa_search


def all_strings(max_len, alphabet="ACGU"):
    for n in range(max_len + 1):
        for p in itertools.product(alphabet, repeat=n):
            yield "".join(p)


class OriginalModule1(unittest.TestCase):
    def test_kmp_substring_dfa_is_exact(self):
        # exhaustive over every string of length <= 7 for several patterns, incl. self-overlapping ones
        for pattern in ["AUG", "AAA", "AUAU", "AAUAA", "GCGC"]:
            dfa = build_substring_dfa(pattern)
            for w in all_strings(7):
                self.assertEqual(dfa.accepts(w), pattern in w, (pattern, w))

    def test_closure_demo_table_unchanged(self):
        l1, l2 = build_substring_dfa("AUG"), build_even_length_dfa()
        inter = product_construction(l1, l2, "intersection")
        union = product_construction(l1, l2, "union")
        neg = complement(l1)
        for w in all_strings(6):
            self.assertEqual(inter.accepts(w), "AUG" in w and len(w) % 2 == 0)
            self.assertEqual(union.accepts(w), "AUG" in w or len(w) % 2 == 0)
            self.assertEqual(neg.accepts(w), "AUG" not in w)
        self.assertEqual(len(inter.states), 8)  # |Q1| x |Q2| = 4 x 2 (full product is still the default)

    def test_redundant_dfa_minimizes_to_two_states(self):
        m, groups = minimize(build_redundant_dfa())
        self.assertEqual(len(m.states), 2)
        self.assertEqual(sorted(sorted(g) for g in groups.values()), [["q0", "q2"], ["q1", "q3"]])

    def test_orf_dfa_already_minimal(self):
        m, _ = minimize(build_orf_dfa())
        self.assertEqual(len(m.states), 4)

    def test_pumping_lemma_all_splits_fail(self):
        for p in range(1, 8):
            s, results = pumping_lemma_counterexample(p)
            self.assertEqual(s, "G" * p + "C" * p)
            self.assertTrue(all(not r[4] for r in results))
        self.assertTrue(gncn("") and gncn("GGCC") and not gncn("GGCCC") and not gncn("CCGG"))


class OriginalModule2(unittest.TestCase):
    def test_enfa_nfa_dfa_agree_on_original_98_strings(self):
        enfa = build_altstart_epsilon_nfa()
        nfa = eliminate_epsilon(enfa)
        dfa = subset_construction(nfa)
        tests = random_test_strings()
        self.assertEqual(len(tests), 98)
        for w in tests:
            self.assertEqual(enfa.accepts(w), nfa.accepts(w))
            self.assertEqual(nfa.accepts(w), dfa_accepts(dfa, w))
        self.assertEqual(len(dfa["states"]), 15)  # value printed by the original report

    def test_enfa_language(self):
        enfa = build_altstart_epsilon_nfa()
        for w in all_strings(6):
            self.assertEqual(enfa.accepts(w), any(c in w for c in ("AUG", "GUG", "UUG")), w)

    def test_transducer_outputs_unchanged(self):
        seq = "CCCAUGGCUACGUAAGGGUGACCC"  # demo sequence of main_module1_2.py
        self.assertEqual(build_complement_mealy().run(seq)[0], "GGGUACCGAUGCAUUCCCACUGGG")
        self.assertEqual(build_codon_boundary_mealy().run(seq)[0], "100" * 8)
        self.assertEqual(build_ry_moore().run(seq)[0][1:], "YYYRYRRYYRYRYRRRRRYRRYYY")


class OriginalDrafts(unittest.TestCase):
    def test_find_orfs_demo(self):
        self.assertEqual(find_orfs("CCCAUGGCUACGUAAGGG", 0), [(3, 15, "AUGGCUACGUAA")])
        self.assertEqual(find_orfs("CCCAUGGCUACGUAAGGG", 1), [])

    def test_find_orfs_matches_reference_scanner(self):
        """The DFA-driven scanner must give exactly the results of the original
        hand-written scan (kept here as an oracle)."""
        import random

        def reference(seq, frame):
            stops, orfs, i, start = {"UAA", "UAG", "UGA"}, [], frame, None
            while i + 3 <= len(seq):
                c = seq[i:i + 3]
                if c == "AUG" and start is None:
                    start = i
                elif start is not None and c in stops:
                    orfs.append((start, i + 3, seq[start:i + 3]))
                    start = None
                i += 3
            return orfs
        rng = random.Random(11)
        for _ in range(3000):
            s = "".join(rng.choice("ACGU") for _ in range(rng.randint(0, 80)))
            for f in range(3):
                self.assertEqual(find_orfs(s, f), reference(s, f), (s, f))

    def test_regex_motif_search(self):
        self.assertEqual(dfa_search(compile_motif("AAUAAA"), "CCCGAAUAAAGGGACGCGU"), [(4, 10, "AAUAAA")])
        self.assertEqual(dfa_search(compile_motif("(A|G)C(A|G)C"), "CCCGAAUAAAGGGACGCGU"), [(13, 17, "ACGC")])


class EntryPoints(unittest.TestCase):
    def _run(self, *args, cwd=None):
        return subprocess.run([sys.executable, *args], cwd=cwd or ROOT, capture_output=True, text=True, timeout=120)

    def test_main_module1_2_runs_from_any_directory(self):
        out = self._run(os.path.join(ROOT, "main_module1_2.py"), cwd=os.path.dirname(ROOT))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("RNA analysis completed successfully.", out.stdout)
        self.assertIn("Open Reading Frame (DFA scan, frames 0-2): Present", out.stdout)

    def test_main_py_runs_and_validates(self):
        out = self._run("main.py")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("((...))((((.(.((...)..))))))", out.stdout)
        bad = self._run("main.py", "AUGXX")
        self.assertEqual(bad.returncode, 2)
        self.assertIn("invalid nucleotide 'X' at position 3", bad.stderr)

    def test_every_module_script_runs(self):
        scripts = ["module1_dfa/dfa_basics.py", "module1_dfa/closure_properties.py", "module1_dfa/minimization.py",
                   "module1_dfa/regular_vs_nonregular.py", "module2_nfa/nfa_epsilon.py",
                   "module2_nfa/epsilon_elimination.py", "module2_nfa/subset_construction_equivalence.py",
                   "module2_nfa/moore_mealy.py", "automata/dfa_nfa.py", "automata/regex_motif.py",
                   "grammars/cfg_structure.py", "grammars/csg_pseudoknot.py", "turing/tm_hairpin.py"]
        for rel in scripts:
            folder, name = os.path.split(os.path.join(ROOT, rel))
            out = self._run(name, cwd=folder)
            self.assertEqual(out.returncode, 0, f"{rel}: {out.stderr}")


if __name__ == "__main__":
    unittest.main()
