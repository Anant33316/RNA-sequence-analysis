"""One test class per bug found in the audit (see CHANGELOG.md)."""

import itertools
import random
import unittest
from functools import lru_cache

from tests import _paths  # noqa: F401

from module1_dfa.dfa_basics import DFA
from module1_dfa.closure_properties import product_construction
from module1_dfa.minimization import minimize
from turing.tm_hairpin import TuringMachine, is_hairpin_capable, find_hairpin_stems
from grammars.cfg_structure import fold, can_pair, is_in_language
from grammars.csg_pseudoknot import annotate_crossing_structure, LBA, parse_dot_bracket
from automata.regex_motif import compile_motif, RegexSyntaxError

COMP = {"A": "U", "U": "A", "G": "C", "C": "G"}


def comp_palindrome(w, allow_center=True):
    if len(w) % 2 and not allow_center:
        return False
    return all(COMP[w[i]] == w[len(w) - 1 - i] for i in range(len(w) // 2))


class TuringMachineFix(unittest.TestCase):
    def test_exhaustive_against_definition(self):
        for n in range(0, 8):
            for w in map("".join, itertools.product("ACGU", repeat=n)):
                self.assertEqual(is_hairpin_capable(w), comp_palindrome(w), w)
                self.assertEqual(is_hairpin_capable(w, allow_center=False), comp_palindrome(w, False), w)

    def test_previously_wrong_examples(self):
        for w in ["CCCG", "UAAA", "AAAU", "GCAAGC"]:
            self.assertFalse(is_hairpin_capable(w), w)
        self.assertTrue(is_hairpin_capable("GGGCCC"))

    def test_single_symbol_no_longer_crashes(self):
        for b in "ACGU":
            tm = TuringMachine(b)
            self.assertTrue(tm.run())               # odd centre allowed (original semantics)
            self.assertFalse(TuringMachine(b, allow_center=False).run())

    def test_trace_records_every_transition(self):
        tm = TuringMachine("GC")
        tm.run()
        self.assertEqual(tm.trace[0]["state"], "q_scan")
        self.assertEqual(tm.trace[0]["next_state"], "seek_G")   # remembered base lives in the finite control
        self.assertEqual(tm.state, "ACCEPT")
        self.assertEqual(len(tm.trace), tm.steps)

    def test_scan_results(self):
        self.assertEqual(find_hairpin_stems("CCCGCGCAAA", 4), [(2, 6, "CGCG"), (3, 7, "GCGC")])


class CfgFoldFix(unittest.TestCase):
    @staticmethod
    def brute(seq, ml=3):
        @lru_cache(None)
        def f(i, j):
            if j - i <= 0:
                return 0
            best = f(i + 1, j)
            for k in range(i + ml + 1, j):
                if can_pair(seq[i], seq[k]):
                    best = max(best, 1 + f(i + 1, k) + f(k + 1, j))
            return best
        return f(0, len(seq))

    def assert_valid(self, seq, db, ml):
        stack = []
        for i, c in enumerate(db):
            if c == "(":
                stack.append(i)
            elif c == ")":
                left = stack.pop()
                self.assertTrue(can_pair(seq[left], seq[i]))
                self.assertGreaterEqual(i - left - 1, ml, f"loop too small in {db}")
        self.assertFalse(stack)

    def test_known_hairpins(self):
        self.assertEqual(fold("GGGAAAUCC"), ("(((...)))", 3))
        self.assertEqual(fold("GCAAAGC"), ("((...))", 2))   # first base pairs with the last base

    def test_optimal_against_brute_force(self):
        rng = random.Random(5)
        for _ in range(1500):
            s = "".join(rng.choice("ACGU") for _ in range(rng.randint(0, 18)))
            for ml in (0, 3):
                db, n = fold(s, min_loop=ml)
                self.assertEqual(n, self.brute(s, ml), (s, ml))
                self.assertEqual(db.count("("), n)
                self.assertEqual(len(db), len(s))
                self.assert_valid(s, db, ml)

    def test_membership_language_not_empty_anymore(self):
        self.assertTrue(is_in_language("GC"))
        self.assertTrue(is_in_language("GGCAUGCC"))
        self.assertTrue(is_in_language(""))
        self.assertFalse(is_in_language("GCGCAAAAGCGC"))
        self.assertFalse(is_in_language("GCA"))
        # with every base paired, the innermost pair encloses nothing, so any
        # min_loop > 0 leaves only the empty string (the root cause of the bug)
        rng = random.Random(1)
        for _ in range(300):
            s = "".join(rng.choice("ACGU") for _ in range(rng.randint(1, 12)))
            self.assertFalse(is_in_language(s, min_loop=1))
        self.assertTrue(is_in_language("", min_loop=3))


class MinimizationFix(unittest.TestCase):
    def test_unreachable_states_removed(self):
        d = DFA({"a", "b", "u"}, ["A"], {("a", "A"): "b", ("b", "A"): "a", ("u", "A"): "a"}, "a", {"a", "u"})
        m, _ = minimize(d)
        self.assertEqual(len(m.states), 2)
        trace = {}
        minimize(d, trace=trace)
        self.assertEqual(trace["unreachable_removed"], ["u"])

    def test_witness_strings_really_distinguish(self):
        from module1_dfa.minimization import build_redundant_dfa
        rng = random.Random(3)
        dfas = [build_redundant_dfa()]
        for _ in range(60):
            n = rng.randint(1, 6)
            states = [f"s{i}" for i in range(n)]
            dfas.append(DFA(states, "AB", {(s, a): rng.choice(states) for s in states for a in "AB"},
                            "s0", {s for s in states if rng.random() < .4}))
        for d in dfas:
            trace = {}
            minimize(d, trace=trace)
            total = d.total()
            for cell in trace["table"]:
                if not cell["distinguishable"]:
                    continue
                p, q = cell["pair"]
                w = cell["witness"]
                run = lambda s: _run_from(total, s, w)
                self.assertNotEqual(run(p) in total.accept, run(q) in total.accept, (p, q, w))


def _run_from(dfa, state, word):
    for a in word:
        state = dfa.transitions[(state, a)]
    return state


class ProductAlphabetFix(unittest.TestCase):
    def test_different_alphabets(self):
        d1 = DFA({0}, ["A"], {(0, "A"): 0}, 0, {0})          # A*
        d2 = DFA({0}, ["C"], {(0, "C"): 0}, 0, {0})          # C*
        u = product_construction(d1, d2, "union")
        targets = set(u.transitions.values())
        self.assertTrue(targets <= u.states, "every transition target must be a product state")
        for w in ["", "A", "AA", "C", "CC", "AC", "CA"]:
            self.assertEqual(u.accepts(w), set(w) <= {"A"} or set(w) <= {"C"}, w)
        i = product_construction(d1, d2, "intersection")
        self.assertTrue(i.accepts(""))
        self.assertFalse(i.accepts("A"))


class RegexValidationFix(unittest.TestCase):
    def test_malformed_patterns_rejected(self):
        for bad in ["(AU", "AU)", "*A", "A||U", "()", "AN", "", "A|", "+"]:
            with self.assertRaises(RegexSyntaxError, msg=bad):
                compile_motif(bad)

    def test_valid_patterns(self):
        for ok in ["AUG", "(A|G)C+", "A?U*", "((A))", "(UAA|UAG|UGA)"]:
            compile_motif(ok)


class PseudoknotFix(unittest.TestCase):
    def test_three_way_crossing_gets_three_types(self):
        tape, ok = annotate_crossing_structure("A" * 6, [(0, 3), (1, 4), (2, 5)])
        self.assertEqual(tape, "([{)]}")
        self.assertTrue(ok)

    def test_same_type_never_crosses(self):
        rng = random.Random(9)
        for _ in range(300):
            n = rng.randint(2, 24)
            free = list(range(n))
            rng.shuffle(free)
            pairs = []
            while len(free) >= 2 and len(pairs) < 6:
                a, b = sorted((free.pop(), free.pop()))
                pairs.append((a, b))
            try:
                tape, ok = annotate_crossing_structure("A" * n, pairs)
            except ValueError:
                continue  # needs > 4 bracket types
            self.assertTrue(ok)
            self.assertEqual(sorted(parse_dot_bracket(tape)), sorted(pairs))

    def test_lba_rejects_unbalanced(self):
        for t, expected in [("([)]", True), ("(()", False), ("())", False), ("((]]", False), ("", True),
                            ("(.[.).]", True), ("{<}>", True)]:
            self.assertEqual(LBA(t).accepts(), expected, t)


if __name__ == "__main__":
    unittest.main()
