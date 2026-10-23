# Analyzing RNA Sequences Using Theory of Computation

An interactive, explainable Theory of Computation laboratory for RNA sequences.
The original Module 1 (DFA) and Module 2 (NFA) implementations, plus the early
CFG / LBA / Turing-machine drafts, are preserved, bug-fixed and tested. They now
power a local web application with step-by-step execution traces, generated
state diagrams and verification tools.

> **Every result comes from running an algorithm.** Diagrams are drawn from the
> automaton definition, highlights come from recorded execution traces, and
> explanations are produced deterministically from those traces. Nothing is
> hard-coded or simulated, and no AI model is involved.

---

## Quick start: Windows PowerShell

Requires **Python 3.10 or newer** (check with `python --version`). Node.js is **not** needed.

```powershell
# 1. unzip the project, then open PowerShell in the project folder
cd path\to\rna_toc_project

# 2. create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
#   If activation is blocked by the execution policy, run this once and retry:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# 3. install the four runtime packages
pip install -r requirements.txt

# 4. start the app (opens your browser)
python run_app.py --open
#   -> http://127.0.0.1:8000     stop with Ctrl+C
```

Run the tests:

```powershell
python -m unittest discover -s tests -t .
# or, after  pip install -r requirements-dev.txt :
python -m pytest
```

The original command-line programs still work and need **no** packages:

```powershell
python main_module1_2.py          # Module 1 + 2 report (the original submission)
python main.py                    # all Chomsky levels on the demo sequence
python main.py AUGGCUUAAGGG       # ...or on your own sequence
python module1_dfa\minimization.py   # every module file is still runnable on its own
```

### macOS / Linux

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 run_app.py --open
python3 -m unittest discover -s tests -t .
```

`run_app.py` options: `--port 9000`, `--host 127.0.0.1` (the default is local-only), `--open`, `--reload`.

---

## What the application does

| Section | What you can do | Status |
|---|---|---|
| **Overview** | Type bases into a live DFA (the project's KMP "contains AUG" automaton) and watch it run; Chomsky-hierarchy map | Core |
| **RNA analyzer** | Paste or upload (FASTA/raw, ≤ 2 MB, ≤ 100,000 nt). Validation explains each invalid character with its position. Composition, GC profile, colour-coded paged sequence viewer, start/stop codons in all frames, ORFs (DFA-driven, with translation and a codon-by-codon DFA trace), motifs (regex → ε-NFA → DFA, custom patterns, view their automata), whole-sequence language membership, Moore/Mealy transducer outputs. Click any result to jump to it in the sequence. JSON export and printable report. Experimental *Structure* tab: CFG folding (Nussinov = CYK) with derivation and arc diagram, and a Turing-machine hairpin-stem scan | Core (Structure tab: **Experimental**) |
| **Automata playground** | Define a DFA/NFA (form or JSON) or load 13 built-in examples; validation (missing transitions, unreachable states, nondeterminism, ε-moves); generated, draggable state diagram; transition table; step-by-step trace player (active **set** for NFAs, ε-closures shown, missing transitions shown) | Core |
| **ε-elimination & NFA→DFA** | Every ε-closure and every subset, with the move/closure that produced it; highlight the NFA states inside each DFA state; optional explicit ∅ dead state | Core |
| **DFA minimization** | Unreachable-state removal → completion → table-filling round by round; partition colouring; pair table with a **distinguishing string** for every marked pair | Core |
| **Verification lab** | **Exhaustive** equivalence proof (product BFS) with the **shortest counterexample**, re-verified by running both machines; **bounded** testing clearly labelled "evidence only"; side-by-side traces and tables | Core |
| **History** | Saved analyses in local SQLite (`data/history.db`); reopen, delete, clear | Core |
| **Learn & docs** | How explanations are produced, proof vs evidence, limits, keyboard shortcuts, API reference | — |

See [`docs/FEATURES.md`](docs/FEATURES.md) for the full list of implemented, experimental
and deliberately excluded features.

## Scientific honesty

* An **ORF** here is a syntactic pattern: AUG followed by an in-frame stop codon on the given strand. It is **not** a gene prediction.
* **Motif** matches are regular-expression matches, not functional annotations.
* **CFG folding** maximizes the *number* of nested base pairs. It ignores thermodynamics, so it is not a validated structure predictor.
* The **Turing machine** decides complementary palindromes, which are only hairpin-stem *candidates*.
* **Bounded testing** is never presented as proof; only the product-construction check is.

---

## Syllabus coverage (original Module 1 & 2 submission, preserved)

### Module 1: Deterministic Finite Automata

| Syllabus topic | File | RNA application |
|---|---|---|
| Chomsky hierarchy intro | `main_module1_2.py`, Overview page | 4-level hierarchy mapped to RNA problems |
| Introduction to FA, examples | `module1_dfa/dfa_basics.py` | DFA for "contains start codon AUG" (KMP construction), codon-level ORF DFA `START (SENSE)* STOP` |
| Language & string acceptance | `module1_dfa/dfa_basics.py` | `DFA.accepts`, `DFA.run_trace` |
| Closure properties | `module1_dfa/closure_properties.py` | Product construction for ∪, ∩, −, ⊕ and complement |
| Minimization of FA | `module1_dfa/minimization.py` | Unreachable removal + table-filling (Myhill–Nerode) with witnesses |
| Regular vs non-regular | `module1_dfa/regular_vs_nonregular.py` | Pumping-lemma proof that `{GⁿCⁿ}` is not regular |

### Module 2: Non-Deterministic Finite Automata

| Syllabus topic | File | RNA application |
|---|---|---|
| Intro & examples | `module2_nfa/nfa_epsilon.py` | ε-NFA for "contains AUG, GUG or UUG" (alternative start codons) |
| FA with ε-transitions, conversion | `module2_nfa/nfa_epsilon.py`, `module2_nfa/epsilon_elimination.py` | ε-closure construction |
| Equivalence of NFA and DFA | `module2_nfa/subset_construction_equivalence.py`, Verification lab | Subset construction + exhaustive product-based equivalence check |
| Moore and Mealy machines | `module2_nfa/moore_mealy.py` | Complement transducer, codon-boundary marker (Mealy), RY encoder (Moore) |

### Beyond the syllabus (early drafts, now fixed and tested)

| Level | File | Model |
|---|---|---|
| Regular | `automata/regex_motif.py`, `automata/dfa_nfa.py` | Regex → Thompson ε-NFA → DFA motif search; DFA-driven ORF scanning |
| Context-free | `grammars/cfg_structure.py` | Secondary-structure CFG parsed by CYK/Nussinov, derivations |
| Context-sensitive | `grammars/csg_pseudoknot.py` | Crossing-pair detection, LBA-style in-place bracket checker |
| Turing-decidable | `turing/tm_hairpin.py` | Single-tape TM for complementary palindromes |

---

## Project layout

```
rna_toc_project/
├─ module1_dfa/  module2_nfa/          original algorithms (bug-fixed, now emit traces)
├─ automata/  grammars/  turing/       original advanced drafts (bug-fixed)
├─ engine/                             validation, JSON <-> objects, explanations, RNA analysis
├─ api/                                Starlette app, Pydantic schemas, SQLite history
├─ web/                                frontend: HTML, CSS, ES-module JavaScript (no build step)
├─ tests/                              104 automated tests (unittest; pytest-compatible)
├─ samples/                            sample FASTA, invalid input, automaton JSON files
├─ docs/                               architecture, features, demo walkthrough, test results
├─ main_module1_2.py  main.py           original command-line entry points
├─ run_app.py                          starts the web app
└─ requirements.txt  requirements-dev.txt
```

* Architecture and design decisions: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
* Presentation script for the viva: [`docs/DEMO_WALKTHROUGH.md`](docs/DEMO_WALKTHROUGH.md)
* What changed and why (bugs, files): [`CHANGELOG.md`](CHANGELOG.md)
* Recorded test run: [`docs/TEST_RESULTS.md`](docs/TEST_RESULTS.md)

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` not found on Windows | Install Python from python.org and tick "Add python.exe to PATH", or use `py` instead of `python` |
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |
| Port 8000 already in use | `python run_app.py --port 8080` |
| Page shows "Server offline" | The terminal running `run_app.py` was closed; start it again |
| Browser shows an old version | Hard-refresh with Ctrl+F5 |
