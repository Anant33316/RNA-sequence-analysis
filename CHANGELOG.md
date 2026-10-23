# Changelog

## 2.1.0 — Advanced Concepts section removed

Removed from the web application, at the author's request: **Closure Properties**, **Moore & Mealy** and
**Grammars, LBA & Turing Machines** (the sidebar's "Advanced Concepts" group), with their pages, routes and API endpoints.
This version builds on the sidebar reorganization of 2.0.

**Kept on purpose (shared with retained features):**
* The original algorithm modules `module1_dfa/closure_properties.py`, `module2_nfa/moore_mealy.py`, `grammars/` and
  `turing/`, and both command-line programs (`main_module1_2.py`, `main.py`), are byte-for-byte unchanged.
  `moore_mealy.py` also powers the RNA analyzer's Transducers tab.
* The RNA analyzer's experimental *Structure* tab (CFG folding and Turing-machine hairpin scan) and its two endpoints,
  `POST /api/advanced/fold` and `POST /api/advanced/hairpins`, are unchanged.
* `GET /api/rna/motifs` still reports `max_tm` in its limits, so its response is unchanged.

**API endpoints removed (now 404):** `POST /api/automata/closure`, `GET /api/machines/examples`,
`POST /api/machines/run`, `POST /api/machines/convert`, `POST /api/advanced/tm`, `POST /api/advanced/lba`,
`POST /api/advanced/pumping`.

**Files deleted (5):** `web/js/views/closure.js`, `web/js/views/machines.js`, `web/js/views/advanced.js`
(the three pages), `engine/closure.py`, `engine/machines.py` (used only by those pages' endpoints).

**Files modified:**
* `web/index.html` — the "Advanced Concepts" sidebar group.
* `web/js/app.js` — the three routes.
* `web/js/views/overview.js` — the three module cards that linked to the removed pages.
* `web/js/views/rna.js` — the "Step through these machines" link (to the removed Moore & Mealy page).
* `web/js/views/history.js` — the "Closure constructions" filter and its Open branch; CFG-fold entries now open the RNA analyzer, where CFG folding lives.
* `web/js/views/learn.js` — passages and API rows about the removed features.
* `api/app.py` — the seven endpoints, their two handlers and the now-unused imports.
* `api/schemas.py` — the eight request models used only by those endpoints.
* `engine/advanced.py` — `tm_spec`, `lba_spec`, `pumping_spec` and the imports only they used (`fold_spec`, `hairpin_scan_spec` unchanged).
* Tests: `tests/test_api.py`, `tests/test_automata_engine.py`, `tests/test_machines_advanced.py`,
  `tests/test_e2e_browser.py`, `tests/test_frontend_static.py` — tests of removed features deleted, absence checks added.
* Docs: `README.md`, `docs/FEATURES.md`, `docs/DEMO_WALKTHROUGH.md`, `docs/ARCHITECTURE.md`, `docs/TEST_RESULTS.md`, this file.

## 2.0.0 — interactive, explainable web application

### Audit summary (state of the uploaded project)

* 16 Python files (~1,900 lines), standard library only, no test suite: each
  module checked itself with `assert`s in its `__main__` block. All scripts ran and
  all built-in assertions passed.
* Verified correct by exhaustive or reference checks: the KMP substring DFA,
  closure products over the same alphabet, ε-elimination, subset construction,
  the Moore/Mealy machines and the pumping-lemma demonstration.
* Running from another directory failed (`ModuleNotFoundError`), because imports
  relied on the current working directory.

### Bugs found and fixed (each has a regression test in `tests/test_bug_fixes.py`)

| # | File | Bug | Evidence | Fix |
|---|---|---|---|---|
| 1 | `turing/tm_hairpin.py` | The TM's "seek right" phase ran onto cells already marked `X`, so after the outermost pair matched it **always accepted** (`CCCG`, `UAAA` accepted). It also crashed with `IndexError` on 1-symbol input. | 1,200 wrong verdicts and 4 crashes over all strings of length ≤ 6 | Seek now stops at the rightmost *unmarked* cell; the remembered base lives in the finite control (`seek_A`…`check_U`); blank cells on both sides. 0 mismatches over all 21,845 strings of length ≤ 7 |
| 2 | `grammars/cfg_structure.py` `fold` | Off-by-one: hairpin loops of only `min_loop − 1` bases were allowed, and the first base of an interval could never pair with the last. `GGGAAAUCC` gave 1 pair instead of 3. | Compared with a brute-force maximum | Pair range corrected; matches brute force on 1,500 random sequences × 2 loop settings |
| 3 | `grammars/cfg_structure.py` `is_in_language` | With the default `min_loop=3` the language was empty for every non-empty string (the innermost pair of a fully-paired structure encloses nothing). | Exhaustive check up to length 8 | Default `min_loop=0`; reason documented |
| 4 | `module1_dfa/minimization.py` | Unreachable states were never removed, so the result was not always minimal. | 3-state DFA with an unreachable state stayed at 3 | Remove unreachable states first; rounds now record a distinguishing string for each marked pair (verified on 60 random DFAs) |
| 5 | `module1_dfa/closure_properties.py` | With different alphabets the product pointed to states that did not exist (`(0, 'TRAP')`). | Direct test | Both DFAs are completed over the union alphabet; difference, symmetric difference and reachable-only construction added |
| 6 | `automata/regex_motif.py` | Malformed patterns (`(AU`, `AU)`, `*A`, `A||U`, `AN`) were silently accepted and misparsed. | Direct test | `RegexSyntaxError` with position; thread-safe state numbering |
| 7 | `grammars/csg_pseudoknot.py` | Every crossing pair was drawn as `[]`, so pairs crossing each other *and* an earlier pair looked nested. | Three-way crossing example | First non-conflicting type among `() [] {} <>`; the LBA checker now works purely on the tape and records each pass |
| 8 | `main_module1_2.py` | Reported "Open Reading Frame: Absent" for a sequence containing `AUG GCU ACG UAA`, because it required the *whole* sequence to be one ORF. It also crashed when run from another directory. | Demo sequence | Reports ORFs found by DFA scanning in all 3 frames, plus whole-sequence membership; path-independent imports |
| 9 | `automata/dfa_nfa.py` | `find_orfs` never used the ORF DFA it built (hand-written scan). | Code inspection | Now feeds codons to the DFA and accepts when it reaches `q2`; identical results to the old scan on 20,000 random sequences × 3 frames |
| 10 | `main.py` | Invalid input (e.g. `AUGXX`) was processed silently. | Direct run | Validation with position and exit code 2 |
| — | NFA/DFA equivalence | Only checked on 98 sample strings (evidence, not proof). | — | Exhaustive product-construction check with shortest counterexample (engine/equivalence.py) |

### Behaviour preserved

* All original command-line entry points and every module's `__main__` still run, with the same outputs except where a bug was fixed (regression tests in `tests/test_original_regressions.py`).
* Original function signatures are unchanged; new abilities are optional keyword arguments (`trace=`, `reachable_only=`, `include_dead_state=`, `allow_center=`).
* The duplicate ORF DFA in `automata/dfa_nfa.py` now reuses the Module 1 definition (single source of truth).

### Files

**Modified (14):**
`README.md`, `main.py`, `main_module1_2.py`,
`module1_dfa/dfa_basics.py`, `module1_dfa/closure_properties.py`, `module1_dfa/minimization.py`,
`module2_nfa/nfa_epsilon.py`, `module2_nfa/epsilon_elimination.py`, `module2_nfa/subset_construction_equivalence.py`,
`automata/dfa_nfa.py`, `automata/regex_motif.py`, `grammars/cfg_structure.py`, `grammars/csg_pseudoknot.py`, `turing/tm_hairpin.py`
(`module1_dfa/regular_vs_nonregular.py` and `module2_nfa/moore_mealy.py` are unchanged.)

**Added:**
* Packages: `module1_dfa/__init__.py`, `module2_nfa/__init__.py`, `automata/__init__.py`, `grammars/__init__.py`, `turing/__init__.py`
* Engine: `engine/__init__.py`, `errors.py`, `automaton_io.py`, `simulate.py`, `examples.py`, `conversions.py`, `minimize.py`, `closure.py`, `equivalence.py`, `machines.py`, `rna.py`, `advanced.py`
* API: `api/__init__.py`, `app.py`, `schemas.py`, `history.py`
* Frontend: `web/index.html`, `web/favicon.svg`, `web/css/app.css`, `web/js/{app,api,dom,graph,components,rnaviz,theme-init}.js`, `web/js/views/{overview,rna,playground,convert,minimize,closure,machines,verify,advanced,history,learn}.js`
* Tests: `tests/__init__.py`, `_paths.py`, `asgi_client.py`, `test_original_regressions.py`, `test_bug_fixes.py`, `test_automata_engine.py`, `test_rna.py`, `test_machines_advanced.py`, `test_api.py`, `test_frontend_static.py`, `test_e2e_browser.py`
* Docs and project files: `CHANGELOG.md`, `docs/ARCHITECTURE.md`, `docs/FEATURES.md`, `docs/DEMO_WALKTHROUGH.md`, `docs/TEST_RESULTS.md`, `run_app.py`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `data/README.txt`, `samples/*`

**Removed (12):** compiled bytecode shipped in the ZIP — `*/__pycache__/*.cpython-313.pyc` (generated artifacts; now git-ignored).
