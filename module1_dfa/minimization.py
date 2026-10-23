"""
Module 1: Minimization of Finite Automata
============================================
Implements the classical TABLE-FILLING (Myhill-Nerode) minimization
algorithm:

  1. Start with all pairs of states unmarked.
  2. Mark (p, q) if exactly one of p, q is accepting.
  3. Repeat: mark (p, q) if for some symbol a, (delta(p,a), delta(q,a))
     is already marked. Repeat until no change.
  4. Unmarked pairs are equivalent -> merge them into single states.

Applied to a deliberately redundant DFA over the RNA alphabet, and to
the ORF DFA, to show the state-count reduction explicitly.
"""

try:
    from .dfa_basics import DFA, build_orf_dfa, ALPHABET
except ImportError:  # executed directly as a script
    from dfa_basics import DFA, build_orf_dfa, ALPHABET


def remove_unreachable(dfa):
    """Drop states that cannot be reached from the start state.

    Table-filling only merges EQUIVALENT states; it never deletes
    unreachable ones, so without this step the result is not guaranteed
    to be minimal.
    """
    keep = dfa.reachable_states()
    transitions = {(s, a): t for (s, a), t in dfa.transitions.items() if s in keep}
    removed = set(dfa.states) - keep
    return DFA(keep, dfa.alphabet, transitions, dfa.start, dfa.accept & keep, dfa.name), removed


def minimize(dfa, trace=None):
    """
    Table-filling minimization. Returns (minimized_dfa, groups) exactly as
    before; `groups` maps a root index to the list of merged original states.

    `trace` (optional dict) is filled with a structured, step-by-step record
    of the run: unreachable states removed, trap completion, the pairs
    marked in round 0 (accepting vs non-accepting), every pair marked in
    later rounds together with the WITNESS symbol and the already-marked
    successor pair that justifies it, the partition after each round, and
    the final equivalence classes.
    """
    reachable, removed = remove_unreachable(dfa)
    d = reachable.total()
    added_trap = sorted(set(d.states) - set(reachable.states), key=str)
    states = sorted(d.states, key=str)
    alphabet = sorted(d.alphabet, key=str)
    n = len(states)
    idx = {s: i for i, s in enumerate(states)}

    marked = [[False] * n for _ in range(n)]
    reason = {}  # (i, j) -> record explaining why the pair is distinguishable

    # round 0: mark pairs differing in accept/non-accept (distinguished by the empty string)
    round0 = []
    for i in range(n):
        for j in range(i + 1, n):
            if (states[i] in d.accept) != (states[j] in d.accept):
                marked[i][j] = True
                rec = {"pair": (states[i], states[j]), "round": 0, "symbol": None, "via": None,
                       "witness": []}
                reason[(i, j)] = rec
                round0.append(rec)

    def partition_now():
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for i in range(n):
            for j in range(i + 1, n):
                if not marked[i][j]:
                    ri, rj = find(i), find(j)
                    if ri != rj:
                        parent[ri] = rj
        blocks = {}
        for i, s in enumerate(states):
            blocks.setdefault(find(i), []).append(s)
        return sorted((sorted(b, key=str) for b in blocks.values()), key=lambda b: str(b[0]))

    rounds = [{"round": 0, "newly_marked": round0, "partition": partition_now()}]

    # rounds 1, 2, ...: mark (p, q) if some symbol leads to a pair marked in an
    # EARLIER round. Using the previous round's table (not the one being
    # updated) makes round k = "distinguishable by a string of length <= k".
    k = 0
    while True:
        k += 1
        snapshot = [row[:] for row in marked]
        newly = []
        for i in range(n):
            for j in range(i + 1, n):
                if snapshot[i][j]:
                    continue
                for a in alphabet:
                    ni = idx[d.transitions[(states[i], a)]]
                    nj = idx[d.transitions[(states[j], a)]]
                    lo, hi = min(ni, nj), max(ni, nj)
                    if ni != nj and snapshot[lo][hi]:
                        marked[i][j] = True
                        via = reason[(lo, hi)]
                        rec = {"pair": (states[i], states[j]), "round": k, "symbol": a,
                               "via": (d.transitions[(states[i], a)], d.transitions[(states[j], a)]),
                               # a distinguishing string: a followed by the successors' witness
                               "witness": [a] + via["witness"]}
                        reason[(i, j)] = rec
                        newly.append(rec)
                        break
        if not newly:
            break
        rounds.append({"round": k, "newly_marked": newly, "partition": partition_now()})

    # step 4: union-find style grouping of unmarked (equivalent) pairs
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(n):
        for j in range(i + 1, n):
            if not marked[i][j]:
                union(i, j)

    groups = {}
    for i, s in enumerate(states):
        root = find(i)
        groups.setdefault(root, []).append(s)

    rep_of = {}
    for root, members in groups.items():
        rep = min(members, key=str)
        for m in members:
            rep_of[m] = rep

    new_states = set(rep_of.values())
    new_start = rep_of[d.start]
    new_accept = {rep_of[s] for s in d.accept}
    new_transitions = {}
    for (s, a), t in d.transitions.items():
        new_transitions[(rep_of[s], a)] = rep_of[t]

    if trace is not None:
        trace.update({
            "original_state_count": len(dfa.states),
            "unreachable_removed": sorted(removed, key=str),
            "trap_added": added_trap,
            "states": states,
            "rounds": rounds,
            "table": [{"pair": (states[i], states[j]), "distinguishable": marked[i][j],
                       "round": reason[(i, j)]["round"] if marked[i][j] else None,
                       "symbol": reason[(i, j)]["symbol"] if marked[i][j] else None,
                       "witness": reason[(i, j)]["witness"] if marked[i][j] else None}
                      for i in range(n) for j in range(i + 1, n)],
            "classes": sorted((sorted(m, key=str) for m in groups.values()), key=lambda b: str(b[0])),
            "representative": rep_of,
            "minimized_state_count": len(new_states),
        })

    return DFA(new_states, d.alphabet, new_transitions, new_start, new_accept,
               f"minimized({d.name})"), groups


def build_redundant_dfa():
    """
    A deliberately over-specified DFA for L = { w : w ends in 'A' } over
    {A, C, G, U}, with duplicate/equivalent states q1 and q3 that a
    naive construction might introduce (e.g. from an unoptimized regex
    compile). Minimization should collapse them.
    """
    states = {"q0", "q1", "q2", "q3"}
    alphabet = ALPHABET
    accept = {"q1", "q3"}
    transitions = {}
    for a in alphabet:
        transitions[("q0", a)] = "q1" if a == "A" else "q2"
        transitions[("q1", a)] = "q3" if a == "A" else "q2"
        transitions[("q2", a)] = "q1" if a == "A" else "q2"
        transitions[("q3", a)] = "q3" if a == "A" else "q2"
    return DFA(states, alphabet, transitions, "q0", accept, "redundant ends-in-A DFA")


if __name__ == "__main__":
    redundant = build_redundant_dfa()
    minimized, groups = minimize(redundant)
    print(f"Original states : {len(redundant.states)}  {sorted(redundant.states)}")
    print(f"Minimized states: {len(minimized.states)}  {sorted(minimized.states, key=str)}")
    print("Equivalence classes found:")
    for root, members in groups.items():
        print(f"  {sorted(members, key=str)}")

    for w in ["CCA", "AAAA", "GGG", "UCA"]:
        assert redundant.accepts(w) == minimized.accepts(w), f"mismatch on {w}"
    print("All test strings agree between original and minimized DFA.\n")

    orf = build_orf_dfa()
    orf_min, orf_groups = minimize(orf)
    print(f"ORF DFA: {len(orf.total().states)} states -> minimized: {len(orf_min.states)} states")
