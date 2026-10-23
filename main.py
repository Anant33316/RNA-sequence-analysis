"""
RNA Sequence Analysis via Theory of Computation
=================================================
Ties together every level of the Chomsky hierarchy used in this project:

  Regular          -> automata/dfa_nfa.py, automata/regex_motif.py
  Context-Free     -> grammars/cfg_structure.py
  Context-Sensitive-> grammars/csg_pseudoknot.py
  Recursively Enum.-> turing/tm_hairpin.py   (decidable subset, via TM)

Run:  python3 main.py [RNA_SEQUENCE]
If no sequence is given, a demo sequence is analyzed.
"""

import sys

from automata.dfa_nfa import find_orfs
from automata.regex_motif import compile_motif, dfa_search
from grammars.cfg_structure import fold
from grammars.csg_pseudoknot import has_pseudoknot, annotate_crossing_structure
from turing.tm_hairpin import find_hairpin_stems

DEMO_SEQUENCE = "CCCAUGGCUACGCGCUAAUAAAGGGUAG"
MOTIF_LIBRARY = {
    "Poly-A signal": "AAUAAA",
    "GC-rich box": "(G|C)(G|C)(G|C)(G|C)",
}


def section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def analyze(sequence):
    sequence = "".join(sequence.split()).upper().replace("T", "U")
    bad = [(i, c) for i, c in enumerate(sequence) if c not in "ACGU"]
    if not sequence:
        raise ValueError("empty sequence")
    if bad:
        i, c = bad[0]
        raise ValueError(f"invalid nucleotide {c!r} at position {i} "
                         f"({len(bad)} invalid character(s) in total); allowed: A, C, G, U (T is read as U)")
    print(f"Input RNA sequence ({len(sequence)} nt): {sequence}")

    # ---- 1. Regular languages: ORF scan across all 3 reading frames ----
    section("1. REGULAR LANGUAGE — DFA: Open Reading Frame detection")
    for frame in range(3):
        orfs = find_orfs(sequence, frame=frame)
        print(f"  Frame {frame}: {orfs if orfs else 'no ORF found'}")

    # ---- 2. Regular languages: regex -> NFA -> DFA motif search ----
    section("2. REGULAR LANGUAGE — Regex/NFA/DFA: motif search")
    for name, pattern in MOTIF_LIBRARY.items():
        dfa = compile_motif(pattern)
        matches = dfa_search(dfa, sequence)
        print(f"  {name} (/{pattern}/): {matches if matches else 'no match'}")

    # ---- 3. Context-free: secondary structure folding ----
    section("3. CONTEXT-FREE GRAMMAR — CYK: secondary structure prediction")
    structure, npairs = fold(sequence, min_loop=3)
    print(f"  Sequence : {sequence}")
    print(f"  Structure: {structure}")
    print(f"  Predicted base pairs: {npairs}")

    # derive (i, j) pairs from the dot-bracket string for the pseudoknot check
    stack, pairs = [], []
    for idx, ch in enumerate(structure):
        if ch == "(":
            stack.append(idx)
        elif ch == ")":
            pairs.append((stack.pop(), idx))

    # ---- 4. Context-sensitive: pseudoknot check ----
    section("4. CONTEXT-SENSITIVE — LBA: pseudoknot detection")
    # NOTE: the CFG can only produce NESTED pairs, so this check is always
    # False on its output -- it demonstrates the checker, not a discovery.
    found, culprits = has_pseudoknot(pairs)
    print(f"  Base pairs from CFG fold: {sorted(pairs)}")
    print(f"  Pseudoknot present: {found}" + (f" (crossing pair: {culprits})" if found else ""))
    if pairs:
        tape_str, accepted = annotate_crossing_structure(sequence, pairs)
        print(f"  LBA bracket verification: {tape_str} -> valid: {accepted}")

    # ---- 5. Turing machine: hairpin-capable stems ----
    section("5. TURING MACHINE — hairpin (complement-palindrome) stems")
    hits = find_hairpin_stems(sequence, min_len=4, max_len=8)
    if hits:
        for start, end, sub in hits:
            print(f"  [{start}:{end}] {sub}")
    else:
        print("  none found in length range 4–8")

    section("Chomsky hierarchy summary")
    print("  Regular            : ORF scanning, motif search")
    print("  Context-Free       : base-pair nesting / secondary structure")
    print("  Context-Sensitive  : pseudoknots (crossing base pairs)")
    print("  Turing-decidable   : hairpin/complement-palindrome check")


if __name__ == "__main__":
    seq = sys.argv[1] if len(sys.argv) > 1 else DEMO_SEQUENCE
    try:
        analyze(seq)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
