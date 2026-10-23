"""
Module 2: Finite Automata with Output — Moore and Mealy Machines
=====================================================================
MEALY MACHINE (output attached to TRANSITIONS, depends on state + input):
    "Complementary strand transducer" -- for every input base, outputs
    the Watson-Crick complementary base (A<->U, G<->C). This is a
    genuine single-state Mealy machine: output = f(current_state, input).
    We also build a second, richer Mealy machine that additionally
    outputs a codon-boundary marker using 3 states (phase 0/1/2).

MOORE MACHINE (output attached to STATES, depends only on current state):
    "Purine/Pyrimidine (RY) encoder" -- classifies each base as R
    (purine: A, G) or Y (pyrimidine: C, U). Since RY-encoding is a real
    concept used in bioinformatics (e.g. RY-coding for phylogenetics),
    each state IS the classification, and output is read off the state,
    not the transition.
"""

COMPLEMENT = {"A": "U", "U": "A", "G": "C", "C": "G"}
PURINE = {"A", "G"}


class MealyMachine:
    def __init__(self, states, alphabet, transition, output_fn, start, name="Mealy"):
        self.states = states
        self.alphabet = alphabet
        self.transition = transition   # (state, input) -> next_state
        self.output_fn = output_fn     # (state, input) -> output symbol
        self.start = start
        self.name = name

    def run(self, input_string):
        state = self.start
        outputs = []
        trace = []
        for ch in input_string:
            out = self.output_fn(state, ch)
            nxt = self.transition(state, ch)
            trace.append((state, ch, out, nxt))
            outputs.append(out)
            state = nxt
        return "".join(outputs), trace


class MooreMachine:
    def __init__(self, states, alphabet, transition, state_output, start, name="Moore"):
        self.states = states
        self.alphabet = alphabet
        self.transition = transition   # (state, input) -> next_state
        self.state_output = state_output  # state -> output symbol
        self.start = start
        self.name = name

    def run(self, input_string):
        state = self.start
        outputs = [self.state_output[state]]  # Moore machines emit output on entry, including start state
        trace = [(None, None, state, self.state_output[state])]
        for ch in input_string:
            nxt = self.transition(state, ch)
            out = self.state_output[nxt]
            trace.append((state, ch, nxt, out))
            outputs.append(out)
            state = nxt
        return "".join(outputs), trace


# ---------------- Mealy #1: complement transducer (1 state) ----------------

def build_complement_mealy():
    states = {"S"}
    alphabet = {"A", "C", "G", "U"}

    def transition(state, ch):
        return "S"  # single state, always loops

    def output_fn(state, ch):
        return COMPLEMENT[ch]

    return MealyMachine(states, alphabet, transition, output_fn, "S", "complement transducer")


# ---------------- Mealy #2: codon-boundary marker (3 states) ----------------

def build_codon_boundary_mealy():
    """States track reading-frame phase (0,1,2). Output = '1' if this
    symbol starts a new codon (phase 0 -> reading), else '0'."""
    states = {0, 1, 2}
    alphabet = {"A", "C", "G", "U"}

    def transition(state, ch):
        return (state + 1) % 3

    def output_fn(state, ch):
        return "1" if state == 0 else "0"

    return MealyMachine(states, alphabet, transition, output_fn, 0, "codon-boundary marker")


# ---------------- Moore: RY (purine/pyrimidine) encoder (2 states) ----------------

def build_ry_moore():
    states = {"R", "Y"}  # state itself doubles as the classification
    alphabet = {"A", "C", "G", "U"}
    state_output = {"R": "R", "Y": "Y"}

    def transition(state, ch):
        return "R" if ch in PURINE else "Y"

    return MooreMachine(states, alphabet, transition, state_output, "Y", "RY (purine/pyrimidine) encoder")


if __name__ == "__main__":
    seq = "AUGGCUACGUAA"

    mealy_c = build_complement_mealy()
    comp_out, _ = mealy_c.run(seq)
    print(f"Input      : {seq}")
    print(f"Complement : {comp_out}   (Mealy machine, 1 state, output = f(input))")

    mealy_b = build_codon_boundary_mealy()
    boundary_out, _ = mealy_b.run(seq)
    print(f"\nInput      : {seq}")
    print(f"Boundaries : {boundary_out}   (Mealy machine, 3 states = reading-frame phase)")

    moore = build_ry_moore()
    ry_out, trace = moore.run(seq)
    print(f"\nInput          : {seq}")
    print(f"RY-encoding    : {ry_out[1:]}   (Moore machine, output = state itself)")
    print(f"(RY string is 1 symbol longer than input: Moore machines also emit")
    print(f" an output for the START state before consuming any input.)")
