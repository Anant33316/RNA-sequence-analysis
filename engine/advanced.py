"""
Advanced / experimental models beyond regular languages. All algorithms
live in the original modules (grammars/, turing/, module1_dfa/); this file
validates input, applies size limits and formats traces.
"""

from __future__ import annotations

from grammars.cfg_structure import fold, leftmost_derivation, is_in_language
from grammars.csg_pseudoknot import has_pseudoknot
from turing.tm_hairpin import find_hairpin_stems

from .errors import EngineError
from .rna import normalize_sequence

MAX_FOLD_LENGTH = 200
MAX_TABLE_LENGTH = 60
MAX_TM_LENGTH = 64
MAX_HAIRPIN_SCAN = 1000


def _clean(sequence: str, field: str = "sequence") -> str:
    norm = normalize_sequence(sequence or "", True)
    if norm["length_including_invalid"] == 0:
        raise EngineError("sequence is empty", field, code="empty")
    if not norm["valid"]:
        first = norm["invalid"][0]
        raise EngineError(f"invalid character '{first['char']}' at position {first['positions'][0]}: "
                          f"{first['reason']}", field)
    return norm["sequence"]


def fold_spec(sequence: str, min_loop: int = 3) -> dict:
    seq = _clean(sequence)
    if len(seq) > MAX_FOLD_LENGTH:
        raise EngineError(f"folding is O(n³); the limit is {MAX_FOLD_LENGTH} nt (got {len(seq)})", "sequence",
                          code="too_large")
    if not (0 <= min_loop <= 10):
        raise EngineError("min_loop must be between 0 and 10", "min_loop")
    trace: dict = {}
    structure, npairs = fold(seq, min_loop=min_loop, trace=trace)
    stack, pairs = [], []
    for i, ch in enumerate(structure):
        if ch == "(":
            stack.append(i)
        elif ch == ")":
            pairs.append((stack.pop(), i))
    pairs.sort()
    derivation, truncated = leftmost_derivation(seq, trace["tree"], max_steps=300)
    table = None
    if len(seq) <= MAX_TABLE_LENGTH:
        n = len(seq)
        table = [[trace["table"][i][j] if j > i else None for j in range(1, n + 1)] for i in range(n)]
    pk, _ = has_pseudoknot(pairs)
    return {
        "sequence": seq, "structure": structure, "pairs": [list(p) for p in pairs], "pair_count": npairs,
        "min_loop": min_loop, "derivation": [{"production": p, "form": f} for p, f in derivation],
        "derivation_truncated": truncated, "dp_table": table,
        "pair_types": [{"pair": [i, j], "bases": seq[i] + "-" + seq[j],
                        "type": "wobble" if {seq[i], seq[j]} == {"G", "U"} else "Watson–Crick"} for i, j in pairs],
        "perfectly_nested_language": is_in_language(seq),
        "pseudoknot": pk,
        "explanation": [
            "Grammar: S → xSy (x–y a valid pair: A–U, G–C, G–U) | xS (x unpaired) | SS | ε.",
            f"A CYK-style dynamic program (the Nussinov algorithm) fills best[i][j] = the maximum number of nested "
            f"pairs derivable from bases i..j−1, requiring at least {min_loop} unpaired base(s) inside every pair.",
            f"The optimum for the whole sequence is best[0][{len(seq)}] = {npairs} pair(s). Tracing back the choices "
            f"gives the parse tree; its leftmost derivation is shown step by step.",
            "Because every pair comes from S → xSy, the result is always properly NESTED: a context-free grammar of "
            "this form cannot produce crossing pairs (pseudoknots).",
        ],
        "disclaimer": ("Experimental educational model: it maximizes the NUMBER of base pairs. It ignores stacking "
                       "energies, loop penalties and thermodynamics, so it is not a validated RNA structure "
                       "prediction (real tools such as ViennaRNA minimize free energy)."),
    }


def hairpin_scan_spec(sequence: str, min_len: int = 4, max_len: int = 10, allow_center: bool = False) -> dict:
    seq = _clean(sequence)
    if len(seq) > MAX_HAIRPIN_SCAN:
        raise EngineError(f"hairpin scanning is limited to {MAX_HAIRPIN_SCAN} nt", "sequence", code="too_large")
    if not (2 <= min_len <= max_len <= 16):
        raise EngineError("require 2 ≤ min_len ≤ max_len ≤ 16", "min_len")
    hits = find_hairpin_stems(seq, min_len=min_len, max_len=max_len, allow_center=allow_center)
    hits.sort()
    return {"sequence": seq, "hits": [{"start": s, "end": e, "text": t} for s, e, t in hits[:2000]],
            "count": len(hits), "truncated": len(hits) > 2000, "min_len": min_len, "max_len": max_len,
            "allow_center": allow_center,
            "explanation": f"Every substring of length {min_len}–{max_len} was run through the Turing machine; "
                           f"{len(hits)} were accepted as complementary palindromes."}
