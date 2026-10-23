"""
NFA conversions with explanations:

  * epsilon elimination      -> module2_nfa.epsilon_elimination.eliminate_epsilon
  * subset construction      -> module2_nfa.subset_construction_equivalence.subset_construction

The traces are recorded by those original functions; this module labels
the subset states (D0, D1, ...), serialises the result, and writes the
explanation text.
"""

from __future__ import annotations

from module1_dfa.dfa_basics import DFA
from module2_nfa.epsilon_elimination import eliminate_epsilon
from module2_nfa.subset_construction_equivalence import subset_construction

from .automaton_io import parse_automaton, to_spec, nfa_to_spec, dfa_to_spec, transition_table, labels, state_label
from .simulate import ensure_kind


def _fmt_set(items) -> str:
    items = list(items)
    return "{" + ", ".join(items) + "}" if items else "∅"


def as_nfa(machine, kind):
    """A DFA is also an NFA: wrap it so NFA algorithms can run on it."""
    if kind == "NFA":
        return machine
    from module2_nfa.nfa_epsilon import NFA
    return NFA(machine.states, machine.alphabet, {k: {v} for k, v in machine.transitions.items()},
               machine.start, machine.accept, machine.name)


# ----------------------------------------------------------------- epsilon elimination

def epsilon_eliminate_spec(spec: dict) -> dict:
    machine, kind, meta = parse_automaton(spec)
    ensure_kind(kind, "NFA", "ε-elimination")
    trace: list = []
    result = eliminate_epsilon(machine, trace=trace)
    steps = []
    for rec in trace:
        q = state_label(rec["state"])
        closure = labels(rec["closure"])
        lines = [f"ε-closure({q}) = {_fmt_set(closure)}."]
        if rec["becomes_accepting"]:
            src = labels(rec["because_of"])
            if src == [q]:
                lines.append(f"{q} was already accepting.")
            else:
                lines.append(f"{q} becomes ACCEPTING because its ε-closure contains {_fmt_set(src)}.")
        rows = []
        for r in rec["transitions"]:
            via = "; ".join(f"from {state_label(s['via'])} on {r['symbol']} → {_fmt_set(labels(s['to']))}"
                            for s in r["sources"])
            res = labels(r["result"])
            rows.append({"symbol": r["symbol"], "via": via, "move": labels(r["move"]), "result": res})
            lines.append(f"δ'({q}, {r['symbol']}) = ε-closure(move) = {_fmt_set(res)}  [{via}].")
        if not rec["transitions"]:
            lines.append(f"No state in the closure has a symbol transition, so {q} gets no outgoing transitions.")
        steps.append({"state": q, "closure": closure, "becomes_accepting": rec["becomes_accepting"],
                      "rows": rows, "explanation": " ".join(lines)})
    before = to_spec(machine, kind, meta)
    after = nfa_to_spec(result, f"{meta['name']} [ε-eliminated]", descriptions=meta.get("descriptions"))
    eps_before = sum(1 for t in before["transitions"] if t["symbol"] == "ε")
    summary = (f"Removed {eps_before} ε-transition(s). The state set is unchanged ({len(after['states'])} states); "
               f"each state q now has, for every symbol a, the transitions of ALL states in ε-closure(q) on a "
               f"(followed by ε-closure), and q accepts iff its ε-closure contains an accepting state. "
               f"The language is unchanged: an ε-free path exists exactly when an ε-path existed.")
    return {"before": before, "after": after, "before_table": transition_table(before),
            "after_table": transition_table(after), "steps": steps, "summary": summary,
            "counts": {"states_before": len(before["states"]), "states_after": len(after["states"]),
                       "transitions_before": len(before["transitions"]),
                       "transitions_after": len(after["transitions"]), "epsilon_removed": eps_before}}


# ----------------------------------------------------------------- subset construction

def determinize(machine, kind, include_dead_state=True):
    """Run the original subset construction and convert its dict result into an
    original DFA object with states named D0, D1, ... (BFS order). Returns
    (dfa, names, trace) where names maps each frozenset to its label."""
    nfa = as_nfa(machine, kind)
    trace: dict = {}
    raw = subset_construction(nfa, include_dead_state=include_dead_state, trace=trace)
    names = {}
    for i, subset in enumerate(trace["order"]):
        names[subset] = "∅" if not subset else f"D{i}"
    dfa = DFA(raw["states"], raw["alphabet"], raw["transitions"], raw["start"], raw["accept"],
              f"DFA({machine.name})")
    return dfa, names, trace


def subset_spec(spec: dict, include_dead_state: bool = True) -> dict:
    machine, kind, meta = parse_automaton(spec)
    dfa, names, trace = determinize(machine, kind, include_dead_state)
    nfa_spec = to_spec(machine, kind, meta)

    def nm(s):
        return names[s]

    start = trace["start_closure"]
    start_lbl = labels(start)
    if trace["start_epsilon_edges"]:
        e = ", ".join(f"{state_label(a)} →ε {state_label(b)}" for a, b in trace["start_epsilon_edges"])
        start_text = (f"The DFA start state is ε-closure({{{state_label(machine.start)}}}) = {_fmt_set(start_lbl)} "
                      f"(following {e}). Call it {nm(start)}.")
    else:
        start_text = (f"The DFA start state is ε-closure({{{state_label(machine.start)}}}) = {_fmt_set(start_lbl)}; "
                      f"no ε-moves apply. Call it {nm(start)}.")

    steps = []
    for rec in trace["processed"]:
        sub = rec["subset"]
        rows = []
        lines = [f"Process {nm(sub)} = {_fmt_set(labels(sub))}."]
        if rec["accepting"]:
            lines.append(f"It is ACCEPTING because it contains NFA accepting state(s) "
                         f"{_fmt_set(labels(rec['accepting_because']))}.")
        for r in rec["rows"]:
            res = r["result"]
            target = names.get(res, "∅")
            status = "new" if r["new"] else ("dead (omitted)" if not res and not include_dead_state else "existing")
            rows.append({"symbol": r["symbol"], "move": labels(r["move"]),
                         "epsilon_edges": [{"from": state_label(a), "to": state_label(b)} for a, b in r["epsilon_edges"]],
                         "result": labels(res), "target": target if (res or include_dead_state) else None,
                         "status": status})
            if not res:
                lines.append(f"On {r['symbol']}: no NFA state moves, the result is ∅"
                             + (" (the dead state)." if include_dead_state else " — transition omitted (partial DFA)."))
            else:
                eps_txt = (" then ε-closure adds " + ", ".join(f"{state_label(a)}→{state_label(b)}"
                                                              for a, b in r["epsilon_edges"])) if r["epsilon_edges"] else ""
                lines.append(f"On {r['symbol']}: move = {_fmt_set(labels(r['move']))}{eps_txt} → "
                             f"{_fmt_set(labels(res))} = {target}" + (" (NEW subset, queued)." if r["new"] else "."))
        steps.append({"state": nm(sub), "subset": labels(sub), "accepting": rec["accepting"],
                      "accepting_because": labels(rec["accepting_because"]), "rows": rows,
                      "explanation": " ".join(lines)})

    rename = {s: names[s] for s in dfa.states}
    subsets = {names[s]: labels(s) for s in dfa.states}
    descriptions = {names[s]: _fmt_set(labels(s)) for s in dfa.states}
    dfa_spec = dfa_to_spec(dfa, f"DFA from {meta['name']}", rename=rename, descriptions=descriptions,
                           extra={"subsets": subsets})
    n = len(nfa_spec["states"])
    possible = 2 ** n if n <= 30 else None
    summary = (f"Subset construction produced {len(dfa_spec['states'])} DFA state(s) from an NFA with {n} state(s). "
               + (f"Of the 2^{n} = {possible} possible subsets, only the {len(dfa_spec['states'])} reachable from "
                  f"the start closure were generated — unreachable subsets are never created. " if possible else "")
               + "Each DFA state is the set of NFA states the NFA could be in after the same input, so the DFA "
                 "accepts a string exactly when some NFA path accepts it.")
    return {"nfa": nfa_spec, "dfa": dfa_spec, "nfa_table": transition_table(nfa_spec),
            "dfa_table": transition_table(dfa_spec), "start_explanation": start_text, "steps": steps,
            "subsets": subsets, "summary": summary,
            "counts": {"nfa_states": n, "dfa_states": len(dfa_spec["states"]),
                       "possible_subsets": possible, "include_dead_state": include_dead_state}}
