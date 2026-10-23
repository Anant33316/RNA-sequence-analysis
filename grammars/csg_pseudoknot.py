"""
Context-Sensitive Grammars & Linear-Bounded Automata: RNA pseudoknots.

TOC concept: a pseudoknot occurs when base pairs CROSS instead of nest --
e.g. positions (i, j) and (k, l) pair with i < k < j < l. This is exactly
the "crossing dependency" pattern (like a^n b^n c^n or ww, the
copy language) that is PROVABLY not context-free -- no CFG/PDA can
recognize it, because a single stack cannot verify two interleaved
matchings at once (a classical pumping-lemma-for-CFLs result).

To handle this we need at least a Context-Sensitive Grammar / Linear
Bounded Automaton (LBA) -- an automaton with a tape bounded by the input
length, allowed to move both directions and overwrite symbols, giving it
enough power to check crossing constraints in place.

This module does two things:
  1. `has_pseudoknot(pairs)`: a simple crossing-detector over a proposed
     pairing (this itself is easy -- checking crossings is decidable in
     polynomial time by a plain algorithm/LBA; the hard part TOC-wise is
     that no CFG can *generate exactly* the language of valid crossing
     structures).
  2. `LBA` : a minimal linear-bounded automaton simulation that verifies
     a bracket string using two interleaved bracket types (e.g. "([)]")
     represents crossing pairs -- demonstrating in-place tape use instead
     of a stack.
"""


def has_pseudoknot(pairs):
    """
    pairs: list of (i, j) index tuples with i < j, representing proposed
    base pairs. Returns True if any two pairs cross (i < k < j < l).
    """
    for a in range(len(pairs)):
        i, j = pairs[a]
        for b in range(a + 1, len(pairs)):
            k, l = pairs[b]
            crosses = (i < k < j < l) or (k < i < l < j)
            if crosses:
                return True, (pairs[a], pairs[b])
    return False, None


BRACKET_TYPES = ("()", "[]", "{}", "<>")
OPENERS = {t[0]: t for t in BRACKET_TYPES}
CLOSERS = {t[1]: t for t in BRACKET_TYPES}


class LBA:
    """
    A Linear-Bounded-Automaton-style checker: it works ONLY on the cells
    occupied by the input (no stack, no extra memory) and overwrites
    matched brackets with '.' in place. Several bracket types may
    interleave (crossing pairs = pseudoknots), which a single PDA stack
    cannot verify in general.

    One pass of the head:
      1. sweep right to the FIRST closing bracket on the tape;
      2. sweep left from there to the NEAREST unmatched opening bracket of
         the same type (other types and '.' are skipped);
      3. overwrite both with '.', return to the left end.
    Reject if a closing bracket has no partner, or opening brackets remain
    when no closing bracket is left. Accept when the tape is all '.'.

    This is a faithful simulation of the procedure an LBA would run; it is
    presented as an "LBA-style" demonstration, not a formal LBA definition
    with an explicit transition table.
    """

    def __init__(self, tape_string):
        bad = [c for c in tape_string if c != "." and c not in OPENERS and c not in CLOSERS]
        if bad:
            raise ValueError(f"unsupported tape symbol {bad[0]!r}; use '.', (), [], {{}}, <>")
        self.tape = list(tape_string)
        self.trace = []
        self.head_moves = 0

    def accepts(self):
        while True:
            close_idx = None
            for idx, ch in enumerate(self.tape):          # step 1: sweep right
                self.head_moves += 1
                if ch in CLOSERS:
                    close_idx = idx
                    break
            if close_idx is None:
                leftover = [i for i, ch in enumerate(self.tape) if ch in OPENERS]
                verdict = not leftover
                self.trace.append({"event": "accept" if verdict else "reject",
                                   "reason": "every bracket was matched" if verdict
                                   else f"opening bracket at {leftover[0]} has no partner",
                                   "tape": "".join(self.tape)})
                return verdict
            kind = CLOSERS[self.tape[close_idx]]
            open_idx = None
            for idx in range(close_idx - 1, -1, -1):        # step 2: sweep left
                self.head_moves += 1
                if self.tape[idx] == kind[0]:
                    open_idx = idx
                    break
            if open_idx is None:
                self.trace.append({"event": "reject",
                                   "reason": f"closing '{kind[1]}' at {close_idx} has no opening partner",
                                   "tape": "".join(self.tape)})
                return False
            self.tape[open_idx] = "."                         # step 3: overwrite in place
            self.tape[close_idx] = "."
            self.trace.append({"event": "match", "type": kind, "open": open_idx, "close": close_idx,
                               "tape": "".join(self.tape)})


def parse_dot_bracket(structure):
    """Parse a dot-bracket string with up to four bracket types into a
    sorted list of (i, j) pairs. Raises ValueError on unbalanced input."""
    stacks = {t: [] for t in BRACKET_TYPES}
    pairs = []
    for idx, ch in enumerate(structure):
        if ch == ".":
            continue
        if ch in OPENERS:
            stacks[OPENERS[ch]].append(idx)
        elif ch in CLOSERS:
            st = stacks[CLOSERS[ch]]
            if not st:
                raise ValueError(f"unmatched '{ch}' at position {idx}")
            pairs.append((st.pop(), idx))
        else:
            raise ValueError(f"unsupported character {ch!r} at position {idx}")
    for t, st in stacks.items():
        if st:
            raise ValueError(f"unmatched '{t[0]}' at position {st[-1]}")
    return sorted(pairs)


def annotate_crossing_structure(rna_sequence, pairs):
    """
    Given a sequence and a set of (i, j) base-pair indices (which may
    include crossings), render a multi-bracket-type string and verify it
    with the LBA. Each pair gets the first bracket type, in the order
    () [] {} <>, that does not cross another pair of the SAME type.

    (Bug fix: the first draft gave every crossing pair '[]', so two pairs
    that cross each other AND an earlier '()' pair were drawn as if they
    were nested.)
    """
    n = len(rna_sequence)
    labels = ["."] * n
    used_types = []
    for (i, j) in sorted(pairs):
        if not (0 <= i < j < n):
            raise ValueError(f"pair {(i, j)} is outside the sequence (length {n})")
        if labels[i] != "." or labels[j] != ".":
            raise ValueError(f"position {i if labels[i] != '.' else j} is used by two pairs")
        for bracket_type in BRACKET_TYPES:
            clash = any(t == bracket_type and ((pi < i < pj < j) or (i < pi < j < pj))
                        for (pi, pj), t in used_types)
            if not clash:
                break
        else:
            raise ValueError("structure needs more than four bracket types")
        used_types.append(((i, j), bracket_type))
        labels[i] = bracket_type[0]
        labels[j] = bracket_type[1]

    tape_string = "".join(labels)
    lba = LBA(tape_string)
    return tape_string, lba.accepts()


if __name__ == "__main__":
    # Example: a nested-only structure (no pseudoknot)
    nested = [(0, 9), (1, 8), (2, 7)]
    found, culprits = has_pseudoknot(nested)
    print(f"Nested pairs {nested} -> pseudoknot: {found}")

    # Example: a crossing structure (classic H-type pseudoknot pattern)
    crossing = [(0, 5), (2, 8), (3, 9)]
    found, culprits = has_pseudoknot(crossing)
    print(f"Crossing pairs {crossing} -> pseudoknot: {found}, crossing pair: {culprits}")

    seq = "A" * 10
    tape_str, accepted = annotate_crossing_structure(seq, crossing)
    print(f"Bracket rendering: {tape_str}  | LBA accepts: {accepted}")

    # three mutually crossing pairs need three bracket types
    tape_str, accepted = annotate_crossing_structure("A" * 6, [(0, 3), (1, 4), (2, 5)])
    print(f"Three-way crossing: {tape_str}  | LBA accepts: {accepted}")
    assert tape_str == "([{)]}"
