"""
JSON <-> automaton conversion and validation.

Specification format (used by the API and the frontend):

    {
      "type": "DFA" | "NFA",
      "name": "contains AUG",
      "states": ["q0", "q1"],
      "alphabet": ["A", "C", "G", "U"],
      "start": "q0",
      "accept": ["q1"],
      "transitions": [{"from": "q0", "symbol": "A", "to": "q1"}, ...],
      "descriptions": {"q0": "nothing matched yet"}      (optional)
    }

In an NFA, the symbol "ε" (also accepted: "eps", "epsilon") denotes an
epsilon transition. Specifications are converted into the ORIGINAL DFA
(module1_dfa.dfa_basics.DFA) and NFA (module2_nfa.nfa_epsilon.NFA) classes,
so every algorithm runs on the project's own implementation.
"""

from __future__ import annotations

from module1_dfa.dfa_basics import DFA
from module2_nfa.nfa_epsilon import NFA, EPSILON

from .errors import EngineError

EPS_DISPLAY = "ε"
EPS_ALIASES = {"ε", "eps", "epsilon", "λ"}

MAX_STATES = 200
MAX_SYMBOLS = 64
MAX_TRANSITIONS = 5000
MAX_INPUT_SYMBOLS = 5000
MAX_NAME = 120


# ----------------------------------------------------------------- labels

def state_label(s) -> str:
    """Stable, human-readable label for any state object used by the
    original algorithms (strings, ints, product tuples, subset frozensets,
    Thompson-NFA state objects)."""
    if isinstance(s, str):
        return s
    if isinstance(s, (bool, int)):
        return str(s)
    if isinstance(s, tuple):
        return "(" + ", ".join(state_label(x) for x in s) + ")"
    if isinstance(s, frozenset):
        return "{" + ", ".join(sorted(state_label(x) for x in s)) + "}" if s else "∅"
    if hasattr(s, "id"):
        return f"n{s.id}"
    return str(s)


def sym_label(a) -> str:
    return EPS_DISPLAY if a == EPSILON else str(a)


def labels(items) -> list[str]:
    return sorted((state_label(x) for x in items), key=_natural_key)


def _natural_key(text: str):
    """Sort 'q2' before 'q10'."""
    import re
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", text)]


# ----------------------------------------------------------------- spec -> object

def _require_list_of_str(spec: dict, key: str, path: str) -> list[str]:
    value = spec.get(key)
    if not isinstance(value, list):
        raise EngineError(f"'{key}' must be a list", f"{path}.{key}")
    out = []
    for i, v in enumerate(value):
        if not isinstance(v, str) or not v.strip():
            raise EngineError(f"'{key}' entries must be non-empty strings", f"{path}.{key}[{i}]")
        out.append(v.strip())
    if len(set(out)) != len(out):
        dup = next(x for x in out if out.count(x) > 1)
        raise EngineError(f"duplicate entry '{dup}' in '{key}'", f"{path}.{key}")
    return out


def parse_automaton(spec: dict, path: str = "automaton"):
    """Validate a JSON spec and build the original DFA / NFA object.

    Returns (machine, kind, meta) where kind is "DFA" or "NFA" and meta keeps
    the name and optional per-state descriptions.
    """
    if not isinstance(spec, dict):
        raise EngineError("automaton must be an object", path)
    kind = str(spec.get("type", "")).upper()
    if kind not in ("DFA", "NFA"):
        raise EngineError("type must be 'DFA' or 'NFA'", f"{path}.type")
    name = str(spec.get("name") or kind)[:MAX_NAME]

    states = _require_list_of_str(spec, "states", path)
    if not states:
        raise EngineError("an automaton needs at least one state", f"{path}.states")
    if len(states) > MAX_STATES:
        raise EngineError(f"at most {MAX_STATES} states are supported", f"{path}.states")
    alphabet = _require_list_of_str(spec, "alphabet", path)
    if not alphabet:
        raise EngineError("the alphabet must contain at least one symbol", f"{path}.alphabet")
    if len(alphabet) > MAX_SYMBOLS:
        raise EngineError(f"at most {MAX_SYMBOLS} alphabet symbols are supported", f"{path}.alphabet")
    for i, a in enumerate(alphabet):
        if a in EPS_ALIASES:
            raise EngineError("ε cannot be an alphabet symbol (it denotes the empty string)",
                              f"{path}.alphabet[{i}]")
        if any(ch.isspace() or ch == "," for ch in a):
            raise EngineError(f"symbol '{a}' may not contain spaces or commas", f"{path}.alphabet[{i}]")

    start = spec.get("start")
    if start not in states:
        raise EngineError(f"start state '{start}' is not in the state list", f"{path}.start")
    accept = _require_list_of_str(spec, "accept", path)
    for i, q in enumerate(accept):
        if q not in states:
            raise EngineError(f"accepting state '{q}' is not in the state list", f"{path}.accept[{i}]")

    raw = spec.get("transitions")
    if not isinstance(raw, list):
        raise EngineError("'transitions' must be a list", f"{path}.transitions")
    if len(raw) > MAX_TRANSITIONS:
        raise EngineError(f"at most {MAX_TRANSITIONS} transitions are supported", f"{path}.transitions")

    state_set, alpha_set = set(states), set(alphabet)
    dfa_t: dict = {}
    nfa_t: dict = {}
    for i, t in enumerate(raw):
        tp = f"{path}.transitions[{i}]"
        if not isinstance(t, dict):
            raise EngineError("each transition must be an object {from, symbol, to}", tp)
        src, sym, dst = t.get("from"), t.get("symbol"), t.get("to")
        if src not in state_set:
            raise EngineError(f"unknown source state '{src}'", f"{tp}.from")
        if dst not in state_set:
            raise EngineError(f"unknown target state '{dst}'", f"{tp}.to")
        if not isinstance(sym, str):
            raise EngineError("symbol must be a string", f"{tp}.symbol")
        sym = sym.strip()
        is_eps = sym in EPS_ALIASES or sym == ""
        if is_eps:
            if kind == "DFA":
                raise EngineError("a DFA cannot have ε-transitions (use type NFA)", f"{tp}.symbol")
            nfa_t.setdefault((src, EPSILON), set()).add(dst)
            continue
        if sym not in alpha_set:
            raise EngineError(f"symbol '{sym}' is not in the alphabet", f"{tp}.symbol")
        if kind == "DFA":
            if (src, sym) in dfa_t and dfa_t[(src, sym)] != dst:
                raise EngineError(
                    f"nondeterminism: δ({src}, {sym}) already goes to '{dfa_t[(src, sym)]}' "
                    f"(a DFA allows one target per state and symbol; use type NFA)", tp)
            dfa_t[(src, sym)] = dst
        else:
            nfa_t.setdefault((src, sym), set()).add(dst)

    meta = {"name": name, "descriptions": _descriptions(spec, state_set)}
    if kind == "DFA":
        return DFA(states, alphabet, dfa_t, start, accept, name), "DFA", meta
    return NFA(states, alphabet, nfa_t, start, accept, name), "NFA", meta


def _descriptions(spec: dict, state_set: set) -> dict:
    d = spec.get("descriptions") or {}
    if not isinstance(d, dict):
        return {}
    return {k: str(v)[:200] for k, v in d.items() if k in state_set}


# ----------------------------------------------------------------- object -> spec

def dfa_to_spec(dfa: DFA, name: str | None = None, rename: dict | None = None,
                descriptions: dict | None = None, extra: dict | None = None) -> dict:
    """Serialise an original DFA object. `rename` maps raw state objects to
    display labels (used for subset-construction states D0, D1, ...)."""
    if rename:
        mapping = dict(rename)
    else:
        mapping, used = {}, set()
        for s in sorted(dfa.states, key=state_label):
            base = state_label(s)
            name_ = base
            k = 1
            while name_ in used:          # two composite states rendered the same text
                k += 1
                name_ = f"{base}#{k}"
            used.add(name_)
            mapping[s] = name_
    lab = mapping.__getitem__
    states = sorted({lab(s) for s in dfa.states}, key=_natural_key)
    transitions = sorted(
        ({"from": lab(s), "symbol": str(a), "to": lab(t)} for (s, a), t in dfa.transitions.items()),
        key=lambda x: (_natural_key(x["from"]), x["symbol"]))
    spec = {
        "type": "DFA",
        "name": name or dfa.name,
        "states": states,
        "alphabet": sorted(str(a) for a in dfa.alphabet),
        "start": lab(dfa.start),
        "accept": sorted({lab(s) for s in dfa.accept}, key=_natural_key),
        "transitions": transitions,
    }
    if descriptions:
        spec["descriptions"] = descriptions
    if extra:
        spec.update(extra)
    return spec


def nfa_to_spec(nfa: NFA, name: str | None = None, descriptions: dict | None = None) -> dict:
    transitions = []
    for (s, a), targets in nfa.transitions.items():
        for t in targets:
            transitions.append({"from": state_label(s), "symbol": sym_label(a), "to": state_label(t)})
    transitions.sort(key=lambda x: (_natural_key(x["from"]), x["symbol"], _natural_key(x["to"])))
    spec = {
        "type": "NFA",
        "name": name or nfa.name,
        "states": labels(nfa.states),
        "alphabet": sorted(str(a) for a in nfa.alphabet),
        "start": state_label(nfa.start),
        "accept": labels(nfa.accept),
        "transitions": transitions,
    }
    if descriptions:
        spec["descriptions"] = descriptions
    return spec


def to_spec(machine, kind: str, meta: dict | None = None) -> dict:
    meta = meta or {}
    if kind == "DFA":
        return dfa_to_spec(machine, meta.get("name"), descriptions=meta.get("descriptions"))
    return nfa_to_spec(machine, meta.get("name"), descriptions=meta.get("descriptions"))


def transition_table(spec: dict) -> dict:
    """Rows = states, columns = symbols (+ ε for NFAs). Missing cells are
    reported explicitly so the UI can show '—' (no transition)."""
    symbols = list(spec["alphabet"])
    has_eps = any(t["symbol"] == EPS_DISPLAY for t in spec["transitions"])
    if has_eps:
        symbols.append(EPS_DISPLAY)
    cells: dict = {}
    for t in spec["transitions"]:
        cells.setdefault(t["from"], {}).setdefault(t["symbol"], []).append(t["to"])
    rows = []
    for s in sorted(spec["states"], key=lambda q: q != spec["start"]):  # start state first, rest in order
        rows.append({
            "state": s,
            "start": s == spec["start"],
            "accepting": s in spec["accept"],
            "cells": {a: sorted(cells.get(s, {}).get(a, []), key=_natural_key) for a in symbols},
        })
    missing = sum(1 for r in rows for a in spec["alphabet"] if not r["cells"][a])
    return {"symbols": symbols, "rows": rows, "missing_transitions": missing}


# ----------------------------------------------------------------- input strings

def tokenize(text, alphabet, path: str = "input") -> list[str]:
    """Turn user input into a list of alphabet symbols.

    * If every symbol is a single character, the input is read character by
      character (whitespace ignored): "AUG" -> [A, U, G].
    * Otherwise (e.g. the codon-level alphabet START/SENSE/STOP) the input
      must be separated by spaces or commas: "START SENSE STOP".
    A list of strings is accepted as-is. Unknown symbols are reported with
    their position instead of being silently dropped.
    """
    alphabet = sorted(str(a) for a in alphabet)
    if isinstance(text, list):
        tokens = [str(t) for t in text]
    elif isinstance(text, str):
        if all(len(a) == 1 for a in alphabet):
            tokens = [c for c in text if not c.isspace()]
        else:
            tokens = [t for t in text.replace(",", " ").split() if t]
    else:
        raise EngineError("input must be a string or a list of symbols", path)
    if len(tokens) > MAX_INPUT_SYMBOLS:
        raise EngineError(f"input is limited to {MAX_INPUT_SYMBOLS} symbols for step-by-step tracing", path,
                          code="too_large")
    aset = set(alphabet)
    for i, tok in enumerate(tokens):
        if tok not in aset:
            raise EngineError(
                f"symbol '{tok}' at position {i} is not in the alphabet {{{', '.join(alphabet)}}}", path)
    return tokens
