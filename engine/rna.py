"""
RNA sequence analysis.

Every feature here is a SYNTACTIC pattern computed by the project's
automata (or by plain counting); none of it is a biological prediction.
In particular an "ORF" is a START codon followed by an in-frame STOP codon
— not evidence of a functional gene.
"""

from __future__ import annotations

from collections import Counter
from itertools import product

from automata.dfa_nfa import find_orfs, START_CODON, STOP_CODONS
from automata.regex_motif import compile_motif, dfa_search
from module1_dfa.dfa_basics import build_substring_dfa, build_even_length_dfa
from module2_nfa.nfa_epsilon import build_altstart_epsilon_nfa
from module2_nfa.moore_mealy import build_complement_mealy, build_codon_boundary_mealy, build_ry_moore

from .errors import EngineError

BASES = ("A", "C", "G", "U")
MAX_SEQUENCE_LENGTH = 100_000
MAX_MATCHES_PER_MOTIF = 1000
MAX_CUSTOM_MOTIFS = 5

IUPAC = {
    "N": "IUPAC code for 'any base'", "R": "IUPAC code for a purine (A/G)", "Y": "IUPAC code for a pyrimidine (C/U)",
    "S": "IUPAC code for G/C", "W": "IUPAC code for A/U", "K": "IUPAC code for G/U", "M": "IUPAC code for A/C",
    "B": "IUPAC code for not-A", "D": "IUPAC code for not-C", "H": "IUPAC code for not-G", "V": "IUPAC code for not-U",
}

GENETIC_CODE = {}
_aa = "KNKNTTTTRSRSIIMIQHQHPPPPRRRRLLLLEDEDAAAAGGGGVVVV*Y*YSSSS*CWCLFLF"
for _i, _c in enumerate("".join(p) for p in product("ACGU", repeat=3)):
    GENETIC_CODE[_c] = _aa[_i]

MOTIF_LIBRARY = [
    {"id": "start", "name": "Start codon", "pattern": "AUG",
     "note": "Canonical start codon (methionine). Any AUG matches, in any frame."},
    {"id": "stop", "name": "Stop codons", "pattern": "UAA|UAG|UGA", "note": "The three standard stop codons."},
    {"id": "alt_start", "name": "Alternative start codons", "pattern": "(G|U)UG",
     "note": "GUG / UUG, used as start codons in some bacteria."},
    {"id": "polya", "name": "Poly(A) signal hexamer", "pattern": "AAUAAA",
     "note": "Canonical eukaryotic polyadenylation signal sequence."},
    {"id": "are", "name": "AU-rich element core", "pattern": "AUUUA",
     "note": "Pentamer found in AU-rich elements of some mRNA 3′ UTRs."},
    {"id": "sd", "name": "Shine–Dalgarno core", "pattern": "AGGAGG",
     "note": "Bacterial ribosome-binding site consensus core."},
    {"id": "gc4", "name": "GC run (≥4)", "pattern": "(G|C)(G|C)(G|C)(G|C)",
     "note": "Four consecutive G/C bases (every overlapping window is reported)."},
]


# ----------------------------------------------------------------- input parsing

def parse_sequence_text(text: str, filename: str | None = None) -> dict:
    """Parse raw text or FASTA. Returns records with raw sequences (unvalidated)."""
    if not isinstance(text, str):
        raise EngineError("sequence text must be a string", "text")
    stripped = text.strip()
    if not stripped:
        raise EngineError("the input is empty — paste an RNA sequence or upload a file", "text", code="empty")
    lines = stripped.splitlines()
    if lines[0].lstrip().startswith(">"):
        records, current = [], None
        for ln, line in enumerate(lines, start=1):
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            if line.startswith(">"):
                header = line[1:].strip()
                current = {"id": header.split()[0] if header else f"record{len(records) + 1}",
                           "description": header, "raw": [], "line": ln}
                records.append(current)
            else:
                current["raw"].append(line)
        for r in records:
            r["raw"] = "".join(r["raw"])
            if not r["raw"]:
                raise EngineError(f"FASTA record '{r['id']}' (line {r['line']}) has no sequence lines", "text",
                                  code="malformed")
        return {"format": "fasta", "records": [{"id": r["id"], "description": r["description"], "raw": r["raw"]}
                                               for r in records]}
    if any(line.lstrip().startswith(">") for line in lines[1:]):
        raise EngineError("a '>' header appears after sequence data: FASTA files must start with a header line",
                          "text", code="malformed")
    return {"format": "raw", "records": [{"id": filename or "input", "description": "", "raw": "".join(lines)}]}


def normalize_sequence(raw: str, convert_t: bool = True) -> dict:
    """Uppercase, drop whitespace, optionally map T->U, and report every
    invalid character with its position and an explanation."""
    seq_chars = []
    invalid = []
    t_count = lower = 0
    pos = 0
    for ch in raw:
        if ch.isspace():
            continue
        up = ch.upper()
        if up != ch:
            lower += 1
        if up == "T" and convert_t:
            up = "U"
            t_count += 1
        if up in BASES:
            seq_chars.append(up)
        else:
            invalid.append((pos, ch))
        pos += 1
    warnings = []
    if t_count:
        warnings.append(f"{t_count} T (thymine, DNA) converted to U.")
    if lower:
        warnings.append(f"{lower} lowercase letter(s) converted to uppercase.")
    issues = []
    if invalid:
        by_char = Counter(c for _, c in invalid)
        for ch, n in by_char.most_common():
            up = ch.upper()
            if up == "T":
                why = "T is a DNA base; enable 'Treat T as U' to read DNA input"
            elif up in IUPAC:
                why = IUPAC[up] + " — ambiguity codes are not part of the {A, C, G, U} alphabet"
            elif ch.isdigit():
                why = "digit (e.g. GenBank position numbers) — remove numbering"
            elif ch in "-.":
                why = "alignment gap character"
            else:
                why = "not a nucleotide symbol"
            positions = [p for p, c in invalid if c == ch]
            issues.append({"char": ch, "count": n, "positions": positions[:20],
                           "more_positions": max(0, len(positions) - 20), "reason": why})
    return {"sequence": "".join(seq_chars), "length_including_invalid": pos, "invalid": issues,
            "invalid_count": len(invalid), "warnings": warnings, "valid": not invalid and pos > 0}


# ----------------------------------------------------------------- analysis

def _composition(seq: str) -> dict:
    n = len(seq)
    counts = {b: seq.count(b) for b in BASES}
    pct = {b: (100.0 * counts[b] / n if n else 0.0) for b in BASES}
    gc = counts["G"] + counts["C"]
    return {"counts": counts, "percent": {b: round(v, 2) for b, v in pct.items()},
            "gc_percent": round(100.0 * gc / n, 2) if n else 0.0,
            "au_percent": round(100.0 * (n - gc) / n, 2) if n else 0.0}


def _gc_windows(seq: str) -> dict:
    n = len(seq)
    if n < 20:
        return {"window": None, "points": []}
    window = max(10, min(200, n // 25))
    step = max(1, window // 2)
    points = []
    for start in range(0, n - window + 1, step):
        w = seq[start:start + window]
        points.append({"start": start, "gc": round(100.0 * (w.count("G") + w.count("C")) / window, 2)})
    return {"window": window, "step": step, "points": points}


def _codon_positions(seq: str) -> dict:
    starts, stops = [], []
    for i in range(len(seq) - 2):
        c = seq[i:i + 3]
        if c == START_CODON:
            starts.append({"pos": i, "frame": i % 3, "codon": c})
        elif c in STOP_CODONS:
            stops.append({"pos": i, "frame": i % 3, "codon": c})
    return {"start": starts, "stop": stops}


def _frames(seq: str) -> list[dict]:
    frames = []
    for f in range(3):
        usable = (len(seq) - f) // 3 * 3 if len(seq) > f else 0
        codons = [seq[i:i + 3] for i in range(f, f + usable, 3)]
        usage = Counter(codons)
        trailing = len(seq) - f - usable if len(seq) > f else 0
        frames.append({"frame": f, "codon_count": len(codons), "leading_bases": min(f, len(seq)),
                       "trailing_bases": trailing,
                       "incomplete_note": (f"{trailing} trailing base(s) do not form a complete codon."
                                           if trailing else "No incomplete trailing codon."),
                       "usage": dict(sorted(usage.items(), key=lambda kv: (-kv[1], kv[0]))),
                       "preview": codons[:40]})
    return frames


def _orfs(seq: str, min_codons: int) -> list[dict]:
    out = []
    for f in range(3):
        for (s, e, orf) in find_orfs(seq, frame=f):
            codons = len(orf) // 3
            if codons < min_codons:
                continue
            protein = "".join(GENETIC_CODE[orf[i:i + 3]] for i in range(0, len(orf), 3))
            out.append({"frame": f, "start": s, "end": e, "length_nt": len(orf), "codons": codons,
                        "sequence": orf if len(orf) <= 3000 else orf[:3000] + "…",
                        "translation": protein if len(protein) <= 1000 else protein[:1000] + "…"})
    out.sort(key=lambda o: (o["start"], o["frame"]))
    return out


def _motifs(seq: str, custom: list[dict] | None) -> list[dict]:
    results = []
    entries = [dict(m, custom=False) for m in MOTIF_LIBRARY]
    for i, c in enumerate(custom or []):
        pattern = str(c.get("pattern", "")).strip().upper()
        entries.append({"id": f"custom{i}", "name": str(c.get("name") or pattern)[:60], "pattern": pattern,
                        "note": "User-defined pattern.", "custom": True})
    for m in entries:
        try:
            dfa = compile_motif(m["pattern"])
        except ValueError as exc:
            raise EngineError(f"motif '{m['name']}': {exc}", "motifs") from exc
        matches = dfa_search(dfa, seq)
        truncated = len(matches) > MAX_MATCHES_PER_MOTIF
        results.append({"id": m["id"], "name": m["name"], "pattern": m["pattern"], "note": m["note"],
                        "custom": m["custom"], "dfa_states": len(dfa["states"]), "count": len(matches),
                        "truncated": truncated,
                        "matches": [{"start": s, "end": e, "text": t} for s, e, t in matches[:MAX_MATCHES_PER_MOTIF]]})
    return results


def _language_properties(seq: str) -> list[dict]:
    """Run the project's own automata on the whole sequence."""
    aug = build_substring_dfa("AUG")
    even = build_even_length_dfa()
    enfa = build_altstart_epsilon_nfa()
    rows = [
        {"example": "aug_dfa", "language": "contains AUG", "machine": "KMP DFA (4 states)", "accepted": aug.accepts(seq)},
        {"example": "even_dfa", "language": "even length", "machine": "DFA (2 states)", "accepted": even.accepts(seq)},
        {"example": "altstart_enfa", "language": "contains AUG | GUG | UUG", "machine": "ε-NFA (11 states)",
         "accepted": enfa.accepts(seq)},
    ]
    a, b = rows[0]["accepted"], rows[1]["accepted"]
    rows.append({"example": None, "language": "contains AUG ∩ even length", "machine": "product DFA",
                 "accepted": a and b, "derived": True})
    rows.append({"example": None, "language": "¬ contains AUG", "machine": "complement DFA",
                 "accepted": not a, "derived": True})
    return rows


def _transducers(seq: str, limit: int = 20000) -> dict:
    s = seq[:limit]
    comp, _ = build_complement_mealy().run(s)
    marks, _ = build_codon_boundary_mealy().run(s)
    ry, _ = build_ry_moore().run(s)
    return {"truncated_to": limit if len(seq) > limit else None,
            "complement": comp, "reverse_complement": comp[::-1], "codon_boundaries": marks, "ry": ry[1:],
            "notes": {"complement": "Mealy machine, 1 state (output on each transition).",
                      "reverse_complement": "The complement above, reversed (5′→3′ of the partner strand). "
                                            "Reversal is done after the transducer — a single left-to-right "
                                            "finite transducer cannot reverse a string.",
                      "codon_boundaries": "Mealy machine, 3 states (reading-frame phase); 1 = first base of a "
                                          "frame-0 codon.",
                      "ry": "Moore machine; R = purine (A, G), Y = pyrimidine (C, U). The start-state symbol "
                            "is omitted."}}


def analyze_sequence(text: str, convert_t: bool = True, record_index: int = 0, min_orf_codons: int = 0,
                     custom_motifs: list[dict] | None = None, filename: str | None = None) -> dict:
    parsed = parse_sequence_text(text, filename)
    records = parsed["records"]
    if not (0 <= record_index < len(records)):
        raise EngineError(f"record_index {record_index} is out of range (file has {len(records)} record(s))",
                          "record_index")
    rec = records[record_index]
    norm = normalize_sequence(rec["raw"], convert_t)
    if norm["length_including_invalid"] == 0:
        raise EngineError("the selected record contains no sequence characters", "text", code="empty")
    if norm["length_including_invalid"] > MAX_SEQUENCE_LENGTH:
        raise EngineError(f"sequence is {norm['length_including_invalid']:,} nt; the limit is "
                          f"{MAX_SEQUENCE_LENGTH:,} nt", "text", code="too_large")
    if custom_motifs and len(custom_motifs) > MAX_CUSTOM_MOTIFS:
        raise EngineError(f"at most {MAX_CUSTOM_MOTIFS} custom motifs", "motifs")
    if not (0 <= int(min_orf_codons) <= 10000):
        raise EngineError("min_orf_codons must be between 0 and 10000", "min_orf_codons")
    base = {"format": parsed["format"],
            "records": [{"id": r["id"], "description": r["description"], "raw_length": len(r["raw"])} for r in records],
            "record_index": record_index, "record_id": rec["id"], "validation": norm}
    if not norm["valid"]:
        first = norm["invalid"][0]
        base["valid"] = False
        base["error"] = (f"{norm['invalid_count']} invalid character(s). First problem: '{first['char']}' at position "
                         f"{first['positions'][0]} — {first['reason']}.")
        return base
    seq = norm["sequence"]
    base.update({
        "valid": True, "sequence": seq, "length": len(seq),
        "composition": _composition(seq), "gc_profile": _gc_windows(seq),
        "codon_positions": _codon_positions(seq), "frames": _frames(seq),
        "orfs": _orfs(seq, int(min_orf_codons)), "min_orf_codons": int(min_orf_codons),
        "motifs": _motifs(seq, custom_motifs), "language_properties": _language_properties(seq),
        "transducers": _transducers(seq),
        "disclaimer": ("All features are syntactic pattern matches produced by finite automata. An ORF here is a "
                       "START codon followed by an in-frame STOP codon on the given strand; it is not evidence of a "
                       "functional gene, and motif matches are not functional annotations."),
    })
    if len(seq) % 3:
        base["warnings"] = [f"Length {len(seq)} is not a multiple of 3: frame 0 ends with {len(seq) % 3} "
                            f"incomplete base(s)."]
    return base


def orf_trace(sequence: str, frame: int, limit: int = 3000) -> dict:
    norm = normalize_sequence(sequence, True)
    if not norm["valid"]:
        raise EngineError("sequence contains invalid characters", "sequence")
    if frame not in (0, 1, 2):
        raise EngineError("frame must be 0, 1 or 2", "frame")
    seq = norm["sequence"]
    trace: list = []
    orfs = find_orfs(seq, frame=frame, trace=trace)
    rows = []
    for r in trace[:limit]:
        if r["action"] == "start":
            text = f"{r['codon']} is START: the ORF DFA leaves q0 → q1 (an ORF begins at {r['pos']})."
        elif r["action"] == "extend":
            text = f"{r['codon']} is {r['class']}: q1 → q1 (inside the ORF; AUG here is read as methionine)."
        elif r["action"] == "accept":
            text = f"{r['codon']} is STOP: q1 → q2, an ACCEPTING state — ORF recognised, scanner resets."
        elif r["action"] == "abort":
            text = f"{r['codon']} is not a valid codon: the run is abandoned."
        else:
            text = f"{r['codon']} is {r['class']}: outside an ORF, waiting for a START codon."
        rows.append(dict(r, explanation=text))
    return {"frame": frame, "orfs": [{"start": s, "end": e, "sequence": o} for s, e, o in orfs],
            "steps": rows, "truncated": len(trace) > limit, "codons": len(trace)}


def compile_motif_spec(pattern: str) -> dict:
    """Expose the regex -> Thompson NFA -> DFA pipeline for visualisation."""
    from automata.regex_motif import regex_to_nfa, nfa_to_dfa, nfa_reachable_states, EPSILON as REPS
    from module1_dfa.dfa_basics import DFA
    from .minimize import minimize_spec
    from .automaton_io import dfa_to_spec
    pattern = (pattern or "").strip().upper()
    try:
        start, accepts = regex_to_nfa(pattern)
    except ValueError as exc:
        raise EngineError(str(exc), "pattern") from exc
    states = nfa_reachable_states(start)
    nfa_spec = {"type": "NFA", "name": f"Thompson NFA for /{pattern}/", "states": [f"n{s.id}" for s in states],
                "alphabet": list(BASES), "start": f"n{start.id}", "accept": [f"n{s.id}" for s in accepts],
                "transitions": [{"from": f"n{s.id}", "symbol": "ε" if sym == REPS else sym, "to": f"n{t.id}"}
                                for s in states for sym, targets in sorted(s.transitions.items())
                                for t in sorted(targets, key=lambda x: x.id)]}
    raw = nfa_to_dfa(start, accepts, list(BASES))
    order = sorted(raw["states"], key=lambda fs: (fs != raw["start"], sorted(x.id for x in fs)))
    names = {fs: f"D{i}" for i, fs in enumerate(order)}
    dfa = DFA(raw["states"], BASES, raw["transitions"], raw["start"], raw["accept"], f"DFA for /{pattern}/")
    dfa_spec = dfa_to_spec(dfa, f"DFA for /{pattern}/", rename=names,
                           descriptions={names[fs]: "{" + ", ".join(f"n{x.id}" for x in sorted(fs, key=lambda x: x.id)) + "}"
                                         for fs in order})
    minimized = minimize_spec(dfa_spec)
    return {"pattern": pattern, "nfa": nfa_spec, "dfa": dfa_spec, "minimized": minimized["after"],
            "counts": {"nfa": len(nfa_spec["states"]), "dfa": len(dfa_spec["states"]),
                       "minimized": len(minimized["after"]["states"])},
            "note": ("The search DFA is partial (no dead state): a missing move ends the match attempt at that start "
                     "position. The minimized DFA is completed with a trap state, so it can have one more state "
                     "than expected.")}
