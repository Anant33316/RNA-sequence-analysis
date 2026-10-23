"""
Verification lab.

* EXHAUSTIVE equivalence: both automata are converted to complete DFAs
  over the union alphabet; a breadth-first search explores the reachable
  pairs of the product (= the symmetric-difference automaton). The
  languages are equal iff no reachable pair has exactly one accepting
  component. Because BFS is used, the counterexample returned is a
  SHORTEST distinguishing string. This is a proof, not a sample.

* BOUNDED testing: every string up to a length bound (plus seeded random
  longer strings) is run through both machines. Agreement here is
  evidence, not proof — the UI labels it that way.
"""

from __future__ import annotations

import itertools
import random

from module1_dfa.dfa_basics import DFA

from .automaton_io import parse_automaton, to_spec, transition_table, tokenize, state_label
from .conversions import determinize
from .simulate import run_machine
from .errors import EngineError

MAX_BOUNDED_STRINGS = 60000


def _complete_dfa(machine, kind, meta):
    """Return an original DFA object (states relabelled to strings)."""
    if kind == "DFA":
        return machine, False
    dfa, names, _ = determinize(machine, kind, include_dead_state=True)
    relabelled = DFA({names[s] for s in dfa.states}, dfa.alphabet,
                     {(names[s], a): names[t] for (s, a), t in dfa.transitions.items()},
                     names[dfa.start], {names[s] for s in dfa.accept}, f"DFA({meta['name']})")
    return relabelled, True


def _word(symbols) -> str:
    if not symbols:
        return "ε"
    return "".join(symbols) if all(len(s) == 1 for s in symbols) else " ".join(symbols)


def check_equivalence(a_spec: dict, b_spec: dict) -> dict:
    ma, ka, meta_a = parse_automaton(a_spec, "a")
    mb, kb, meta_b = parse_automaton(b_spec, "b")
    da, a_det = _complete_dfa(ma, ka, meta_a)
    db, b_det = _complete_dfa(mb, kb, meta_b)
    alphabet = sorted(set(da.alphabet) | set(db.alphabet), key=str)
    A, B = da.total(alphabet), db.total(alphabet)

    start = (A.start, B.start)
    parent = {start: None}
    queue = [start]
    head = 0
    witness_pair = None
    while head < len(queue):
        pair = queue[head]
        head += 1
        p, q = pair
        if (p in A.accept) != (q in B.accept):
            witness_pair = pair
            break
        for x in alphabet:
            nxt = (A.transitions[(p, x)], B.transitions[(q, x)])
            if nxt not in parent:
                parent[nxt] = (pair, x)
                queue.append(nxt)

    steps = []
    if a_det:
        steps.append(f"A is an NFA: converted to a DFA with {len(da.states)} state(s) by subset construction.")
    if b_det:
        steps.append(f"B is an NFA: converted to a DFA with {len(db.states)} state(s) by subset construction.")
    if set(da.alphabet) != set(db.alphabet):
        steps.append("The alphabets differ; both DFAs were completed over the union alphabet "
                     "{" + ", ".join(alphabet) + "} (unknown symbols lead to a trap state).")
    steps.append("Build the product of the two complete DFAs on the fly, starting from "
                 f"({state_label(A.start)}, {state_label(B.start)}), exploring pairs breadth-first.")
    steps.append("A pair (p, q) is a WITNESS if exactly one of p, q is accepting — the string leading there is in one "
                 "language but not the other (the symmetric difference).")

    explored = head
    result = {"a": to_spec(ma, ka, meta_a), "b": to_spec(mb, kb, meta_b),
              "a_dfa_states": len(A.states), "b_dfa_states": len(B.states),
              "explored_pairs": explored, "method": "exhaustive product-construction search (BFS)"}
    if witness_pair is None:
        steps.append(f"All {explored} reachable pair(s) were explored and none is a witness, so the symmetric "
                     f"difference is EMPTY: L(A) = L(B). This is a complete proof, not a sample.")
        result.update({"equivalent": True, "counterexample": None, "steps": steps})
        return result

    path = []
    node = witness_pair
    pairs = [witness_pair]
    while parent[node] is not None:
        prev, x = parent[node]
        path.append(x)
        node = prev
        pairs.append(prev)
    path.reverse()
    pairs.reverse()
    a_acc = witness_pair[0] in A.accept
    word = _word(path)
    steps.append(f"Witness found after exploring {explored} pair(s): "
                 f"({state_label(witness_pair[0])}, {state_label(witness_pair[1])}) where A is "
                 f"{'accepting' if a_acc else 'not accepting'} and B is {'not accepting' if a_acc else 'accepting'}.")
    steps.append(f"Following parent links back to the start gives the shortest counterexample '{word}': "
                 f"{'A accepts it and B rejects it' if a_acc else 'B accepts it and A rejects it'}.")
    result.update({
        "equivalent": False, "counterexample": path, "counterexample_text": word,
        "accepted_by": "A" if a_acc else "B",
        "path": [[state_label(p), state_label(q)] for p, q in pairs], "steps": steps,
        "verification": {"a": run_machine(ma, ka, path)["accepted"], "b": run_machine(mb, kb, path)["accepted"]},
    })
    return result


def bounded_test(a_spec: dict, b_spec: dict, max_length: int = 6, random_count: int = 200,
                 random_max_length: int = 40, seed: int = 7) -> dict:
    if not (0 <= max_length <= 12):
        raise EngineError("max_length must be between 0 and 12", "max_length")
    if not (0 <= random_count <= 5000):
        raise EngineError("random_count must be between 0 and 5000", "random_count")
    ma, ka, meta_a = parse_automaton(a_spec, "a")
    mb, kb, meta_b = parse_automaton(b_spec, "b")
    alphabet = sorted(set(map(str, ma.alphabet)) | set(map(str, mb.alphabet)))
    total = sum(len(alphabet) ** k for k in range(max_length + 1))
    if total > MAX_BOUNDED_STRINGS:
        raise EngineError(f"{total} strings up to length {max_length}: reduce the bound "
                          f"(limit {MAX_BOUNDED_STRINGS})", "max_length", code="too_large")

    def accepts(machine, word):
        if any(x not in machine.alphabet for x in word):
            return False  # a symbol outside this machine's alphabet: rejected
        return machine.accepts(word)  # original DFA.accepts / NFA.accepts

    mismatches, agree_acc, agree_rej, n, total_mis = [], 0, 0, 0, 0
    for k in range(max_length + 1):
        for word in itertools.product(alphabet, repeat=k):
            n += 1
            ra, rb = accepts(ma, list(word)), accepts(mb, list(word))
            if ra != rb:
                total_mis += 1
                if len(mismatches) < 25:
                    mismatches.append({"input": _word(list(word)), "a": ra, "b": rb})
            elif ra:
                agree_acc += 1
            else:
                agree_rej += 1
    rng = random.Random(seed)
    for _ in range(random_count):
        word = [rng.choice(alphabet) for _ in range(rng.randint(max_length + 1, max(max_length + 1, random_max_length)))]
        ra, rb = accepts(ma, word), accepts(mb, word)
        if ra != rb:
            total_mis += 1
            if len(mismatches) < 25:
                mismatches.append({"input": _word(word), "a": ra, "b": rb})
    tested = n + random_count
    found = total_mis > 0
    return {
        "method": "bounded testing (evidence, NOT a proof)",
        "exhaustive_up_to_length": max_length, "exhaustive_strings": n,
        "random_strings": random_count, "random_seed": seed, "tested": tested,
        "agree_accept": agree_acc, "agree_reject": agree_rej,
        "mismatch_count": total_mis,
        "mismatches": mismatches, "disagreement_found": found,
        "explanation": (f"Ran {n} strings (every string of length 0..{max_length}) plus {random_count} seeded random "
                        f"strings (seed {seed}). "
                        + ("The automata DISAGREE on the strings listed — they are definitely not equivalent."
                           if found else
                           "No disagreement was found. This is consistent with equivalence but does NOT prove it; "
                           "use the exhaustive check for a proof.")),
    }


def compare(a_spec: dict, b_spec: dict, input_value) -> dict:
    ma, ka, meta_a = parse_automaton(a_spec, "a")
    mb, kb, meta_b = parse_automaton(b_spec, "b")
    sa, sb = to_spec(ma, ka, meta_a), to_spec(mb, kb, meta_b)
    out = {"a": sa, "b": sb, "a_table": transition_table(sa), "b_table": transition_table(sb),
           "stats": {"a": {"type": ka, "states": len(sa["states"]), "transitions": len(sa["transitions"]),
                           "accepting": len(sa["accept"])},
                     "b": {"type": kb, "states": len(sb["states"]), "transitions": len(sb["transitions"]),
                           "accepting": len(sb["accept"])}}}
    if input_value is not None:
        alpha = sorted(set(map(str, ma.alphabet)) | set(map(str, mb.alphabet)))
        sym = tokenize(input_value, alpha)
        ra = run_machine(ma, ka, sym) if all(x in ma.alphabet for x in sym) else None
        rb = run_machine(mb, kb, sym) if all(x in mb.alphabet for x in sym) else None
        out["runs"] = {"a": ra, "b": rb,
                       "agree": (ra["accepted"] if ra else False) == (rb["accepted"] if rb else False)}
    return out
