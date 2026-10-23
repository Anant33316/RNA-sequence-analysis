"""
Built-in example automata.

RNA examples are produced by the ORIGINAL builder functions of the
project (no hand-copied tables); a few classic textbook machines are
added to exercise edge cases (epsilon cycles, unreachable states, partial
DFAs, exponential subset blow-up).
"""

from __future__ import annotations

from module1_dfa.dfa_basics import build_substring_dfa, build_even_length_dfa, build_orf_dfa, ALPHABET
from module1_dfa.minimization import build_redundant_dfa
from module2_nfa.nfa_epsilon import build_altstart_epsilon_nfa
from module2_nfa.epsilon_elimination import eliminate_epsilon

from .automaton_io import dfa_to_spec, nfa_to_spec
from .errors import EngineError

BASES = list(ALPHABET)


def _aug_dfa() -> dict:
    pattern = "AUG"
    dfa = build_substring_dfa(pattern)
    rename = {i: f"q{i}" for i in dfa.states}
    desc = {f"q{i}": (f"longest matched prefix: '{pattern[:i]}'" if 0 < i < len(pattern)
                      else "nothing matched yet" if i == 0 else f"'{pattern}' has been found (absorbing)")
            for i in dfa.states}
    return dfa_to_spec(dfa, "contains AUG (start codon) — KMP DFA", rename=rename, descriptions=desc)


def _even_dfa() -> dict:
    return dfa_to_spec(build_even_length_dfa(), "even length",
                       descriptions={"EVEN": "read an even number of bases", "ODD": "read an odd number of bases"})


def _orf_dfa() -> dict:
    return dfa_to_spec(build_orf_dfa(), "ORF (codon level): START (SENSE)* STOP",
                       descriptions={"q0": "no START codon read yet", "q1": "inside an open reading frame",
                                     "q2": "ORF closed by a STOP codon (accepting)",
                                     "qtrap": "invalid order — reject sink"})


def _redundant_dfa() -> dict:
    return dfa_to_spec(build_redundant_dfa(), "ends in A (redundant, 4 states)",
                       descriptions={"q0": "start", "q1": "last base was A", "q2": "last base was not A",
                                     "q3": "last base was A (duplicate of q1)"})


def _altstart_enfa() -> dict:
    return nfa_to_spec(build_altstart_epsilon_nfa(), "contains AUG | GUG | UUG (ε-NFA)",
                       descriptions={"q0": "scanning", "qacc": "an alternative start codon was found",
                                     "b1_0": "try AUG", "b2_0": "try GUG", "b3_0": "try UUG"})


def _altstart_nfa() -> dict:
    return nfa_to_spec(eliminate_epsilon(build_altstart_epsilon_nfa()),
                       "contains AUG | GUG | UUG (ε-eliminated NFA)")


def _stop_codon_nfa() -> dict:
    t = [{"from": "q0", "symbol": a, "to": "q0"} for a in BASES]
    t += [{"from": "q0", "symbol": "U", "to": "u"},
          {"from": "u", "symbol": "A", "to": "ua"}, {"from": "u", "symbol": "G", "to": "ug"},
          {"from": "ua", "symbol": "A", "to": "stop"}, {"from": "ua", "symbol": "G", "to": "stop"},
          {"from": "ug", "symbol": "A", "to": "stop"}]
    t += [{"from": "stop", "symbol": a, "to": "stop"} for a in BASES]
    return {"type": "NFA", "name": "contains a stop codon (UAA | UAG | UGA)", "states": ["q0", "u", "ua", "ug", "stop"],
            "alphabet": BASES, "start": "q0", "accept": ["stop"], "transitions": t,
            "descriptions": {"q0": "scanning; may guess a stop codon starts here", "u": "read U",
                             "ua": "read UA", "ug": "read UG", "stop": "stop codon found"}}


def _third_from_last_nfa() -> dict:
    t = [{"from": "p0", "symbol": a, "to": "p0"} for a in BASES]
    t.append({"from": "p0", "symbol": "G", "to": "p1"})
    t += [{"from": "p1", "symbol": a, "to": "p2"} for a in BASES]
    t += [{"from": "p2", "symbol": a, "to": "p3"} for a in BASES]
    return {"type": "NFA", "name": "3rd symbol from the end is G", "states": ["p0", "p1", "p2", "p3"],
            "alphabet": BASES, "start": "p0", "accept": ["p3"], "transitions": t,
            "descriptions": {"p0": "waiting; guesses which G is 3rd from the end", "p1": "guessed G",
                             "p2": "one more symbol", "p3": "exactly two symbols after the guessed G"}}


def _epsilon_cycle_nfa() -> dict:
    t = [{"from": "p", "symbol": "ε", "to": "q"}, {"from": "q", "symbol": "ε", "to": "p"},
         {"from": "q", "symbol": "A", "to": "r"}, {"from": "r", "symbol": "U", "to": "p"},
         {"from": "p", "symbol": "ε", "to": "f"}]
    return {"type": "NFA", "name": "(AU)* with an ε-cycle", "states": ["p", "q", "r", "f"],
            "alphabet": ["A", "U"], "start": "p", "accept": ["f"], "transitions": t,
            "descriptions": {"p": "between repeats", "q": "ε-cycle partner of p", "r": "read A, expecting U",
                             "f": "accepting exit"}}


def _unreachable_dfa() -> dict:
    t = []
    for a in BASES:
        t.append({"from": "s0", "symbol": a, "to": "s1" if a == "G" else "s0"})
        t.append({"from": "s1", "symbol": a, "to": "s1" if a == "G" else "s0"})
        t.append({"from": "s2", "symbol": a, "to": "s3" if a == "G" else "s2"})
        t.append({"from": "s3", "symbol": a, "to": "s3" if a == "G" else "s2"})
        t.append({"from": "u9", "symbol": a, "to": "s1"})
    return {"type": "DFA", "name": "ends in G (with unreachable copies)", "states": ["s0", "s1", "s2", "s3", "u9"],
            "alphabet": BASES, "start": "s0", "accept": ["s1", "s3"], "transitions": t,
            "descriptions": {"s2": "unreachable copy of s0", "s3": "unreachable copy of s1",
                             "u9": "unreachable"}}


def _exact_aug_partial() -> dict:
    t = [{"from": "q0", "symbol": "A", "to": "q1"}, {"from": "q1", "symbol": "U", "to": "q2"},
         {"from": "q2", "symbol": "G", "to": "q3"}]
    return {"type": "DFA", "name": "exactly AUG (partial DFA)", "states": ["q0", "q1", "q2", "q3"],
            "alphabet": BASES, "start": "q0", "accept": ["q3"], "transitions": t,
            "descriptions": {"q3": "read exactly AUG"}}


def _suffix_aug_dfa() -> dict:
    """Alternative (non-minimal-looking but different) DFA for 'contains AUG' used
    to demonstrate equivalence checking against the KMP DFA: states remember the
    last two bases directly."""
    states, t = [], []
    names = ["", "A", "AU"]
    for i, n in enumerate(names):
        states.append(f"m{i}")
    states.append("hit")
    for i, n in enumerate(names):
        for a in BASES:
            w = n + a
            if w.endswith("AUG"):
                nxt = "hit"
            elif w.endswith("AU"):
                nxt = "m2"
            elif w.endswith("A"):
                nxt = "m1"
            else:
                nxt = "m0"
            t.append({"from": f"m{i}", "symbol": a, "to": nxt})
    t += [{"from": "hit", "symbol": a, "to": "hit"} for a in BASES]
    return {"type": "DFA", "name": "contains AUG (suffix-tracking DFA)", "states": states, "alphabet": BASES,
            "start": "m0", "accept": ["hit"], "transitions": t}


def _buggy_aug_dfa() -> dict:
    """A deliberately WRONG 'contains AUG' DFA (forgets that 'A' can restart a
    match after 'AU' fails) — used to show counterexample generation."""
    t = [{"from": "q0", "symbol": a, "to": "q1" if a == "A" else "q0"} for a in BASES]
    t += [{"from": "q1", "symbol": a, "to": "q2" if a == "U" else "q0"} for a in BASES]
    t += [{"from": "q2", "symbol": a, "to": "q3" if a == "G" else "q0"} for a in BASES]
    t += [{"from": "q3", "symbol": a, "to": "q3"} for a in BASES]
    return {"type": "DFA", "name": "contains AUG (BUGGY: forgets overlapping A)", "states": ["q0", "q1", "q2", "q3"],
            "alphabet": BASES, "start": "q0", "accept": ["q3"], "transitions": t}


EXAMPLES = {
    "aug_dfa": ("RNA", "DFA recognising sequences that contain the start codon AUG, built by the "
                       "project's KMP construction.", _aug_dfa, ["CCAUGG", "AAUG", "AUAUG", "CCCC", ""]),
    "even_dfa": ("RNA", "Two-state DFA for even-length sequences.", _even_dfa, ["AUGC", "AUG", ""]),
    "orf_dfa": ("RNA", "Codon-level DFA for one open reading frame: input symbols are codon CLASSES.",
                _orf_dfa, ["START SENSE SENSE STOP", "START STOP START SENSE STOP", "SENSE START STOP", ""]),
    "redundant_dfa": ("Minimization", "Over-specified DFA for 'ends in A' with equivalent states.",
                      _redundant_dfa, ["CCA", "AAAA", "GGG", ""]),
    "altstart_enfa": ("RNA", "ε-NFA guessing one of the alternative start codons AUG/GUG/UUG.",
                      _altstart_enfa, ["CCCGUGCC", "CAUCGU", "UUG", ""]),
    "altstart_nfa": ("RNA", "The same language after the project's ε-elimination.", _altstart_nfa,
                     ["CCCGUGCC", "CAUCGU"]),
    "stop_nfa": ("RNA", "NFA guessing where a stop codon starts.", _stop_codon_nfa, ["AUGGCUUAA", "AUGGCC", "UGA"]),
    "third_last_g": ("Classic", "NFA whose DFA needs 2³ = 8 states (subset blow-up).", _third_from_last_nfa,
                     ["AGCU", "GAAA", "CCGUA", "GG"]),
    "eps_cycle": ("Classic", "ε-NFA with an ε-cycle p ↔ q; accepts (AU)*.", _epsilon_cycle_nfa,
                  ["", "AU", "AUAU", "AUA", "UA"]),
    "unreachable_dfa": ("Minimization", "DFA with unreachable states that minimization removes.",
                        _unreachable_dfa, ["AUG", "GGA", ""]),
    "exact_aug": ("Classic", "Partial DFA with missing transitions (rejects on undefined moves).",
                  _exact_aug_partial, ["AUG", "AUGA", "AU", "C"]),
    "aug_suffix_dfa": ("Verification", "A differently built DFA for 'contains AUG' — equivalent to the KMP DFA.",
                       _suffix_aug_dfa, ["AAUG", "AUAUG"]),
    "aug_buggy_dfa": ("Verification", "A subtly wrong 'contains AUG' DFA — not equivalent (find the counterexample).",
                      _buggy_aug_dfa, ["AAUG", "AUG"]),
}


def list_examples() -> list[dict]:
    out = []
    for key, (category, description, builder, inputs) in EXAMPLES.items():
        spec = builder()
        out.append({"id": key, "category": category, "description": description, "name": spec["name"],
                    "type": spec["type"], "state_count": len(spec["states"]), "sample_inputs": inputs})
    return out


def get_example(key: str) -> dict:
    if key not in EXAMPLES:
        raise EngineError(f"unknown example '{key}'", "id", code="not_found")
    category, description, builder, inputs = EXAMPLES[key]
    spec = builder()
    return {"id": key, "category": category, "description": description, "sample_inputs": inputs,
            "automaton": spec}
