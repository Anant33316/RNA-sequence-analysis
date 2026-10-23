"""Engine tests: validation, traces, conversions, minimization,
equivalence — including randomized property tests against brute force."""

import itertools
import random
import unittest

from tests import _paths  # noqa: F401

from engine.automaton_io import parse_automaton, tokenize, dfa_to_spec
from engine.errors import EngineError
from engine.examples import list_examples, get_example
from engine.simulate import run_spec, describe_spec
from engine.conversions import subset_spec, epsilon_eliminate_spec
from engine.minimize import minimize_spec
from engine.equivalence import check_equivalence, bounded_test, compare


def ex(key):
    return get_example(key)["automaton"]


def words(alphabet, max_len):
    for n in range(max_len + 1):
        for p in itertools.product(alphabet, repeat=n):
            yield list(p)


def accepts(spec, w):
    m, kind, _ = parse_automaton(spec)
    if any(a not in m.alphabet for a in w):
        return False
    return m.accepts(w)


def random_dfa(rng, n, alphabet="AB", partial=False, name="R"):
    states = [f"s{i}" for i in range(n)]
    t = [{"from": s, "symbol": a, "to": rng.choice(states)} for s in states for a in alphabet
         if not (partial and rng.random() < .25)]
    return {"type": "DFA", "name": name, "states": states, "alphabet": list(alphabet), "start": "s0",
            "accept": [s for s in states if rng.random() < .4], "transitions": t}


def random_nfa(rng, n, alphabet="AB", eps=True):
    states = [f"p{i}" for i in range(n)]
    t = []
    for s in states:
        for a in list(alphabet) + (["ε"] if eps else []):
            for d in states:
                if rng.random() < (0.12 if a == "ε" else 0.3):
                    t.append({"from": s, "symbol": a, "to": d})
    return {"type": "NFA", "name": "N", "states": states, "alphabet": list(alphabet), "start": "p0",
            "accept": [s for s in states if rng.random() < .3], "transitions": t}


class Validation(unittest.TestCase):
    def base(self, **kw):
        spec = {"type": "DFA", "states": ["q0", "q1"], "alphabet": ["A", "U"], "start": "q0", "accept": ["q1"],
                "transitions": [{"from": "q0", "symbol": "A", "to": "q1"}]}
        spec.update(kw)
        return spec

    def assertRejected(self, spec, fragment):
        with self.assertRaises(EngineError) as cm:
            parse_automaton(spec)
        self.assertIn(fragment, cm.exception.message)

    def test_valid(self):
        m, kind, _ = parse_automaton(self.base())
        self.assertEqual(kind, "DFA")

    def test_errors(self):
        self.assertRejected(self.base(start="zz"), "start state")
        self.assertRejected(self.base(accept=["zz"]), "accepting state")
        self.assertRejected(self.base(states=[]), "at least one state")
        self.assertRejected(self.base(states=["q0", "q0"]), "duplicate")
        self.assertRejected(self.base(alphabet=["A", "ε"]), "ε cannot")
        self.assertRejected(self.base(transitions=[{"from": "q0", "symbol": "G", "to": "q1"}]), "not in the alphabet")
        self.assertRejected(self.base(transitions=[{"from": "qx", "symbol": "A", "to": "q1"}]), "unknown source")
        self.assertRejected(self.base(transitions=[{"from": "q0", "symbol": "ε", "to": "q1"}]), "cannot have ε")
        self.assertRejected(self.base(transitions=[{"from": "q0", "symbol": "A", "to": "q1"},
                                                   {"from": "q0", "symbol": "A", "to": "q0"}]), "nondeterminism")
        self.assertRejected(self.base(type="PDA"), "type must be")

    def test_tokenize(self):
        self.assertEqual(tokenize("A U\nG", ["A", "G", "U"]), ["A", "U", "G"])
        self.assertEqual(tokenize("START, SENSE STOP", ["START", "SENSE", "STOP"]), ["START", "SENSE", "STOP"])
        with self.assertRaises(EngineError) as cm:
            tokenize("AXG", ["A", "G"])
        self.assertIn("position 1", cm.exception.message)

    def test_every_example_is_valid(self):
        for e in list_examples():
            d = describe_spec(ex(e["id"]))
            self.assertEqual(d["facts"]["state_count"], e["state_count"])
            for inp in e["sample_inputs"]:
                run_spec(ex(e["id"]), inp)


class Traces(unittest.TestCase):
    def test_dfa_trace(self):
        r = run_spec(ex("aug_dfa"), "CAUG")
        self.assertTrue(r["accepted"])
        self.assertEqual([s["state"] for s in r["steps"]], ["q0", "q0", "q1", "q2"])
        self.assertEqual(r["steps"][-1]["next"], "q3")
        self.assertIn("accepting", r["verdict"])

    def test_missing_transition_halts(self):
        r = run_spec(ex("exact_aug"), "AUC")
        self.assertFalse(r["accepted"])
        self.assertEqual(r["halted_at"], 2)
        self.assertFalse(r["steps"][-1]["exists"])
        self.assertEqual(len(r["steps"]), 3)

    def test_empty_string(self):
        self.assertTrue(run_spec(ex("eps_cycle"), "")["accepted"])      # ε reaches f through the closure
        self.assertFalse(run_spec(ex("aug_dfa"), "")["accepted"])
        self.assertTrue(run_spec(ex("even_dfa"), "")["accepted"])

    def test_nfa_tracks_sets_not_paths(self):
        r = run_spec(ex("third_last_g"), "GGA")
        self.assertEqual(r["steps"][0]["next_active"], ["p0", "p1"])
        self.assertEqual(r["steps"][1]["next_active"], ["p0", "p1", "p2"])
        self.assertEqual(r["final_active"], ["p0", "p2", "p3"])
        self.assertTrue(r["accepted"])

    def test_epsilon_cycle_terminates(self):
        r = run_spec(ex("eps_cycle"), "AUAU")
        self.assertTrue(r["accepted"])
        self.assertEqual(r["initial_active"], ["f", "p", "q"])

    def test_nfa_dies(self):
        r = run_spec(ex("eps_cycle"), "UA")
        self.assertFalse(r["accepted"])
        self.assertEqual(r["halted_at"], 0)


class Conversions(unittest.TestCase):
    def test_subset_blowup(self):
        r = subset_spec(ex("third_last_g"))
        self.assertEqual(r["counts"]["dfa_states"], 8)
        self.assertEqual(r["counts"]["possible_subsets"], 16)

    def test_subset_dead_state_option(self):
        with_dead = subset_spec(ex("exact_aug"), True)
        without = subset_spec(ex("exact_aug"), False)
        self.assertIn("∅", with_dead["dfa"]["states"])
        self.assertNotIn("∅", without["dfa"]["states"])

    def test_random_nfas_preserve_language(self):
        rng = random.Random(21)
        for _ in range(120):
            nfa = random_nfa(rng, rng.randint(1, 5))
            dfa = subset_spec(nfa)["dfa"]
            noeps = epsilon_eliminate_spec(nfa)["after"]
            self.assertFalse(any(t["symbol"] == "ε" for t in noeps["transitions"]))
            for w in words("AB", 6):
                expected = accepts(nfa, w)
                self.assertEqual(accepts(dfa, w), expected)
                self.assertEqual(accepts(noeps, w), expected)
            self.assertTrue(check_equivalence(nfa, dfa)["equivalent"])

    def test_subset_on_dfa_input(self):
        r = subset_spec(ex("aug_dfa"))
        self.assertEqual(r["counts"]["dfa_states"], 4)

    def test_eps_elimination_requires_nfa(self):
        with self.assertRaises(EngineError):
            epsilon_eliminate_spec(ex("aug_dfa"))


class Minimization(unittest.TestCase):
    def test_examples(self):
        self.assertEqual(minimize_spec(ex("redundant_dfa"))["counts"]["minimized"], 2)
        r = minimize_spec(ex("unreachable_dfa"))
        self.assertEqual(r["counts"]["unreachable_removed"], ["s2", "s3", "u9"])
        self.assertEqual(r["counts"]["minimized"], 2)
        r = minimize_spec(ex("exact_aug"))
        self.assertEqual(r["counts"]["trap_added"], ["TRAP"])
        self.assertEqual(r["counts"]["minimized"], 5)

    def test_random_dfas_minimal_and_equivalent(self):
        rng = random.Random(4)
        for _ in range(150):
            d = random_dfa(rng, rng.randint(1, 7), partial=rng.random() < .3)
            m = minimize_spec(d)["after"]
            self.assertTrue(check_equivalence(d, m)["equivalent"])
            # minimality: every pair of states in the result is distinguishable
            again = minimize_spec(m)
            self.assertEqual(again["counts"]["minimized"], len(m["states"]))
            self.assertEqual(again["counts"]["unreachable_removed"], [])

    def test_requires_dfa(self):
        with self.assertRaises(EngineError):
            minimize_spec(ex("eps_cycle"))


class Equivalence(unittest.TestCase):
    def test_equivalent_examples(self):
        self.assertTrue(check_equivalence(ex("aug_dfa"), ex("aug_suffix_dfa"))["equivalent"])
        self.assertTrue(check_equivalence(ex("altstart_enfa"), ex("altstart_nfa"))["equivalent"])

    def test_counterexample_is_shortest_and_real(self):
        r = check_equivalence(ex("aug_dfa"), ex("aug_buggy_dfa"))
        self.assertFalse(r["equivalent"])
        self.assertEqual(r["counterexample_text"], "AAUG")
        self.assertEqual(r["verification"], {"a": True, "b": False})

    def test_against_brute_force(self):
        """For DFAs with <= 3 states over {A,B}, any difference shows up on a
        string of length < 3*3+1, so brute force up to length 9 is exact."""
        rng = random.Random(17)
        for _ in range(300):
            a, b = random_dfa(rng, rng.randint(1, 3)), random_dfa(rng, rng.randint(1, 3))
            r = check_equivalence(a, b)
            diffs = [w for w in words("AB", 9) if accepts(a, w) != accepts(b, w)]
            self.assertEqual(r["equivalent"], not diffs)
            if diffs:
                self.assertEqual(len(r["counterexample"]), min(len(w) for w in diffs))
                self.assertNotEqual(accepts(a, r["counterexample"]), accepts(b, r["counterexample"]))

    def test_different_alphabets(self):
        a = {"type": "DFA", "states": ["x"], "alphabet": ["A"], "start": "x", "accept": ["x"],
             "transitions": [{"from": "x", "symbol": "A", "to": "x"}]}
        b = dict(a, alphabet=["A", "C"])
        b["transitions"] = a["transitions"] + [{"from": "x", "symbol": "C", "to": "x"}]
        r = check_equivalence(a, b)
        self.assertFalse(r["equivalent"])
        self.assertEqual(r["counterexample"], ["C"])

    def test_bounded_test(self):
        r = bounded_test(ex("aug_dfa"), ex("aug_buggy_dfa"), max_length=5, random_count=50)
        self.assertTrue(r["disagreement_found"])
        self.assertGreater(r["mismatch_count"], 0)
        self.assertEqual(r["exhaustive_strings"], sum(4 ** k for k in range(6)))
        ok = bounded_test(ex("aug_dfa"), ex("aug_suffix_dfa"), max_length=5)
        self.assertFalse(ok["disagreement_found"])
        self.assertIn("NOT", ok["method"])
        with self.assertRaises(EngineError):
            bounded_test(ex("aug_dfa"), ex("aug_dfa"), max_length=12)

    def test_compare(self):
        r = compare(ex("altstart_enfa"), subset_spec(ex("altstart_enfa"))["dfa"], "CGUG")
        self.assertTrue(r["runs"]["agree"])
        self.assertLess(r["stats"]["a"]["states"], r["stats"]["b"]["states"])


class Serialization(unittest.TestCase):
    def test_label_collisions_are_disambiguated(self):
        from module1_dfa.dfa_basics import DFA
        d = DFA({("a, b", "c"), ("a", "b, c")}, ["A"], {(("a, b", "c"), "A"): ("a", "b, c"),
                                                         (("a", "b, c"), "A"): ("a, b", "c")},
                ("a, b", "c"), set())
        spec = dfa_to_spec(d)
        self.assertEqual(len(set(spec["states"])), 2)


if __name__ == "__main__":
    unittest.main()
