"""
RNA Sequence Analysis — report generator.

Presentation layer only: calls into module1_dfa/ and module2_nfa/
exactly as before and reports the same computed results, formatted as
a clean analysis report rather than an academic demonstration.
"""

import os
import sys

# make the packages importable no matter which directory this is run from
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from module1_dfa.dfa_basics import build_substring_dfa, build_even_length_dfa, build_orf_dfa
from module1_dfa.closure_properties import product_construction, complement as dfa_complement
from module1_dfa.minimization import minimize, build_redundant_dfa

from module2_nfa.nfa_epsilon import build_altstart_epsilon_nfa
from module2_nfa.epsilon_elimination import eliminate_epsilon
from module2_nfa.subset_construction_equivalence import subset_construction, dfa_accepts, random_test_strings
from module2_nfa.moore_mealy import build_complement_mealy, build_codon_boundary_mealy, build_ry_moore
from automata.dfa_nfa import find_orfs

DEMO_SEQUENCE = "CCCAUGGCUACGUAAGGGUGACCC"

START_CODON = "AUG"
STOP_CODONS = {"UAA", "UAG", "UGA"}


def _classify_codon(codon):
    if codon == START_CODON:
        return "START"
    if codon in STOP_CODONS:
        return "STOP"
    return "SENSE"


def yn(value):
    return "Yes" if value else "No"


def run(seq=DEMO_SEQUENCE):
    # ---------------- computations (same calls as before) ----------------
    dfa_aug = build_substring_dfa("AUG")
    orf_dfa = build_orf_dfa()
    codons = [seq[i:i + 3] for i in range(0, len(seq) - len(seq) % 3, 3)]

    start_codon_detected = "AUG" in codons
    # Whole-string membership: is frame 0, read from the FIRST base, exactly a
    # chain of ORFs (START SENSE* STOP)+ ? (This is what the report used to
    # print as "Open Reading Frame", which said "Absent" even when an ORF
    # was present further along the sequence.)
    whole_sequence_is_orf = orf_dfa.accepts([_classify_codon(c) for c in codons])
    # Scanning: ORFs found anywhere, in each of the three forward frames,
    # by feeding codons to the same ORF DFA from every START codon.
    orfs_by_frame = {f: find_orfs(seq, frame=f) for f in range(3)}
    orf_present = any(orfs_by_frame.values())

    l2 = build_even_length_dfa()
    inter = product_construction(dfa_aug, l2, "intersection")
    union = product_construction(dfa_aug, l2, "union")
    notl1 = dfa_complement(dfa_aug)

    contains_aug = dfa_aug.accepts(seq)
    even_length = l2.accepts(seq)
    intersection_property = inter.accepts(seq)
    union_property = union.accepts(seq)
    complement_property = notl1.accepts(seq)

    redundant = build_redundant_dfa()
    minimized, _groups = minimize(redundant)

    enfa = build_altstart_epsilon_nfa()
    alt_start_detected = enfa.accepts(seq)

    nfa = eliminate_epsilon(enfa)
    epsilon_eliminated = not any(a == "eps" for (_, a) in nfa.transitions)

    dfa = subset_construction(nfa)
    tests = random_test_strings()
    mismatches = sum(
        1 for w in tests
        if not (enfa.accepts(w) == nfa.accepts(w) == dfa_accepts(dfa, w))
    )
    equivalence_confirmed = mismatches == 0

    comp_out, _ = build_complement_mealy().run(seq)
    boundary_out, _ = build_codon_boundary_mealy().run(seq)
    ry_out, _ = build_ry_moore().run(seq)

    # ---------------- report ----------------
    print("=" * 50)
    print("RNA SEQUENCE ANALYSIS REPORT")
    print("=" * 50)

    print("\nInput RNA Sequence:")
    print(seq)

    print("\nGENE DETECTION")
    print("-" * 14)
    print(f"• Start codon detected (frame 0): {yn(start_codon_detected)}")
    print(f"• Codons identified (frame 0): {codons}")
    print(f"• Open Reading Frame (DFA scan, frames 0-2): {'Present' if orf_present else 'Absent'}")
    for f, orfs in orfs_by_frame.items():
        for (s, e, orf) in orfs:
            print(f"    frame {f}: [{s}:{e}] {orf}")
    print(f"• Entire frame-0 sequence is an ORF chain: {yn(whole_sequence_is_orf)}")
    print("  (syntactic pattern: START ... in-frame STOP; not a gene prediction)")

    print("\nSEQUENCE PROPERTIES")
    print("-" * 19)
    print(f"• Contains AUG: {yn(contains_aug)}")
    print(f"• Even length: {yn(even_length)}")
    print(f"• Intersection property: {intersection_property}")
    print(f"• Union property: {union_property}")
    print(f"• Complement property: {complement_property}")

    print("\nAUTOMATON OPTIMIZATION")
    print("-" * 23)
    print(f"• Original DFA states: {len(redundant.states)}")
    print(f"• Minimized DFA states: {len(minimized.states)}")

    print("\nPATTERN ANALYSIS")
    print("-" * 16)
    print(f"• Alternative start codons detected: {yn(alt_start_detected)}")
    print(f"• ε-transitions eliminated: {yn(epsilon_eliminated)}")
    print(f"• Equivalent DFA states generated: {len(dfa['states'])}")

    print("\nRNA TRANSFORMATIONS")
    print("-" * 19)
    print("• Complementary RNA:")
    print(comp_out)
    print("\n• Codon Boundary Map:")
    print(boundary_out)
    print("\n• Purine/Pyrimidine Encoding:")
    print(ry_out[1:])

    print("\nFINAL RESULT")
    print("-" * 12)
    if equivalence_confirmed:
        print("RNA analysis completed successfully.")
    else:
        print("RNA analysis completed with warnings (equivalence check found mismatches).")


if __name__ == "__main__":
    run()
