"""
Context-Free Grammars & Pushdown Automata: RNA secondary structure.

TOC concept: RNA secondary structure is dominated by NESTED base pairs
(Watson-Crick A-U, G-C, plus the wobble pair G-U), which form stems and
loops. Nested pairing is exactly what a context-free grammar (and its
machine model, the pushdown automaton -- a stack naturally matches
nested brackets) can express, but a *regular* grammar cannot: you cannot
track "how many opens are still unmatched" with finitely many states.

Grammar (informal, not yet in CNF):

    S -> a S u | u S a | g S c | c S g | g S u | u S g      (a base pair enclosing a substructure)
        | S S                                                (two adjacent substructures / stems)
        | a S | c S | g S | u S                              (an unpaired base, e.g. a loop/bulge base)
        | eps

This is parsed with a CYK-style O(n^3) dynamic program: table[i][j] holds
the set of ways S can generate sequence[i:j]. Because the grammar mixes
paired and unpaired productions, we track, for every subrange, whether it
is derivable from S, and reconstruct a traceback into a dot-bracket
string identical in spirit to the classical Nussinov algorithm --
Nussinov's DP *is* CYK parsing of this exact grammar.
"""

PAIRS = {
    frozenset({"A", "U"}),
    frozenset({"G", "C"}),
    frozenset({"G", "U"}),  # wobble pair
}


def can_pair(b1, b2):
    return frozenset({b1, b2}) in PAIRS


def fold(rna_sequence, min_loop=3, trace=None):
    """
    CYK-style dynamic program over the secondary-structure CFG.
    Returns a dot-bracket string ('.' = unpaired, '(' / ')' = paired).

    min_loop: minimum number of unpaired bases required inside a hairpin
    loop (biologically realistic RNA loops need >=3 bases due to
    backbone geometry) -- this restricts which 'S -> b_i S b_j' productions
    are allowed, same role a semantic/context restriction plays alongside
    a CFG in real bioinformatics grammars.
    """
    seq = rna_sequence.upper().replace("T", "U")
    n = len(seq)
    # best[i][j] = max number of base pairs derivable from seq[i:j)
    best = [[0] * (n + 1) for _ in range(n + 1)]
    choice = [[None] * (n + 1) for _ in range(n + 1)]  # traceback info

    for length in range(1, n + 1):
        for i in range(0, n - length + 1):
            j = i + length
            # Option 1: leave seq[i] unpaired -> S -> a S
            best_here = best[i + 1][j]
            best_choice = ("unpaired", i)

            # Option 2: pair seq[i] with seq[k-1] for some k in (i, j],
            # leaving >= min_loop bases inside the pair.
            # (Bug fix: the first draft used range(i + min_loop + 1, j), which
            # allowed loops of only min_loop-1 bases AND never let seq[i] pair
            # with the last base seq[j-1] of the interval.)
            for k in range(i + min_loop + 2, j + 1):
                if can_pair(seq[i], seq[k - 1]):
                    inside = best[i + 1][k - 1]
                    outside = best[k][j]
                    candidate = inside + 1 + outside
                    if candidate > best_here:
                        best_here = candidate
                        best_choice = ("paired", i, k - 1, k)

            # Option 3: split into two adjacent substructures S -> S S
            for k in range(i + 1, j):
                candidate = best[i][k] + best[k][j]
                if candidate > best_here:
                    best_here = candidate
                    best_choice = ("split", k)

            best[i][j] = best_here
            choice[i][j] = best_choice

    dot_bracket = ["."] * n

    def traceback(i, j):
        if i >= j:
            return
        c = choice[i][j]
        if c[0] == "unpaired":
            traceback(i + 1, j)
        elif c[0] == "paired":
            _, left, right, k = c
            dot_bracket[left] = "("
            dot_bracket[right] = ")"
            traceback(i + 1, right)
            traceback(k, j)
        elif c[0] == "split":
            k = c[1]
            traceback(i, k)
            traceback(k, j)

    traceback(0, n)
    if trace is not None:
        trace["tree"] = _parse_tree(choice, 0, n)
        trace["table"] = best
    return "".join(dot_bracket), best[0][n]


def _parse_tree(choice, i, j):
    """Rebuild the parse tree of S for seq[i:j] from the DP choices.
    Node kinds map 1:1 onto grammar productions:
      'eps'      S -> eps
      'unpaired' S -> x S
      'pair'     S -> x S y           (pair closes the whole interval)
      'split'    S -> S S             (a pair followed by more structure, or an explicit split)
    """
    if i >= j:
        return {"kind": "eps", "span": (i, j)}
    c = choice[i][j]
    if c[0] == "unpaired":
        return {"kind": "unpaired", "span": (i, j), "pos": i, "child": _parse_tree(choice, i + 1, j)}
    if c[0] == "paired":
        _, left, right, k = c
        pair_node = {"kind": "pair", "span": (left, right + 1), "pos": (left, right),
                     "child": _parse_tree(choice, left + 1, right)}
        if k == j:
            return pair_node
        return {"kind": "split", "span": (i, j), "left": pair_node, "right": _parse_tree(choice, k, j)}
    k = c[1]
    return {"kind": "split", "span": (i, j), "left": _parse_tree(choice, i, k), "right": _parse_tree(choice, k, j)}


def leftmost_derivation(sequence, tree, max_steps=400):
    """Turn a parse tree into a leftmost derivation: a list of
    (production, sentential_form) pairs, starting from 'S'."""
    seq = sequence.upper().replace("T", "U")
    form = [tree]          # items: terminal strings or tree nodes (= nonterminal S)
    steps = [("start", "S")]

    def render(items):
        return " ".join(x if isinstance(x, str) else "S" for x in items) or "eps"

    while len(steps) <= max_steps:
        idx = next((k for k, x in enumerate(form) if not isinstance(x, str)), None)
        if idx is None:
            break
        node = form[idx]
        kind = node["kind"]
        if kind == "eps":
            repl, prod = [], "S -> eps"
        elif kind == "unpaired":
            b = seq[node["pos"]]
            repl, prod = [b, node["child"]], f"S -> {b} S"
        elif kind == "pair":
            l, r = node["pos"]
            repl, prod = [seq[l], node["child"], seq[r]], f"S -> {seq[l]} S {seq[r]}"
        else:
            repl, prod = [node["left"], node["right"]], "S -> S S"
        form = form[:idx] + repl + form[idx + 1:]
        steps.append((prod, render(form)))
    truncated = any(not isinstance(x, str) for x in form)
    return steps, truncated


def is_in_language(rna_sequence, min_loop=0):
    """
    Membership test: does S derive this ENTIRE sequence with every base
    paired (a 'perfect' nested structure, no unpaired bases)? Useful as a
    pure CFG-membership demo distinct from the optimization above.

    Grammar used here: S -> x S y (x,y a valid pair) | S S | eps.
    min_loop now defaults to 0. (Bug fix: with the old default of 3 the
    language was EMPTY for every non-empty string.) Reason: when every base
    is paired, the INNERMOST pair always encloses zero bases, so any
    min_loop > 0 rules out every non-empty string -- a hairpin loop needs
    unpaired bases, which this grammar has no production for. The
    parameter is kept for compatibility; the optimisation in fold() is
    the one that models loops.
    """
    seq = rna_sequence.upper().replace("T", "U")
    n = len(seq)
    if n % 2 != 0:
        return False
    # derivable[i][j] = True if S ->* seq[i:j] using ONLY the pairing
    # and split productions (no unpaired-base production)
    derivable = [[False] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        derivable[i][i] = True  # epsilon

    for length in range(2, n + 1, 2):
        for i in range(0, n - length + 1):
            j = i + length
            ok = False
            if length - 2 >= min_loop and can_pair(seq[i], seq[j - 1]):
                if derivable[i + 1][j - 1]:
                    ok = True
            if not ok:
                for k in range(i + 2, j - 1, 2):
                    if derivable[i][k] and derivable[k][j]:
                        ok = True
                        break
            derivable[i][j] = ok
    return derivable[0][n]


if __name__ == "__main__":
    seq = "GGGAAAUCC"  # small hairpin: GGG ... loop ... UCC roughly pairs
    structure, npairs = fold(seq, min_loop=3)
    print(f"Sequence : {seq}")
    print(f"Structure: {structure}  ({npairs} base pairs)")

    perfect = "GCGCAAAAGCGC"
    print(f"\nMembership test on '{perfect}': {is_in_language(perfect)}  (A-A cannot pair)")
    perfect2 = "GGCAUGCC"
    print(f"Membership test on '{perfect2}': {is_in_language(perfect2)}")
