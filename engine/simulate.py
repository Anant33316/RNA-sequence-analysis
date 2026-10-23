"""
Step-by-step execution of DFAs and NFAs.

The trace comes from DFA.run_trace / NFA.run_trace in the original
modules; this file only converts state objects to labels and attaches a
deterministic explanation to each step (no guessing, no AI).
"""

from __future__ import annotations

from .automaton_io import parse_automaton, to_spec, tokenize, transition_table, state_label, labels
from .errors import EngineError


def _fmt_set(items) -> str:
    items = list(items)
    return "{" + ", ".join(items) + "}" if items else "∅"


def _fmt_word(symbols) -> str:
    if not symbols:
        return "ε (the empty string)"
    if all(len(s) == 1 for s in symbols):
        return "".join(symbols)
    return " ".join(symbols)


def run_dfa(dfa, symbols: list[str]) -> dict:
    raw = dfa.run_trace(symbols)
    steps = []
    for st in raw["steps"]:
        cur, sym = state_label(st["state"]), st["symbol"]
        if st["exists"]:
            nxt = state_label(st["next"])
            text = (f"Position {st['index']}: in state {cur}, read '{sym}'. "
                    f"The transition δ({cur}, {sym}) = {nxt} exists, so move to {nxt}.")
        else:
            nxt = None
            text = (f"Position {st['index']}: in state {cur}, read '{sym}'. "
                    f"δ({cur}, {sym}) is NOT defined (partial DFA), so the run halts here and the input "
                    f"is rejected. Formally this is a move to an implicit dead state.")
        steps.append({"index": st["index"], "state": cur, "symbol": sym, "next": nxt,
                      "exists": st["exists"], "active": [cur], "next_active": [nxt] if nxt else [],
                      "explanation": text})

    accept_labels = labels(dfa.accept)
    word = _fmt_word(symbols)
    if raw["halted_at"] is not None:
        verdict = (f"REJECTED: the DFA has no transition for symbol '{symbols[raw['halted_at']]}' at position "
                   f"{raw['halted_at']}, so it cannot finish reading {word}.")
        final = []
    else:
        final_state = state_label(raw["final_state"])
        final = [final_state]
        if not symbols:
            lead = f"The input is empty, so the DFA stays in its start state {final_state}. "
        else:
            lead = f"After reading all {len(symbols)} symbols the DFA is in state {final_state}. "
        if raw["accepted"]:
            verdict = lead + f"{final_state} is an accepting state, so the input is ACCEPTED."
        else:
            verdict = lead + (f"{final_state} is not accepting (accepting states: {_fmt_set(accept_labels)}), "
                              f"so the input is REJECTED.")
    return {"kind": "DFA", "input": symbols, "accepted": raw["accepted"], "steps": steps,
            "initial_active": [state_label(dfa.start)], "initial_explanation":
                f"Start in the start state {state_label(dfa.start)}.",
            "final_active": final, "halted_at": raw["halted_at"], "verdict": verdict}


def run_nfa(nfa, symbols: list[str]) -> dict:
    raw = nfa.run_trace(symbols)
    init = raw["initial"]
    init_set = [state_label(s) for s in init["set"]]
    start = state_label(nfa.start)
    if init["epsilon_edges"]:
        edges = ", ".join(f"{state_label(a)} →ε {state_label(b)}" for a, b in init["epsilon_edges"])
        init_text = (f"Start in {start} and take its ε-closure by following ε-transitions "
                     f"({edges}). Active set: {_fmt_set(init_set)}.")
    else:
        init_text = f"Start in {start}. It has no ε-transitions, so the active set is {_fmt_set(init_set)}."

    steps = []
    for st in raw["steps"]:
        active = [state_label(s) for s in st["active"]]
        moves = [{"from": state_label(m["from"]), "to": [state_label(t) for t in m["to"]]} for m in st["moves"]]
        after = [state_label(s) for s in st["after_move"]]
        nxt = [state_label(s) for s in st["next"]]
        eps = [{"from": state_label(a), "to": state_label(b)} for a, b in st["epsilon_edges"]]
        parts = [f"Position {st['index']}: read '{st['symbol']}' from active set {_fmt_set(active)}."]
        for m in moves:
            if m["to"]:
                parts.append(f"δ({m['from']}, {st['symbol']}) = {_fmt_set(m['to'])}.")
            else:
                parts.append(f"{m['from']} has no '{st['symbol']}'-transition, so that branch dies.")
        parts.append(f"Union of the moves: {_fmt_set(after)}.")
        if eps:
            parts.append("ε-closure adds " + ", ".join(f"{e['from']} →ε {e['to']}" for e in eps) + ".")
        parts.append(f"New active set: {_fmt_set(nxt)}." if nxt else
                     "New active set is empty: every branch has died, so the NFA rejects.")
        steps.append({"index": st["index"], "symbol": st["symbol"], "active": active, "moves": moves,
                      "after_move": after, "epsilon_edges": eps, "next_active": nxt,
                      "explanation": " ".join(parts)})

    final = [state_label(s) for s in raw["final_set"]]
    acc_in = [state_label(s) for s in raw["accepting_states_in_final_set"]]
    if raw["died_at"] is not None:
        verdict = (f"REJECTED: the active set became empty after position {raw['died_at']}, "
                   f"so no computation path can read the whole input.")
    elif raw["accepted"]:
        verdict = (f"ACCEPTED: the final active set {_fmt_set(final)} contains the accepting state(s) "
                   f"{_fmt_set(acc_in)}. An NFA accepts if AT LEAST ONE computation path ends in an "
                   f"accepting state.")
    else:
        verdict = (f"REJECTED: the final active set {_fmt_set(final)} contains no accepting state "
                   f"(accepting states: {_fmt_set(labels(nfa.accept))}). Every computation path ends in a "
                   f"non-accepting state.")
    return {"kind": "NFA", "input": symbols, "accepted": raw["accepted"], "steps": steps,
            "initial_active": init_set, "initial_epsilon_edges":
                [{"from": state_label(a), "to": state_label(b)} for a, b in init["epsilon_edges"]],
            "initial_explanation": init_text, "final_active": final, "halted_at": raw["died_at"],
            "verdict": verdict}


def run_machine(machine, kind: str, symbols: list[str]) -> dict:
    return run_dfa(machine, symbols) if kind == "DFA" else run_nfa(machine, symbols)


def run_spec(spec: dict, input_value) -> dict:
    machine, kind, meta = parse_automaton(spec)
    symbols = tokenize(input_value, machine.alphabet)
    result = run_machine(machine, kind, symbols)
    norm = to_spec(machine, kind, meta)
    result["automaton"] = norm
    result["table"] = transition_table(norm)
    return result


def describe_spec(spec: dict) -> dict:
    """Validation + structural facts used by the playground's info panel."""
    machine, kind, meta = parse_automaton(spec)
    norm = to_spec(machine, kind, meta)
    table = transition_table(norm)
    if kind == "DFA":
        reachable = labels(machine.reachable_states())
    else:
        reachable = labels(_nfa_reachable(machine))
    unreachable = [s for s in norm["states"] if s not in reachable]
    eps_count = sum(1 for t in norm["transitions"] if t["symbol"] == "ε")
    nondeterministic = []
    if kind == "NFA":
        for (s, a), targets in machine.transitions.items():
            if len(targets) > 1 and a != "eps":
                nondeterministic.append({"state": state_label(s), "symbol": a, "targets": labels(targets)})
    facts = {
        "kind": kind, "state_count": len(norm["states"]), "transition_count": len(norm["transitions"]),
        "alphabet_size": len(norm["alphabet"]), "missing_transitions": table["missing_transitions"],
        "complete": table["missing_transitions"] == 0 and kind == "DFA",
        "unreachable_states": unreachable, "epsilon_transitions": eps_count,
        "nondeterministic_choices": nondeterministic,
        "accepts_empty_string": run_machine(machine, kind, [])["accepted"],
    }
    notes = []
    if kind == "DFA" and facts["missing_transitions"]:
        notes.append(f"This DFA is partial: {facts['missing_transitions']} (state, symbol) pairs have no "
                     f"transition. Reading such a symbol rejects (implicit dead state).")
    if unreachable:
        notes.append(f"Unreachable from the start state: {', '.join(unreachable)}. They never affect the language.")
    if eps_count:
        notes.append(f"{eps_count} ε-transition(s): the machine can change state without reading input.")
    if nondeterministic:
        notes.append(f"{len(nondeterministic)} (state, symbol) pair(s) have more than one target (nondeterminism).")
    facts["notes"] = notes
    return {"automaton": norm, "table": table, "facts": facts}


def _nfa_reachable(nfa) -> set:
    seen = {nfa.start}
    stack = [nfa.start]
    while stack:
        s = stack.pop()
        for (src, _a), targets in nfa.transitions.items():
            if src == s:
                for t in targets:
                    if t not in seen:
                        seen.add(t)
                        stack.append(t)
    return seen


def ensure_kind(kind: str, expected: str, what: str):
    if kind != expected:
        raise EngineError(f"{what} requires a {expected}, but a {kind} was given", "automaton.type")
