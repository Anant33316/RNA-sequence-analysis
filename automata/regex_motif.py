"""
Regular Languages, take 2: Regex -> NFA (Thompson's construction) ->
DFA (subset construction) -> minimized DFA, applied to RNA motif search.

TOC concept: every regular expression describes a regular language, and
every regular language has an equivalent minimal DFA. We build that
pipeline explicitly instead of using Python's `re` module, so every stage
of the automata theory pipeline is visible: this is the same
epsilon-NFA -> NFA -> DFA -> minimal DFA pipeline you're using for the
DFA construction / minimality proofs coursework, just applied to RNA
motifs (e.g. Shine-Dalgarno-like sequences, poly-A signals) instead of
toy alphabets.

Supported regex syntax: literals over {A,C,G,U}, concatenation, `|`
(union), `*` (Kleene star), `+`, `?`, and parentheses for grouping.
"""

import threading

EPSILON = "eps"
_COMPILE_LOCK = threading.Lock()  # NFAState ids come from a shared counter
MAX_PATTERN_LENGTH = 200


class RegexSyntaxError(ValueError):
    """Raised for malformed motif patterns, with the offending position."""

    def __init__(self, message, position):
        super().__init__(f"{message} (at position {position})")
        self.position = position


class NFAState:
    _counter = 0

    def __init__(self):
        self.id = NFAState._counter
        NFAState._counter += 1
        self.transitions = {}  # symbol -> set[NFAState], EPSILON included

    def add_transition(self, symbol, state):
        self.transitions.setdefault(symbol, set()).add(state)


class NFAFragment:
    """A fragment with one start state and one accept state (Thompson style)."""

    def __init__(self, start, accept):
        self.start = start
        self.accept = accept


# ---------- Regex parser (recursive descent) -> Thompson's construction ----------

class RegexParser:
    def __init__(self, pattern, alphabet=("A", "C", "G", "U")):
        self.pattern = pattern
        self.pos = 0
        self.alphabet = set(alphabet)

    def peek(self):
        return self.pattern[self.pos] if self.pos < len(self.pattern) else None

    def consume(self):
        ch = self.peek()
        self.pos += 1
        return ch

    def parse(self):
        if not self.pattern:
            raise RegexSyntaxError("empty pattern", 0)
        if len(self.pattern) > MAX_PATTERN_LENGTH:
            raise RegexSyntaxError(f"pattern longer than {MAX_PATTERN_LENGTH} characters", MAX_PATTERN_LENGTH)
        frag = self.parse_union()
        if self.peek() == ")":
            raise RegexSyntaxError("unmatched ')'", self.pos)
        return frag

    def parse_union(self):
        left = self.parse_concat()
        while self.peek() == "|":
            self.consume()
            right = self.parse_concat()
            left = self._union(left, right)
        return left

    def parse_concat(self):
        pieces = []
        while self.peek() is not None and self.peek() not in ")|":
            pieces.append(self.parse_star())
        if not pieces:
            # an empty alternative such as "A|" or "(|A)" -- reject instead of
            # silently treating it as epsilon; '?' expresses optionality
            raise RegexSyntaxError("empty alternative (use '?' to make something optional)", self.pos)
        frag = pieces[0]
        for nxt in pieces[1:]:
            frag = self._concat(frag, nxt)
        return frag

    def parse_star(self):
        frag = self.parse_atom()
        while self.peek() in ("*", "+", "?"):
            op = self.consume()
            if op == "*":
                frag = self._star(frag)
            elif op == "+":
                frag = self._plus(frag)
            elif op == "?":
                frag = self._optional(frag)
        return frag

    def parse_atom(self):
        ch = self.peek()
        if ch == "(":
            open_pos = self.pos
            self.consume()
            frag = self.parse_union()
            if self.peek() != ")":
                raise RegexSyntaxError("unclosed '('", open_pos)
            self.consume()
            return frag
        if ch in ("*", "+", "?"):
            raise RegexSyntaxError(f"'{ch}' has nothing to repeat", self.pos)
        if ch not in self.alphabet:
            raise RegexSyntaxError(
                f"'{ch}' is not a symbol of the alphabet {{{', '.join(sorted(self.alphabet))}}}", self.pos)
        self.consume()
        return self._literal(ch)

    # ---- Thompson construction primitives ----
    @staticmethod
    def _literal(symbol):
        s0, s1 = NFAState(), NFAState()
        s0.add_transition(symbol, s1)
        return NFAFragment(s0, s1)

    @staticmethod
    def _concat(a, b):
        a.accept.add_transition(EPSILON, b.start)
        return NFAFragment(a.start, b.accept)

    @staticmethod
    def _union(a, b):
        s0, s1 = NFAState(), NFAState()
        s0.add_transition(EPSILON, a.start)
        s0.add_transition(EPSILON, b.start)
        a.accept.add_transition(EPSILON, s1)
        b.accept.add_transition(EPSILON, s1)
        return NFAFragment(s0, s1)

    @staticmethod
    def _star(a):
        s0, s1 = NFAState(), NFAState()
        s0.add_transition(EPSILON, a.start)
        s0.add_transition(EPSILON, s1)
        a.accept.add_transition(EPSILON, a.start)
        a.accept.add_transition(EPSILON, s1)
        return NFAFragment(s0, s1)

    @staticmethod
    def _plus(a):
        star = RegexParser._star(a)
        return RegexParser._concat(
            NFAFragment(a.start, a.accept), star
        )

    @staticmethod
    def _optional(a):
        s0, s1 = NFAState(), NFAState()
        s0.add_transition(EPSILON, a.start)
        s0.add_transition(EPSILON, s1)
        a.accept.add_transition(EPSILON, s1)
        return NFAFragment(s0, s1)


def regex_to_nfa(pattern, alphabet=("A", "C", "G", "U")):
    with _COMPILE_LOCK:
        NFAState._counter = 0
        parser = RegexParser(pattern, alphabet)
        frag = parser.parse()
    return frag.start, {frag.accept}


def nfa_reachable_states(nfa_start):
    """All Thompson-NFA states reachable from the start (for display/export)."""
    seen = {nfa_start}
    stack = [nfa_start]
    while stack:
        s = stack.pop()
        for targets in s.transitions.values():
            for t in targets:
                if t not in seen:
                    seen.add(t)
                    stack.append(t)
    return sorted(seen, key=lambda st: st.id)


# ---------- Subset construction: NFA -> DFA ----------

def epsilon_closure(states):
    stack = list(states)
    closure = set(states)
    while stack:
        s = stack.pop()
        for nxt in s.transitions.get(EPSILON, set()):
            if nxt not in closure:
                closure.add(nxt)
                stack.append(nxt)
    return frozenset(closure)


def move(states, symbol):
    result = set()
    for s in states:
        result |= s.transitions.get(symbol, set())
    return result


def nfa_to_dfa(nfa_start, nfa_accepts, alphabet):
    start_closure = epsilon_closure({nfa_start})
    dfa_states = {start_closure}
    dfa_transitions = {}
    unmarked = [start_closure]
    dfa_accept = set()

    while unmarked:
        current = unmarked.pop()
        if current & nfa_accepts:
            dfa_accept.add(current)
        for symbol in alphabet:
            nxt = epsilon_closure(move(current, symbol))
            if not nxt:
                continue
            dfa_transitions[(current, symbol)] = nxt
            if nxt not in dfa_states:
                dfa_states.add(nxt)
                unmarked.append(nxt)

    return {
        "states": dfa_states,
        "start": start_closure,
        "accept": dfa_accept,
        "transitions": dfa_transitions,
        "alphabet": alphabet,
    }


def dfa_search(dfa, text):
    """Find all end positions where a substring of `text` matches the DFA."""
    matches = []
    n = len(text)
    for start in range(n):
        state = dfa["start"]
        for end in range(start, n):
            symbol = text[end]
            key = (state, symbol)
            if key not in dfa["transitions"]:
                break
            state = dfa["transitions"][key]
            if state in dfa["accept"]:
                matches.append((start, end + 1, text[start:end + 1]))
    return matches


def compile_motif(pattern, alphabet=("A", "C", "G", "U")):
    """Full pipeline: regex string -> NFA -> DFA, ready for searching."""
    nfa_start, nfa_accepts = regex_to_nfa(pattern, alphabet)
    dfa = nfa_to_dfa(nfa_start, nfa_accepts, list(alphabet))
    return dfa


if __name__ == "__main__":
    # Poly-A-ish signal: AAUAAA, plus a simple GC-rich motif example
    seq = "CCCGAAUAAAGGGACGCGU"
    dfa = compile_motif("AAUAAA")
    print("Motif AAUAAA matches:", dfa_search(dfa, seq))

    dfa2 = compile_motif("(A|G)C(A|G)C")
    print("Motif (A|G)C(A|G)C matches:", dfa_search(dfa2, seq))
