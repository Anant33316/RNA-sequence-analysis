"""
Module 2: Epsilon Elimination (epsilon-NFA -> NFA without epsilon)
=====================================================================
Standard construction: for each state q, replace its epsilon-closure
transitions with direct transitions -- for every symbol a and every
state r in epsilon_closure(q), add (q, a) -> delta(r, a) directly, and
make q accepting if epsilon_closure(q) contains any original accept
state. The resulting NFA has identical language but zero epsilon
transitions.
"""

try:
    from .nfa_epsilon import NFA, EPSILON, build_altstart_epsilon_nfa
except ImportError:  # executed directly as a script
    from nfa_epsilon import NFA, EPSILON, build_altstart_epsilon_nfa


def eliminate_epsilon(enfa, trace=None):
    """`trace` (optional list) receives, for every state q, its epsilon-closure,
    whether it became accepting (and because of which state), and each new
    direct transition with the closure states it was inherited from."""
    new_transitions = {}
    new_accept = set()

    for q in sorted(enfa.states, key=str):
        closure_q = enfa.epsilon_closure({q})
        reached_accept = sorted(closure_q & enfa.accept, key=str)
        if reached_accept:
            new_accept.add(q)
        rows = []
        for a in sorted(enfa.alphabet, key=str):
            targets = set()
            sources = []
            for r in sorted(closure_q, key=str):
                got = enfa.transitions.get((r, a), set())
                if got:
                    sources.append({"via": r, "to": sorted(got, key=str)})
                targets |= got
            if targets:
                # also close the destination set over epsilon, since after
                # consuming `a` we may again be free to epsilon-move
                closed_targets = set()
                for t in targets:
                    closed_targets |= enfa.epsilon_closure({t})
                new_transitions[(q, a)] = closed_targets
                rows.append({"symbol": a, "sources": sources, "move": sorted(targets, key=str),
                             "result": sorted(closed_targets, key=str)})
        if trace is not None:
            trace.append({"state": q, "closure": sorted(closure_q, key=str),
                          "becomes_accepting": bool(reached_accept), "because_of": reached_accept,
                          "transitions": rows})

    return NFA(enfa.states, enfa.alphabet, new_transitions, enfa.start, new_accept,
               name=f"{enfa.name} [epsilon-eliminated]")


if __name__ == "__main__":
    enfa = build_altstart_epsilon_nfa()
    nfa = eliminate_epsilon(enfa)

    print("Transitions AFTER epsilon elimination (no 'eps' entries remain):")
    for (s, a), targets in sorted(nfa.transitions.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        assert a != EPSILON, "epsilon transition survived elimination!"
        print(f"    δ({s}, {a}) = {sorted(targets)}")
    print(f"\nAccept states after elimination: {sorted(nfa.accept)}")

    tests = ["CCCAUGCCC", "CCCGUGCCC", "CCCUUGCCC", "CCCCCCCCC", "CAUCGU"]
    print("\nCross-checking acceptance is unchanged after elimination:")
    for w in tests:
        a1, a2 = enfa.accepts(w), nfa.accepts(w)
        status = "OK" if a1 == a2 else "MISMATCH"
        print(f"  '{w}': epsilon-NFA={a1}  no-epsilon-NFA={a2}   [{status}]")
        assert a1 == a2
