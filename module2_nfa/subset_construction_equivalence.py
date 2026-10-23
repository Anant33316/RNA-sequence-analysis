"""
Module 2: Subset Construction (NFA -> DFA) and Equivalence of NFA and DFA
============================================================================
Standard subset construction: each DFA state is a SET of NFA states
(the set of states the NFA could simultaneously be in). Applied here to
the epsilon-free NFA produced by epsilon_elimination.py, completing the
pipeline:

    epsilon-NFA  --[eliminate_epsilon]-->  NFA  --[subset construction]--> DFA

We then verify NFA/DFA EQUIVALENCE empirically: run both machines on a
battery of test strings (including ones not in nfa_epsilon.py's demo)
and confirm identical accept/reject verdicts on every one.
"""

import itertools

try:
    from .nfa_epsilon import build_altstart_epsilon_nfa
    from .epsilon_elimination import eliminate_epsilon
except ImportError:  # executed directly as a script
    from nfa_epsilon import build_altstart_epsilon_nfa
    from epsilon_elimination import eliminate_epsilon


def subset_construction(nfa, include_dead_state=False, trace=None):
    """
    Subset construction. Works for epsilon-free NFAs (as before) AND for
    epsilon-NFAs: every subset is closed under epsilon moves, which is a
    no-op when the NFA has no epsilon transitions.

    include_dead_state=False keeps the original behaviour (transitions to
    the empty set are omitted -> partial DFA). With True, the empty set is
    added as an explicit dead state so the resulting DFA is total.

    `trace` (optional dict) records the initial closure, every processed
    subset in order (FIFO), each symbol's move/closure/result and whether
    the result was a NEW subset, and why accepting subsets accept.
    """
    start, start_edges = nfa.epsilon_closure_trace({nfa.start})
    dfa_states = {start}
    order = [start]
    unmarked = [start]
    dfa_transitions = {}
    dfa_accept = set()
    processed = []

    while unmarked:
        current = unmarked.pop(0)  # FIFO -> subsets are numbered breadth-first
        reason = sorted(current & nfa.accept, key=str)
        if reason:
            dfa_accept.add(current)
        rows = []
        for a in sorted(nfa.alphabet, key=str):
            moved = set()
            for s in current:
                moved |= nfa.transitions.get((s, a), set())
            closed, edges = nfa.epsilon_closure_trace(moved)
            nxt = frozenset(closed)
            is_new = nxt not in dfa_states
            rows.append({"symbol": a, "move": sorted(moved, key=str), "epsilon_edges": edges,
                         "result": nxt, "new": is_new and (bool(nxt) or include_dead_state)})
            if not nxt and not include_dead_state:
                continue  # implicit dead/trap state, omitted for brevity
            dfa_transitions[(current, a)] = nxt
            if is_new:
                dfa_states.add(nxt)
                order.append(nxt)
                unmarked.append(nxt)
        processed.append({"subset": current, "accepting": bool(reason), "accepting_because": reason,
                          "rows": rows})

    if trace is not None:
        trace.update({"start_closure": start, "start_epsilon_edges": start_edges,
                      "processed": processed, "order": order,
                      "nfa_state_count": len(nfa.states)})

    return {
        "states": dfa_states,
        "start": start,
        "accept": dfa_accept,
        "transitions": dfa_transitions,
        "alphabet": nfa.alphabet,
    }


def dfa_accepts(dfa, string):
    state = dfa["start"]
    for ch in string:
        key = (state, ch)
        if key not in dfa["transitions"]:
            return False
        state = dfa["transitions"][key]
    return state in dfa["accept"]


def random_test_strings():
    """A batch of strings not all previously used, to stress-test equivalence."""
    bases = "ACGU"
    fixed = ["", "A", "AUG", "GUG", "UUG", "AUGGUG", "CCCC", "UGA", "GAUUGCC",
             "AAAAAAAA", "UUUUUUUU", "CAUGC", "GGUGGG"]
    # a handful of short exhaustive strings to be thorough
    exhaustive = ["".join(p) for length in range(0, 4) for p in itertools.product(bases, repeat=length)]
    return fixed + exhaustive


if __name__ == "__main__":
    enfa = build_altstart_epsilon_nfa()
    nfa = eliminate_epsilon(enfa)
    dfa = subset_construction(nfa)

    print(f"Epsilon-NFA states : {len(enfa.states)}")
    print(f"NFA states (no eps): {len(nfa.states)}")
    print(f"DFA states (subset construction): {len(dfa['states'])}")
    print("\nSample of DFA states (each is a SET of NFA states):")
    for s in list(dfa["states"])[:5]:
        print(f"  {sorted(s)}")

    tests = random_test_strings()
    mismatches = 0
    for w in tests:
        a_enfa = enfa.accepts(w)
        a_nfa = nfa.accepts(w)
        a_dfa = dfa_accepts(dfa, w)
        if not (a_enfa == a_nfa == a_dfa):
            mismatches += 1
            print(f"  MISMATCH on '{w}': eNFA={a_enfa} NFA={a_nfa} DFA={a_dfa}")

    print(f"\nTested {len(tests)} strings (epsilon-NFA vs NFA vs DFA).")
    if mismatches == 0:
        print("All three machines agree on every test string -> NFA and DFA")
        print("(and the epsilon-NFA they came from) are EQUIVALENT: they")
        print("recognize exactly the same language, confirming the")
        print("epsilon-NFA = NFA = DFA equivalence theorem for this example.")
    else:
        print(f"{mismatches} mismatches found -- equivalence broken, check construction.")
