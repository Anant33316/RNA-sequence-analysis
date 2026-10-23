"""
Module 1: Deterministic Finite Automata (DFA)
================================================
- Chomsky hierarchy (intro, printed in main script)
- Introduction to FA, examples
- Language acceptance and string acceptance by a DFA
- (closure properties, minimization, regular/non-regular -> separate files)

This file: a reusable DFA class + a couple of concrete DFA examples over
the RNA alphabet {A, C, G, U}, used by every other file in this module.
"""

TRAP = "TRAP"


class DFA:
    def __init__(self, states, alphabet, transitions, start, accept, name="DFA"):
        self.states = set(states)
        self.alphabet = set(alphabet)
        self.transitions = dict(transitions)  # (state, symbol) -> state
        self.start = start
        self.accept = set(accept)
        self.name = name

    def total(self, alphabet=None):
        """Make the DFA total, adding a trap state only if any transition is missing.

        `alphabet` (optional) completes the DFA over a LARGER alphabet -- needed
        when two DFAs over different alphabets are combined in a product
        construction. Symbols the DFA never used lead to the trap state.
        """
        alphabet = set(self.alphabet) | set(alphabet or ())
        missing = any((s, a) not in self.transitions for s in self.states for a in alphabet)
        if not missing:
            return DFA(self.states, alphabet, self.transitions, self.start, self.accept, self.name)
        trap = TRAP
        while trap in self.states:          # never collide with a user state named "TRAP"
            trap = trap + "'"
        states = set(self.states) | {trap}
        transitions = dict(self.transitions)
        for s in self.states:
            for a in alphabet:
                if (s, a) not in transitions:
                    transitions[(s, a)] = trap
        for a in alphabet:
            transitions[(trap, a)] = trap
        return DFA(states, alphabet, transitions, self.start, self.accept, self.name)

    def accepts(self, string):
        state = self.start
        for ch in string:
            key = (state, ch)
            if key not in self.transitions:
                return False
            state = self.transitions[key]
        return state in self.accept

    def run_trace(self, symbols):
        """Run the DFA and record every step (used by the explainable UI).

        Returns a dict with one record per consumed symbol. If a transition is
        missing (partial DFA), the run halts there and the string is rejected.
        """
        state = self.start
        steps = []
        halted_at = None
        for i, ch in enumerate(symbols):
            key = (state, ch)
            exists = key in self.transitions
            nxt = self.transitions[key] if exists else None
            steps.append({"index": i, "state": state, "symbol": ch, "next": nxt, "exists": exists,
                          "in_alphabet": ch in self.alphabet})
            if not exists:
                halted_at = i
                break
            state = nxt
        accepted = halted_at is None and state in self.accept
        return {"steps": steps, "final_state": None if halted_at is not None else state,
                "halted_at": halted_at, "accepted": accepted}

    def reachable_states(self):
        """States reachable from the start state (breadth-first)."""
        seen = {self.start}
        queue = [self.start]
        while queue:
            s = queue.pop(0)
            for a in sorted(self.alphabet, key=str):
                t = self.transitions.get((s, a))
                if t is not None and t not in seen:
                    seen.add(t)
                    queue.append(t)
        return seen

    def print_table(self):
        print(f"\nDFA: {self.name}")
        print(f"  States : {sorted(self.states, key=str)}")
        print(f"  Start  : {self.start}")
        print(f"  Accept : {sorted(self.accept, key=str)}")
        print("  Transition table:")
        for (s, a), t in sorted(self.transitions.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
            print(f"    δ({s}, {a}) = {t}")


ALPHABET = ["A", "C", "G", "U"]


def build_substring_dfa(pattern, alphabet=ALPHABET, name=None):
    """
    DFA recognizing { w : pattern is a substring of w }, built with the
    KMP failure-function technique (standard construction: each state =
    length of the longest prefix of `pattern` currently matched).
    """
    m = len(pattern)
    # failure function
    fail = [0] * m
    k = 0
    for i in range(1, m):
        while k > 0 and pattern[i] != pattern[k]:
            k = fail[k - 1]
        if pattern[i] == pattern[k]:
            k += 1
        fail[i] = k

    states = list(range(m + 1))
    transitions = {}
    for state in range(m + 1):
        for a in alphabet:
            if state == m:
                # already saw the full pattern once -> absorbing accept
                # state, since "contains pattern" stays true forever
                transitions[(state, a)] = m
                continue
            if a == pattern[state]:
                transitions[(state, a)] = state + 1
            else:
                # KMP mismatch step: fall back through the failure function
                # to find the longest prefix of `pattern` that is still a
                # suffix of (matched-so-far + a).
                k2 = state
                nxt = 0
                while True:
                    if k2 == 0:
                        nxt = 1 if pattern[0] == a else 0
                        break
                    if k2 < m and pattern[k2] == a:
                        nxt = k2 + 1
                        break
                    k2 = fail[k2 - 1]
                transitions[(state, a)] = nxt
    accept = {m}
    return DFA(states, alphabet, transitions, 0, accept, name or f"contains '{pattern}'").total()


def build_even_length_dfa(alphabet=ALPHABET, name="even length"):
    states = ["EVEN", "ODD"]
    transitions = {}
    for a in alphabet:
        transitions[("EVEN", a)] = "ODD"
        transitions[("ODD", a)] = "EVEN"
    return DFA(states, alphabet, transitions, "EVEN", {"EVEN"}, name)


def build_orf_dfa(alphabet=None, name="ORF: START (SENSE)* STOP, codon-level"):
    """
    Same ORF DFA as before, but expressed at the CODON level (alphabet =
    the 64 codons classified into START/SENSE/STOP) since that's the
    natural symbol granularity for reading frames.
    """
    codon_alphabet = ["START", "SENSE", "STOP"]
    states = {"q0", "q1", "q2", "qtrap"}
    accept = {"q2"}
    transitions = {
        ("q0", "START"): "q1", ("q0", "SENSE"): "qtrap", ("q0", "STOP"): "qtrap",
        ("q1", "SENSE"): "q1", ("q1", "STOP"): "q2", ("q1", "START"): "q1",
        ("q2", "SENSE"): "qtrap", ("q2", "STOP"): "qtrap", ("q2", "START"): "q1",
        ("qtrap", "SENSE"): "qtrap", ("qtrap", "STOP"): "qtrap", ("qtrap", "START"): "qtrap",
    }
    return DFA(states, codon_alphabet, transitions, "q0", accept, name)


if __name__ == "__main__":
    dfa = build_substring_dfa("AUG")
    dfa.print_table()
    for test in ["CCCAUGGGG", "CCCCCCC", "AAUGCC"]:
        print(f"  accepts('{test}') = {dfa.accepts(test)}")

    even = build_even_length_dfa()
    print(f"\n{even.name}: accepts('AUGC') = {even.accepts('AUGC')}, accepts('AUG') = {even.accepts('AUG')}")
