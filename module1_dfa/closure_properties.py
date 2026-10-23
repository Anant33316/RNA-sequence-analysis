"""
Module 1: Closure Properties of Regular Languages
====================================================
Regular languages are closed under union, intersection, and complement.
We demonstrate this constructively with the PRODUCT AUTOMATON
construction (run two DFAs "in parallel" over a combined state space of
pairs), applied to two concrete RNA properties:

    L1 = { w : "AUG" is a substring of w }   (contains a start codon)
    L2 = { w : |w| is even }                  (even-length sequence)

We build DFAs for L1 ∩ L2, L1 ∪ L2, and complement(L1), and verify the
results against direct Python checks.
"""

try:  # imported as part of the package (web app, tests)
    from .dfa_basics import DFA, build_substring_dfa, build_even_length_dfa, ALPHABET, TRAP
except ImportError:  # executed directly as a script: python closure_properties.py
    from dfa_basics import DFA, build_substring_dfa, build_even_length_dfa, ALPHABET, TRAP

# acceptance rule for each supported product-construction mode
PRODUCT_MODES = {
    "union": (lambda a, b: a or b, "accept if EITHER component accepts (F1 x Q2  U  Q1 x F2)"),
    "intersection": (lambda a, b: a and b, "accept if BOTH components accept (F1 x F2)"),
    "difference": (lambda a, b: a and not b, "accept if the first accepts and the second does not (F1 x (Q2 - F2))"),
    "symmetric_difference": (lambda a, b: a != b, "accept if EXACTLY ONE component accepts"),
}


def product_construction(dfa1, dfa2, mode, reachable_only=False, trace=None):
    """
    mode: 'union', 'intersection', 'difference' or 'symmetric_difference'
    Builds the product DFA over states (s1, s2) with the combined
    accept condition determined by `mode`.

    Both DFAs are first completed over the UNION of their alphabets (a
    symbol unknown to one DFA sends that component to its trap state).
    With reachable_only=False every pair is built (|Q1| x |Q2| states, the
    textbook construction); with reachable_only=True only pairs reachable
    from (start1, start2) are generated.

    `trace` (optional list) receives one structured record per generated
    product state, for the explainable UI.
    """
    if mode not in PRODUCT_MODES:
        raise ValueError("mode must be one of " + ", ".join(PRODUCT_MODES))
    rule, _ = PRODUCT_MODES[mode]
    alphabet = set(dfa1.alphabet) | set(dfa2.alphabet)
    d1, d2 = dfa1.total(alphabet), dfa2.total(alphabet)
    start = (d1.start, d2.start)

    if reachable_only:
        states = {start}
        order = [start]
        i = 0
        while i < len(order):
            s1, s2 = order[i]
            i += 1
            for a in sorted(alphabet, key=str):
                t = (d1.transitions[(s1, a)], d2.transitions[(s2, a)])
                if t not in states:
                    states.add(t)
                    order.append(t)
    else:
        order = sorted(((s1, s2) for s1 in d1.states for s2 in d2.states), key=str)
        states = set(order)

    transitions = {}
    accept = set()
    for (s1, s2) in order:
        moves = []
        for a in sorted(alphabet, key=str):
            t = (d1.transitions[(s1, a)], d2.transitions[(s2, a)])
            transitions[((s1, s2), a)] = t
            moves.append({"symbol": a, "to": t})
        a1, a2 = s1 in d1.accept, s2 in d2.accept
        is_acc = rule(a1, a2)
        if is_acc:
            accept.add((s1, s2))
        if trace is not None:
            trace.append({"state": (s1, s2), "first_accepts": a1, "second_accepts": a2,
                          "accepting": is_acc, "moves": moves})

    name = f"({d1.name}) {mode} ({d2.name})"
    return DFA(states, alphabet, transitions, start, accept, name)


def complement(dfa, trace=None):
    """Complement: swap accepting / non-accepting (requires a TOTAL DFA)."""
    d = dfa.total()
    added_trap = len(d.states) > len(dfa.states)
    accept = d.states - d.accept
    if trace is not None:
        trace.append({"added_trap": added_trap,
                      "trap_state": next(iter(d.states - set(dfa.states)), None),
                      "old_accept": sorted(d.accept, key=str), "new_accept": sorted(accept, key=str)})
    return DFA(d.states, d.alphabet, d.transitions, d.start, accept, f"complement({d.name})")


def _reference_check(w):
    """Ground-truth check computed directly in Python, to verify the DFAs."""
    contains_aug = "AUG" in w
    even_len = len(w) % 2 == 0
    return contains_aug, even_len


if __name__ == "__main__":
    l1 = build_substring_dfa("AUG", name="L1: contains AUG")
    l2 = build_even_length_dfa(name="L2: even length")

    intersection = product_construction(l1, l2, "intersection")
    union = product_construction(l1, l2, "union")
    not_l1 = complement(l1)

    tests = ["CCCAUGGG", "AUGCCC", "CCCCCC", "AUGC", "GGGCUA"]
    print(f"{'string':<12}{'AUG?':<7}{'even?':<8}{'L1∩L2':<8}{'L1∪L2':<8}{'¬L1':<6}")
    for w in tests:
        ref_aug, ref_even = _reference_check(w)
        i = intersection.accepts(w)
        u = union.accepts(w)
        c = not_l1.accepts(w)
        assert i == (ref_aug and ref_even), f"intersection mismatch on {w}"
        assert u == (ref_aug or ref_even), f"union mismatch on {w}"
        assert c == (not ref_aug), f"complement mismatch on {w}"
        print(f"{w:<12}{str(ref_aug):<7}{str(ref_even):<8}{str(i):<8}{str(u):<8}{str(c):<6}")

    print("\nAll closure-construction results match direct reference checks.")
    print(f"|states(L1∩L2)| = {len(intersection.states)}  (= |states(L1)| x |states(L2)| = "
          f"{len(l1.total().states)} x {len(l2.total().states)})")
