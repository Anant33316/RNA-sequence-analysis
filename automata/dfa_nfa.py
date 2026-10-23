"""
Regular Languages: DFA / NFA for Open Reading Frame (ORF) detection.

TOC concept: RNA is built from a 4-symbol alphabet {A, C, G, U}. We define
the language of valid ORFs (in a fixed reading frame) as:

    L = { AUG (XYZ)* (UAA | UAG | UGA) : XYZ is any codon }

This is a REGULAR language -- it can be recognized by a finite automaton
that reads the sequence three symbols (one codon) at a time. We build it
first as an NFA-with-epsilon-ish nondeterministic codon matcher, then
determinize it via subset construction into a DFA, mirroring the
epsilon-NFA -> NFA -> DFA pipeline.
"""

import os
import sys
from itertools import product

try:
    from module1_dfa.dfa_basics import build_orf_dfa as _module1_orf_dfa
except ImportError:  # executed directly as a script from inside automata/
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    from module1_dfa.dfa_basics import build_orf_dfa as _module1_orf_dfa

BASES = ["A", "C", "G", "U"]
START_CODON = "AUG"
STOP_CODONS = {"UAA", "UAG", "UGA"}
ALL_CODONS = ["".join(p) for p in product(BASES, repeat=3)]
SENSE_CODONS = [c for c in ALL_CODONS if c not in STOP_CODONS and c != START_CODON]


class DFA:
    """A DFA over the alphabet of codons (each 'symbol' is a 3-letter codon)."""

    def __init__(self, states, alphabet, transitions, start, accept):
        self.states = states
        self.alphabet = alphabet
        self.transitions = transitions  # dict[(state, symbol)] -> state
        self.start = start
        self.accept = accept

    def run(self, codon_sequence):
        """Returns (accepted: bool, path: list[state]) for a list of codons."""
        state = self.start
        path = [state]
        for codon in codon_sequence:
            symbol = self._classify(codon)
            key = (state, symbol)
            if key not in self.transitions:
                return False, path  # dead state / reject
            state = self.transitions[key]
            path.append(state)
        return state in self.accept, path

    @staticmethod
    def _classify(codon):
        if codon == START_CODON:
            return "START"
        if codon in STOP_CODONS:
            return "STOP"
        if len(codon) == 3 and all(b in BASES for b in codon):
            return "SENSE"
        return "INVALID"


def build_orf_dfa():
    """
    Builds the minimal DFA recognizing: START (SENSE)* STOP

    States:
      q0 - initial, no start codon seen yet
      q1 - start codon seen, currently inside an ORF (accepting only after STOP)
      q2 - ORF completed (accepting, dead-end / could chain another ORF)
      qtrap - reject sink
    """
    # Single source of truth: the transition table is the Module 1 ORF DFA
    # (module1_dfa/dfa_basics.py). Notable transitions:
    #   (q1, START) -> q1  AUG can appear mid-ORF as a sense codon (Met)
    #   (q2, START) -> q1  allow scanning into a *new* ORF
    m1 = _module1_orf_dfa()
    return DFA(set(m1.states), set(m1.alphabet), dict(m1.transitions), m1.start, set(m1.accept))


def find_orfs(rna_sequence, frame=0, trace=None):
    """
    Scans rna_sequence in the given reading frame (0, 1, or 2) using the
    ORF DFA, and returns a list of (start_index, end_index, orf_string)
    for every accepted run.

    Scanning strategy (unchanged results): outside an ORF we look for a
    START codon; from that codon on, every codon is fed to the ORF DFA
    (q0 -START-> q1 -SENSE/START-> q1 -STOP-> q2). The DFA reaching its
    accepting state q2 means "START (SENSE|START)* STOP" was recognised,
    i.e. an ORF ends here. Inner AUG codons do not start a nested ORF
    (they are read as methionine inside the current frame).

    `trace` (optional list) receives one record per codon: position,
    codon, its class, the DFA state before/after, and the scanner action.
    """
    rna_sequence = rna_sequence.upper().replace("T", "U")
    dfa = build_orf_dfa()
    orfs = []

    i = frame
    codon_start = None
    state = None  # None = scanning outside any ORF (the DFA is not running)
    while i + 3 <= len(rna_sequence):
        codon = rna_sequence[i:i + 3]
        symbol = DFA._classify(codon)
        before = state
        action = "skip"

        if state is None:
            if symbol == "START":
                codon_start = i
                state = dfa.transitions[(dfa.start, symbol)]  # q0 -START-> q1
                action = "start"
        elif symbol == "INVALID":
            state, codon_start, action = None, None, "abort"  # invalid codon breaks the run
        else:
            state = dfa.transitions[(state, symbol)]
            action = "extend"
            if state in dfa.accept:  # q1 -STOP-> q2: an ORF has been recognised
                orfs.append((codon_start, i + 3, rna_sequence[codon_start:i + 3]))
                action = "accept"
                codon_start, state = None, None
        if trace is not None:
            trace.append({"pos": i, "codon": codon, "class": symbol,
                          "state_before": before or "scan", "state_after": state or ("q2" if action == "accept" else "scan"),
                          "action": action})
        i += 3

    return orfs


def is_valid_orf(codon_sequence):
    """Direct DFA acceptance check for a list of codons (demo of DFA.run)."""
    dfa = build_orf_dfa()
    accepted, path = dfa.run(codon_sequence)
    return accepted, path


if __name__ == "__main__":
    demo_seq = "CCCAUGGCUACGUAAGGG"
    print(f"Sequence: {demo_seq}")
    for f in range(3):
        found = find_orfs(demo_seq, frame=f)
        print(f"  Frame {f}: {found}")
