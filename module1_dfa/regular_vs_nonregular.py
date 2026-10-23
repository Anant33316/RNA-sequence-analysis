"""
Module 1: Regular Languages vs Non-Regular Languages
=======================================================
Everything so far (ORF detection, motif containment, even length) is
REGULAR. To show the boundary of what finite automata can do, we prove
-- constructively, via the Pumping Lemma for regular languages -- that
the language of "perfectly nested stems"

    L = { G^n C^n : n >= 0 }   (n G's followed by exactly n C's)

is NOT regular. (This is the same reason the FULL RNA secondary
structure language needs a context-free grammar, not a DFA -- covered
in a later module; this file only needs Module 1 concepts.)

Pumping Lemma: if L were regular, there would be a DFA with some number
of states p such that every string s in L with |s| >= p can be split
s = xyz with |xy| <= p, |y| >= 1, and xy^i z in L for every i >= 0.

We give a constructive counterexample generator: for any candidate
pumping length p, take s = G^p C^p, and show that pumping ANY valid
split (with |xy| <= p, so y consists only of G's) produces a string
with unequal G and C counts, hence NOT of the form G^n C^n. Since this
holds no matter what p is, no such p can exist, so L is not regular.
"""


def is_in_language(s):
    """Ground-truth membership check for L = { G^n C^n : n >= 0 }."""
    n_g = 0
    i = 0
    while i < len(s) and s[i] == "G":
        n_g += 1
        i += 1
    n_c = 0
    while i < len(s) and s[i] == "C":
        n_c += 1
        i += 1
    return i == len(s) and n_g == n_c


def pumping_lemma_counterexample(p):
    """
    For a candidate pumping length p, construct s = G^p C^p and show
    that EVERY valid split x y z (|xy| <= p, |y| >= 1) fails to stay in
    L when pumped (specifically, pumping down with i=0 already breaks
    it, since y is all G's and removing it unbalances the counts).
    Returns a list of (x, y, z, pumped_string, still_in_L) records.
    """
    s = "G" * p + "C" * p
    assert is_in_language(s), "sanity check: s should be in L"

    results = []
    # |xy| <= p forces y to lie entirely within the G-block
    for len_xy in range(1, p + 1):
        for len_y in range(1, len_xy + 1):
            len_x = len_xy - len_y
            x = s[:len_x]
            y = s[len_x:len_x + len_y]
            z = s[len_xy:]
            pumped = x + (y * 0) + z  # i = 0: "pump down"
            still_in_L = is_in_language(pumped)
            results.append((x, y, z, pumped, still_in_L))
    return s, results


def demonstrate(p=4):
    s, results = pumping_lemma_counterexample(p)
    print(f"Candidate pumping length p = {p}")
    print(f"s = G^{p} C^{p} = '{s}'  (in L: {is_in_language(s)}, |s| = {len(s)} >= p)")
    print("\nChecking every valid split s = xyz with |xy| <= p, |y| >= 1:")
    all_fail = True
    for (x, y, z, pumped, still_in_L) in results:
        status = "STILL in L (ok)" if still_in_L else "NOT in L -> contradiction!"
        if still_in_L:
            all_fail = False
        print(f"  x='{x}' y='{y}' z='{z}'  ->  xy^0z = '{pumped}'   {status}")
    print()
    if all_fail:
        print(f"Every split leads to a contradiction for p={p}. Since this argument")
        print("works for ANY p (the G-block always has length p, so y is always")
        print("all-G's and removing it always unbalances the counts), no valid")
        print("pumping length can exist. Therefore L = {G^n C^n} is NOT regular.")
    else:
        print("Unexpected: found a split that survives pumping (should not happen for this L).")


if __name__ == "__main__":
    demonstrate(p=4)
    print("\n--- sanity: membership checks ---")
    for w in ["GGCC", "GGGCCC", "GGCCC", "GC", "", "CCGG"]:
        print(f"  '{w}' in L: {is_in_language(w)}")
