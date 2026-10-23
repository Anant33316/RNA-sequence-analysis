"""
Module 2: Non-Deterministic Finite Automata with Epsilon Transitions
=======================================================================
Builds an NFA WITH epsilon transitions for the language:

    L = { w : w contains "AUG" or "GUG" or "UUG" }

(all three are used as alternative start codons in real biology --
GUG and UUG are known bacterial alternative start codons). This is a
natural place for epsilon transitions: a single epsilon-branch state
nondeterministically guesses which of the three codon-alternatives to
try, exactly like a regex union a|b|c compiles to an epsilon-NFA.
"""

EPSILON = "eps"


class NFA:
    def __init__(self, states, alphabet, transitions, start, accept, name="NFA"):
        self.states = set(states)
        self.alphabet = set(alphabet)
        self.transitions = dict(transitions)  # (state, symbol) -> set(states); symbol may be EPSILON
        self.start = start
        self.accept = set(accept)
        self.name = name

    def epsilon_closure(self, states):
        stack = list(states)
        closure = set(states)
        while stack:
            s = stack.pop()
            for nxt in self.transitions.get((s, EPSILON), set()):
                if nxt not in closure:
                    closure.add(nxt)
                    stack.append(nxt)
        return frozenset(closure)

    def epsilon_closure_trace(self, states):
        """Same as epsilon_closure, but also returns the epsilon edges that were
        followed (in discovery order) -- this is what the UI uses to explain
        *why* a state became active without consuming input."""
        stack = sorted(states, key=str)
        closure = set(states)
        edges = []
        while stack:
            s = stack.pop(0)
            for nxt in sorted(self.transitions.get((s, EPSILON), set()), key=str):
                if nxt not in closure:
                    closure.add(nxt)
                    stack.append(nxt)
                    edges.append((s, nxt))
        return frozenset(closure), edges

    def run_trace(self, symbols):
        """Simulate the NFA on `symbols`, recording the full set of active
        states at every step (an NFA is NOT a single path)."""
        current, eps_edges = self.epsilon_closure_trace({self.start})
        initial = {"set": sorted(current, key=str), "epsilon_edges": eps_edges}
        steps = []
        died_at = None
        for i, ch in enumerate(symbols):
            moves = []
            moved = set()
            for s in sorted(current, key=str):
                targets = self.transitions.get((s, ch), set())
                moves.append({"from": s, "to": sorted(targets, key=str)})
                moved |= targets
            closed, edges = self.epsilon_closure_trace(moved)
            steps.append({"index": i, "symbol": ch, "active": sorted(current, key=str),
                          "moves": moves, "after_move": sorted(moved, key=str),
                          "epsilon_edges": edges, "next": sorted(closed, key=str),
                          "in_alphabet": ch in self.alphabet})
            current = closed
            if not current:
                died_at = i
                break
        accepting_reached = sorted(current & self.accept, key=str)
        return {"initial": initial, "steps": steps, "final_set": sorted(current, key=str),
                "accepting_states_in_final_set": accepting_reached,
                "died_at": died_at, "accepted": bool(accepting_reached) and died_at is None}

    def accepts(self, string):
        current = self.epsilon_closure({self.start})
        for ch in string:
            nxt = set()
            for s in current:
                nxt |= self.transitions.get((s, ch), set())
            current = self.epsilon_closure(nxt)
            if not current:
                return False
        return bool(current & self.accept)

    def print_table(self):
        print(f"\nNFA (with epsilon transitions): {self.name}")
        print(f"  States : {sorted(self.states)}")
        print(f"  Start  : {self.start}")
        print(f"  Accept : {sorted(self.accept)}")
        print("  Transitions:")
        for (s, a), targets in sorted(self.transitions.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
            label = "ε" if a == EPSILON else a
            print(f"    δ({s}, {label}) = {sorted(targets)}")


def build_altstart_epsilon_nfa():
    """
    "Contains AUG or GUG or UUG as a substring" -- built directly as an
    epsilon-NFA: a start state can, at any point, epsilon-branch into
    scanning for any of the three codon patterns, then epsilon-merge
    into a shared accept state that self-loops (absorbing, since once
    contained, it stays contained).
    """
    # states: q0 (scan), branch states b1..b3 (epsilon targets of q0),
    # per-codon progress states, and qacc (absorbing accept)
    states = {
        "q0",
        "b1_0", "b1_1", "b1_2",  # AUG progress
        "b2_0", "b2_1", "b2_2",  # GUG progress
        "b3_0", "b3_1", "b3_2",  # UUG progress
        "qacc",
    }
    alphabet = {"A", "C", "G", "U"}
    transitions = {}

    def add(s, a, t):
        transitions.setdefault((s, a), set()).add(t)

    # q0 stays scanning on any symbol (self-loop over all 4 bases: can
    # start trying a codon match at any later position too)
    for a in alphabet:
        add("q0", a, "q0")

    # epsilon-branch from q0 into each of the three codon-matching paths
    add("q0", EPSILON, "b1_0")
    add("q0", EPSILON, "b2_0")
    add("q0", EPSILON, "b3_0")

    codons = {"b1": "AUG", "b2": "GUG", "b3": "UUG"}
    for prefix, codon in codons.items():
        add(prefix + "_0", codon[0], prefix + "_1")
        add(prefix + "_1", codon[1], prefix + "_2")
        add(prefix + "_2", codon[2], "qacc")

    # qacc absorbs everything once reached (pattern already found)
    for a in alphabet:
        add("qacc", a, "qacc")

    return NFA(states, alphabet, transitions, "q0", {"qacc"},
               name="contains AUG|GUG|UUG (epsilon-NFA)")


if __name__ == "__main__":
    nfa = build_altstart_epsilon_nfa()
    nfa.print_table()
    tests = ["CCCAUGCCC", "CCCGUGCCC", "CCCUUGCCC", "CCCCCCCCC", "CAUCGU"]
    print("\nAcceptance tests:")
    for w in tests:
        print(f"  accepts('{w}') = {nfa.accepts(w)}")
