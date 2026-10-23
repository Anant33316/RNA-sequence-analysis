"""
Turing Machines: detecting hairpin-capable (reverse-complement palindrome)
substrings.

TOC concept: this is the classic single-tape TM construction for
recognizing palindromic languages (usually taught as {w : w = reverse(w)}
over {0,1}), adapted here to RNA COMPLEMENTARY palindromes: a sequence
that reads the same on one strand as its Watson-Crick complement does
reversed on the other -- exactly the property that lets a strand fold
back on itself into a hairpin stem.

    w is "complement-palindromic" iff  w[i] pairs_with w[n-1-i]  for all i.

Algorithm (standard TM technique -- match outer symbols, mark them
visited, move inward, repeat):
  1. Read the leftmost unmarked symbol; remember it; mark it 'X'.
  2. Scan right to the rightmost unmarked symbol.
  3. If it complements the remembered symbol, mark it 'X' too; else reject.
  4. Move back to the leftmost unmarked symbol; repeat.
  5. Accept when zero or one unmarked symbols remain.

We implement this literally as a TM: an explicit tape (list of cells),
a head position, a finite control (state), and a transition function --
not just a Python string check -- so the state/tape/transition mechanics
used elsewhere in TOC (and in your DFA work) are visible here too, one
level up the Chomsky hierarchy.
"""

BLANK = "_"
MARK = "X"
COMPLEMENT = {"A": "U", "U": "A", "G": "C", "C": "G"}
BASES = ("A", "C", "G", "U")


class TuringMachine:
    """
    Single-tape TM. The remembered base is stored in the FINITE CONTROL
    (states seek_A, seek_C, ..., check_A, ...), exactly as a real TM must --
    there is no extra Python variable acting as memory.

    Tape layout: _ w _   (blank on both sides), head starts on w[0].

      q_scan   : at the leftmost unmarked cell.
                 X -> move R;  _ -> ACCEPT (everything matched);
                 b -> write X, go to seek_b, move R
      seek_b   : run right over unmarked bases; on X or _ step back L -> check_b
      check_b  : at the RIGHTMOST unmarked cell.
                 complement(b) -> write X, move L, q_return
                 other base    -> REJECT
                 X (only the remembered centre base was left) -> ACCEPT if
                   allow_center (odd length, original behaviour) else REJECT
      q_return : run left over bases; on X step R -> q_scan

    Bug fixed vs. the first draft: seek previously ran to the very END of the
    tape (onto cells already marked X), so after the outermost pair matched
    the machine always accepted; it also crashed on 1-symbol inputs.
    """

    def __init__(self, tape_string, allow_center=True):
        self.tape = [BLANK] + list(tape_string) + [BLANK]
        self.head = 1
        self.state = "q_scan"
        self.steps = 0
        self.allow_center = allow_center
        self.trace = []

    def _delta(self, state, cell):
        """Transition function: returns (write, move, next_state)."""
        if state == "q_scan":
            if cell == BLANK:
                return cell, "N", "ACCEPT"
            if cell == MARK:
                return cell, "R", "q_scan"
            return MARK, "R", "seek_" + cell
        if state.startswith("seek_"):
            if cell in (MARK, BLANK):
                return cell, "L", "check_" + state[5:]
            return cell, "R", state
        if state.startswith("check_"):
            remembered = state[6:]
            if cell == MARK:
                return cell, "N", "ACCEPT" if self.allow_center else "REJECT"
            if COMPLEMENT.get(cell) == remembered:
                return MARK, "L", "q_return"
            return cell, "N", "REJECT"
        if state == "q_return":
            if cell == MARK:
                return cell, "R", "q_scan"
            return cell, "L", "q_return"
        raise RuntimeError(f"no transition for state {state}")

    def step(self):
        cell = self.tape[self.head]
        if cell not in BASES and cell not in (BLANK, MARK):
            raise ValueError(f"symbol {cell!r} is not in the tape alphabet")
        write, move, nxt = self._delta(self.state, cell)
        self.trace.append({"step": self.steps, "state": self.state, "head": self.head,
                           "read": cell, "write": write, "move": move, "next_state": nxt,
                           "tape": "".join(self.tape)})
        self.tape[self.head] = write
        self.head += {"L": -1, "R": 1, "N": 0}[move]
        self.state = nxt
        self.steps += 1
        return self.state in ("ACCEPT", "REJECT")

    def run(self, max_steps=10000):
        while self.steps < max_steps:
            if self.step():
                return self.state == "ACCEPT"
        return False  # did not halt within bound


def is_hairpin_capable(rna_sequence, allow_center=True):
    """Runs the TM on a single sequence; True iff it's a complement-palindrome
    (w[i] is the Watson-Crick complement of w[n-1-i] for every i < n/2)."""
    tm = TuringMachine(rna_sequence.upper().replace("T", "U"), allow_center=allow_center)
    return tm.run()


def find_hairpin_stems(rna_sequence, min_len=4, max_len=None, allow_center=True):
    """
    Scans all substrings of the given length range and reports which
    ones the TM accepts as hairpin-capable stems -- a brute-force outer
    loop around the core TM decision procedure.
    """
    seq = rna_sequence.upper().replace("T", "U")
    n = len(seq)
    max_len = max_len or n
    hits = []
    for length in range(min_len, max_len + 1):
        for i in range(0, n - length + 1):
            sub = seq[i:i + length]
            if is_hairpin_capable(sub, allow_center):
                hits.append((i, i + length, sub))
    return hits


if __name__ == "__main__":
    # GCGC reversed-complemented: complement(GCGC) reversed = GCGC -> should accept
    for test in ["GCGC", "AUAU", "AUCG", "GGGCCC"]:
        tm = TuringMachine(test)
        accepted = tm.run()
        print(f"'{test}' hairpin-capable: {accepted}  (steps: {tm.steps})")
    # regression cases for the fixed bug: only the OUTER pair matches here
    for test in ["CCCG", "UAAA", "AUCU"]:
        assert not is_hairpin_capable(test), test

    print()
    seq = "CCCGCGCAAA"
    print(f"Scanning '{seq}' for hairpin stems (len>=4):")
    for start, end, sub in find_hairpin_stems(seq, min_len=4):
        print(f"  [{start}:{end}] {sub}")
