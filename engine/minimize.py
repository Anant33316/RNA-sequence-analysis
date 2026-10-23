"""DFA minimization with explanation (algorithm: module1_dfa.minimization.minimize)."""

from __future__ import annotations

from module1_dfa.minimization import minimize

from .automaton_io import parse_automaton, to_spec, dfa_to_spec, transition_table, state_label, labels
from .simulate import ensure_kind


def _blocks(partition) -> list[list[str]]:
    return [labels(b) for b in partition]


def _fmt_blocks(blocks) -> str:
    return "  ".join("{" + ", ".join(b) + "}" for b in blocks)


def _word(witness) -> str:
    if not witness:
        return "ε"
    if all(len(str(a)) == 1 for a in witness):
        return "".join(str(a) for a in witness)
    return " ".join(str(a) for a in witness)


def minimize_spec(spec: dict) -> dict:
    machine, kind, meta = parse_automaton(spec)
    ensure_kind(kind, "DFA", "Minimization")
    trace: dict = {}
    minimized, _groups = minimize(machine, trace=trace)

    pre = []
    if trace["unreachable_removed"]:
        pre.append(f"Step 1 — remove unreachable states: {', '.join(labels(trace['unreachable_removed']))} cannot be "
                   f"reached from the start state, so they are deleted (table-filling alone would keep them).")
    else:
        pre.append("Step 1 — every state is reachable from the start state; nothing to remove.")
    if trace["trap_added"]:
        pre.append(f"Step 2 — the DFA is partial, so a trap state {', '.join(labels(trace['trap_added']))} is added "
                   f"to make every transition defined (missing moves go there).")
    else:
        pre.append("Step 2 — the DFA is already complete (every state has a move on every symbol).")

    rounds = []
    for r in trace["rounds"]:
        marked = []
        for m in r["newly_marked"]:
            p, q = (state_label(x) for x in m["pair"])
            if m["round"] == 0:
                why = f"exactly one of {p}, {q} is accepting, so the empty string ε distinguishes them"
            else:
                a = m["symbol"]
                vp, vq = (state_label(x) for x in m["via"])
                why = (f"on '{a}' they go to ({vp}, {vq}), which was already marked, so the string "
                       f"'{_word(m['witness'])}' distinguishes them")
            marked.append({"pair": [p, q], "symbol": m["symbol"],
                           "via": [state_label(x) for x in m["via"]] if m["via"] else None,
                           "witness": _word(m["witness"]), "reason": why})
        blocks = _blocks(r["partition"])
        if r["round"] == 0:
            text = (f"Round 0 — initial partition: accepting vs non-accepting states → {_fmt_blocks(blocks)}. "
                    f"{len(marked)} pair(s) marked distinguishable.")
        else:
            text = (f"Round {r['round']} — a pair is marked if some symbol sends it to a pair marked in an earlier "
                    f"round. {len(marked)} new pair(s) marked. Partition is now {_fmt_blocks(blocks)}.")
        rounds.append({"round": r["round"], "marked": marked, "partition": blocks, "explanation": text})

    classes = _blocks(trace["classes"])
    merged = [c for c in classes if len(c) > 1]
    if merged:
        merge_text = ("No further pair can be marked, so the unmarked pairs are equivalent. Merged classes: "
                      + "; ".join("{" + ", ".join(c) + "} → " + c[0] for c in merged) + ".")
    else:
        merge_text = "No pair of states is equivalent: every state is already distinguishable, so the DFA was minimal."

    table = []
    for cell in trace["table"]:
        table.append({"pair": [state_label(x) for x in cell["pair"]], "distinguishable": cell["distinguishable"],
                      "round": cell["round"], "symbol": cell["symbol"],
                      "witness": _word(cell["witness"]) if cell["distinguishable"] else None})

    before = to_spec(machine, kind, meta)
    rep = {state_label(k): state_label(v) for k, v in trace["representative"].items()}
    desc = {}
    for c in classes:
        desc[c[0]] = "merged: {" + ", ".join(c) + "}" if len(c) > 1 else c[0]
    after = dfa_to_spec(minimized, f"minimized({meta['name']})", descriptions=desc,
                        extra={"classes": {c[0]: c for c in classes}})
    summary = (f"{trace['original_state_count']} state(s) → {trace['minimized_state_count']} state(s)"
               + (f" (unreachable removed: {len(trace['unreachable_removed'])}"
                  + (f", trap added: {len(trace['trap_added'])}" if trace["trap_added"] else "") + ")"
                  if trace["unreachable_removed"] or trace["trap_added"] else "")
               + ". The minimized DFA recognises the same language; by the Myhill–Nerode theorem it is the unique "
                 "smallest complete DFA for it (up to renaming states).")
    return {"before": before, "after": after, "before_table": transition_table(before),
            "after_table": transition_table(after), "preprocessing": pre, "rounds": rounds,
            "pair_table": table, "table_states": [state_label(s) for s in trace["states"]],
            "classes": classes, "representative": rep, "merge_explanation": merge_text, "summary": summary,
            "counts": {"original": trace["original_state_count"], "minimized": trace["minimized_state_count"],
                       "unreachable_removed": labels(trace["unreachable_removed"]),
                       "trap_added": labels(trace["trap_added"])}}
