# Test results

## 2.1.0 (Advanced Concepts section removed)

Recorded on 2026-10-18 in the build environment (Linux, same package versions as below). Actual output of
`python -m unittest discover -s tests -t . -v`: **104 tests, 104 passed, 0 failed, 0 skipped** (Ran 104 tests in 11.717s).

| Module | Tests |
|---|---|
| `test_original_regressions` | 14 |
| `test_bug_fixes` | 16 |
| `test_automata_engine` | 25 |
| `test_rna` | 21 |
| `test_machines_advanced` | 3 |
| `test_api` | 18 |
| `test_frontend_static` | 6 |
| `test_e2e_browser` | 1 |

Compared with 2.0 (114 tests): the 4 closure-lab tests, 4 Moore/Mealy tests and 3 TM-trace/LBA/pumping tests were
removed with their features; 1 static test was added that checks the removed pages are absent, and one API test now
checks that the seven removed endpoints return 404. The regression and bug-fix tests for the original closure,
Moore/Mealy, CFG, LBA and Turing-machine modules are unchanged and pass.

Also checked in headless Chromium: all 8 sidebar links open the right page; `#/closure`, `#/machines` and `#/advanced`
fall back to the Overview; the RNA analyzer (analysis, ORF DFA trace, motifs and their automata, Transducers tab, and
the Structure tab's CFG fold and TM hairpin scan), playground, ε-elimination, subset construction, minimization,
verification (proof and bounded tests), History and Learn pages all work; no console errors. `main_module1_2.py` and
`main.py` run unchanged.

---

## 2.0.0 (earlier record, kept for reference)

Recorded on 2026-10-18 in the build environment (Linux, Python 3.13.16, starlette 1.6.0, pydantic 2.13.5, uvicorn 0.53.0).
These are the actual results of the commands below, not assumed results.

## Baseline (original upload, before any change)

- No automated test suite existed. Every module's `__main__` self-check ran and passed (13 scripts, exit code 0); `main_module1_2.py` and `main.py` ran.
- Exhaustive probes found the bugs listed in CHANGELOG.md (e.g. the Turing machine gave 1,200 wrong verdicts on strings of length ≤ 6 and crashed on 1-symbol input).

## Automated suite

```
python -m unittest discover -s tests -t . -v
```

Result: **114 tests, all passed** (Ran 114 tests in 14.416s).

| Module | Tests | What it covers |
|---|---|---|
| `test_original_regressions` | 14 | original behaviour: KMP DFA exhaustive, closure table, 4→2 minimization, 98-string equivalence, transducer outputs, DFA ORF scan = old scan on 3,000 random sequences, all CLI scripts run |
| `test_bug_fixes` | 16 | one class per fixed bug; TM exhaustive to length 7, CFG vs brute force, witness strings, product alphabets, regex errors, bracket typing |
| `test_automata_engine` | 29 | validation errors, DFA/NFA traces, missing transitions, ε-cycles, empty string, subset/ε-elimination on 120 random NFAs, minimization on 150 random DFAs, closure vs reference, equivalence vs brute force on 300 random pairs |
| `test_rna` | 21 | empty/invalid/oversized input, FASTA records, T→U, incomplete codons, overlapping motifs, ORFs, genetic code, 100,000-nt input |
| `test_machines_advanced` | 10 | Moore/Mealy outputs and conversions, CFG fold/derivation, TM, hairpin scan, LBA, pumping lemma, limits |
| `test_api` | 18 | status codes 200/204/400/404/405/413/415/422, error shape, uploads, history CRUD |
| `test_frontend_static` | 5 | imports resolve, routes have views, assets exist, no innerHTML, JS syntax (Node) |
| `test_e2e_browser` | 1 | real uvicorn server + headless Chromium: every page renders and one interaction each, no JS errors (skipped without Playwright) |

<details><summary>Full verbose output</summary>

```
test_frontend_served (tests.test_api.Basics.test_frontend_served) ... ok
test_health (tests.test_api.Basics.test_health) ... ok
test_unknown_and_wrong_method (tests.test_api.Basics.test_unknown_and_wrong_method) ... ok
test_closure_equivalence_bounded_compare (tests.test_api.Endpoints.test_closure_equivalence_bounded_compare) ... ok
test_examples_listing (tests.test_api.Endpoints.test_examples_listing) ... ok
test_machines (tests.test_api.Endpoints.test_machines) ... ok
test_motif_library (tests.test_api.Endpoints.test_motif_library) ... ok
test_rna_and_advanced (tests.test_api.Endpoints.test_rna_and_advanced) ... ok
test_run_validate_convert_minimize (tests.test_api.Endpoints.test_run_validate_convert_minimize) ... ok
test_crud (tests.test_api.History.test_crud) ... ok
test_body_too_large (tests.test_api.Malformed.test_body_too_large) ... ok
test_invalid_json (tests.test_api.Malformed.test_invalid_json) ... ok
test_schema_violation (tests.test_api.Malformed.test_schema_violation) ... ok
test_semantic_error_has_field (tests.test_api.Malformed.test_semantic_error_has_field) ... ok
test_semantic_too_large (tests.test_api.Malformed.test_semantic_too_large) ... ok
test_wrong_content_type (tests.test_api.Malformed.test_wrong_content_type) ... ok
test_fasta_upload (tests.test_api.Upload.test_fasta_upload) ... ok
test_rejections (tests.test_api.Upload.test_rejections) ... ok
test_complement (tests.test_automata_engine.Closure.test_complement) ... ok
test_needs_b (tests.test_automata_engine.Closure.test_needs_b) ... ok
test_operations_against_reference (tests.test_automata_engine.Closure.test_operations_against_reference) ... ok
test_run_consistency (tests.test_automata_engine.Closure.test_run_consistency) ... ok
test_eps_elimination_requires_nfa (tests.test_automata_engine.Conversions.test_eps_elimination_requires_nfa) ... ok
test_random_nfas_preserve_language (tests.test_automata_engine.Conversions.test_random_nfas_preserve_language) ... ok
test_subset_blowup (tests.test_automata_engine.Conversions.test_subset_blowup) ... ok
test_subset_dead_state_option (tests.test_automata_engine.Conversions.test_subset_dead_state_option) ... ok
test_subset_on_dfa_input (tests.test_automata_engine.Conversions.test_subset_on_dfa_input) ... ok
test_against_brute_force (tests.test_automata_engine.Equivalence.test_against_brute_force)
For DFAs with <= 3 states over {A,B}, any difference shows up on a ... ok
test_bounded_test (tests.test_automata_engine.Equivalence.test_bounded_test) ... ok
test_compare (tests.test_automata_engine.Equivalence.test_compare) ... ok
test_counterexample_is_shortest_and_real (tests.test_automata_engine.Equivalence.test_counterexample_is_shortest_and_real) ... ok
test_different_alphabets (tests.test_automata_engine.Equivalence.test_different_alphabets) ... ok
test_equivalent_examples (tests.test_automata_engine.Equivalence.test_equivalent_examples) ... ok
test_examples (tests.test_automata_engine.Minimization.test_examples) ... ok
test_random_dfas_minimal_and_equivalent (tests.test_automata_engine.Minimization.test_random_dfas_minimal_and_equivalent) ... ok
test_requires_dfa (tests.test_automata_engine.Minimization.test_requires_dfa) ... ok
test_label_collisions_are_disambiguated (tests.test_automata_engine.Serialization.test_label_collisions_are_disambiguated) ... ok
test_dfa_trace (tests.test_automata_engine.Traces.test_dfa_trace) ... ok
test_empty_string (tests.test_automata_engine.Traces.test_empty_string) ... ok
test_epsilon_cycle_terminates (tests.test_automata_engine.Traces.test_epsilon_cycle_terminates) ... ok
test_missing_transition_halts (tests.test_automata_engine.Traces.test_missing_transition_halts) ... ok
test_nfa_dies (tests.test_automata_engine.Traces.test_nfa_dies) ... ok
test_nfa_tracks_sets_not_paths (tests.test_automata_engine.Traces.test_nfa_tracks_sets_not_paths) ... ok
test_errors (tests.test_automata_engine.Validation.test_errors) ... ok
test_every_example_is_valid (tests.test_automata_engine.Validation.test_every_example_is_valid) ... ok
test_tokenize (tests.test_automata_engine.Validation.test_tokenize) ... ok
test_valid (tests.test_automata_engine.Validation.test_valid) ... ok
test_known_hairpins (tests.test_bug_fixes.CfgFoldFix.test_known_hairpins) ... ok
test_membership_language_not_empty_anymore (tests.test_bug_fixes.CfgFoldFix.test_membership_language_not_empty_anymore) ... ok
test_optimal_against_brute_force (tests.test_bug_fixes.CfgFoldFix.test_optimal_against_brute_force) ... ok
test_unreachable_states_removed (tests.test_bug_fixes.MinimizationFix.test_unreachable_states_removed) ... ok
test_witness_strings_really_distinguish (tests.test_bug_fixes.MinimizationFix.test_witness_strings_really_distinguish) ... ok
test_different_alphabets (tests.test_bug_fixes.ProductAlphabetFix.test_different_alphabets) ... ok
test_lba_rejects_unbalanced (tests.test_bug_fixes.PseudoknotFix.test_lba_rejects_unbalanced) ... ok
test_same_type_never_crosses (tests.test_bug_fixes.PseudoknotFix.test_same_type_never_crosses) ... ok
test_three_way_crossing_gets_three_types (tests.test_bug_fixes.PseudoknotFix.test_three_way_crossing_gets_three_types) ... ok
test_malformed_patterns_rejected (tests.test_bug_fixes.RegexValidationFix.test_malformed_patterns_rejected) ... ok
test_valid_patterns (tests.test_bug_fixes.RegexValidationFix.test_valid_patterns) ... ok
test_exhaustive_against_definition (tests.test_bug_fixes.TuringMachineFix.test_exhaustive_against_definition) ... ok
test_previously_wrong_examples (tests.test_bug_fixes.TuringMachineFix.test_previously_wrong_examples) ... ok
test_scan_results (tests.test_bug_fixes.TuringMachineFix.test_scan_results) ... ok
test_single_symbol_no_longer_crashes (tests.test_bug_fixes.TuringMachineFix.test_single_symbol_no_longer_crashes) ... ok
test_trace_records_every_transition (tests.test_bug_fixes.TuringMachineFix.test_trace_records_every_transition) ... ok
test_every_page (tests.test_e2e_browser.BrowserSmoke.test_every_page) ... ok
test_imports_resolve (tests.test_frontend_static.FrontendStatic.test_imports_resolve) ... ok
test_index_assets_exist (tests.test_frontend_static.FrontendStatic.test_index_assets_exist) ... ok
test_modules_parse (tests.test_frontend_static.FrontendStatic.test_modules_parse) ... ok
test_no_inner_html (tests.test_frontend_static.FrontendStatic.test_no_inner_html) ... ok
test_routes_have_views (tests.test_frontend_static.FrontendStatic.test_routes_have_views) ... ok
test_fold (tests.test_machines_advanced.Advanced.test_fold) ... ok
test_fold_limits (tests.test_machines_advanced.Advanced.test_fold_limits) ... ok
test_hairpin_scan (tests.test_machines_advanced.Advanced.test_hairpin_scan) ... ok
test_lba (tests.test_machines_advanced.Advanced.test_lba) ... ok
test_pumping (tests.test_machines_advanced.Advanced.test_pumping) ... ok
test_tm (tests.test_machines_advanced.Advanced.test_tm) ... ok
test_conversions_round_trip (tests.test_machines_advanced.Machines.test_conversions_round_trip) ... ok
test_empty_input (tests.test_machines_advanced.Machines.test_empty_input) ... ok
test_examples_match_original_functions (tests.test_machines_advanced.Machines.test_examples_match_original_functions) ... ok
test_invalid_machines (tests.test_machines_advanced.Machines.test_invalid_machines) ... ok
test_every_module_script_runs (tests.test_original_regressions.EntryPoints.test_every_module_script_runs) ... ok
test_main_module1_2_runs_from_any_directory (tests.test_original_regressions.EntryPoints.test_main_module1_2_runs_from_any_directory) ... ok
test_main_py_runs_and_validates (tests.test_original_regressions.EntryPoints.test_main_py_runs_and_validates) ... ok
test_find_orfs_demo (tests.test_original_regressions.OriginalDrafts.test_find_orfs_demo) ... ok
test_find_orfs_matches_reference_scanner (tests.test_original_regressions.OriginalDrafts.test_find_orfs_matches_reference_scanner)
The DFA-driven scanner must give exactly the results of the original ... ok
test_regex_motif_search (tests.test_original_regressions.OriginalDrafts.test_regex_motif_search) ... ok
test_closure_demo_table_unchanged (tests.test_original_regressions.OriginalModule1.test_closure_demo_table_unchanged) ... ok
test_kmp_substring_dfa_is_exact (tests.test_original_regressions.OriginalModule1.test_kmp_substring_dfa_is_exact) ... ok
test_orf_dfa_already_minimal (tests.test_original_regressions.OriginalModule1.test_orf_dfa_already_minimal) ... ok
test_pumping_lemma_all_splits_fail (tests.test_original_regressions.OriginalModule1.test_pumping_lemma_all_splits_fail) ... ok
test_redundant_dfa_minimizes_to_two_states (tests.test_original_regressions.OriginalModule1.test_redundant_dfa_minimizes_to_two_states) ... ok
test_enfa_language (tests.test_original_regressions.OriginalModule2.test_enfa_language) ... ok
test_enfa_nfa_dfa_agree_on_original_98_strings (tests.test_original_regressions.OriginalModule2.test_enfa_nfa_dfa_agree_on_original_98_strings) ... ok
test_transducer_outputs_unchanged (tests.test_original_regressions.OriginalModule2.test_transducer_outputs_unchanged) ... ok
test_counts_and_percentages (tests.test_rna.Composition.test_counts_and_percentages) ... ok
test_incomplete_codons (tests.test_rna.Composition.test_incomplete_codons) ... ok
test_single_base (tests.test_rna.Composition.test_single_base) ... ok
test_custom_motif_errors (tests.test_rna.Features.test_custom_motif_errors) ... ok
test_genetic_code (tests.test_rna.Features.test_genetic_code) ... ok
test_language_properties_come_from_automata (tests.test_rna.Features.test_language_properties_come_from_automata) ... ok
test_motif_pipeline (tests.test_rna.Features.test_motif_pipeline) ... ok
test_orf_min_length_filter (tests.test_rna.Features.test_orf_min_length_filter) ... ok
test_orf_trace (tests.test_rna.Features.test_orf_trace) ... ok
test_orf_without_stop_is_not_reported (tests.test_rna.Features.test_orf_without_stop_is_not_reported) ... ok
test_orfs_and_translation (tests.test_rna.Features.test_orfs_and_translation) ... ok
test_overlapping_and_repeated_motifs (tests.test_rna.Features.test_overlapping_and_repeated_motifs) ... ok
test_start_stop_positions_all_frames (tests.test_rna.Features.test_start_stop_positions_all_frames) ... ok
test_transducers (tests.test_rna.Features.test_transducers) ... ok
test_empty (tests.test_rna.Parsing.test_empty) ... ok
test_fasta_records (tests.test_rna.Parsing.test_fasta_records) ... ok
test_invalid_characters_explained_with_positions (tests.test_rna.Parsing.test_invalid_characters_explained_with_positions) ... ok
test_malformed_fasta (tests.test_rna.Parsing.test_malformed_fasta) ... ok
test_raw_multiline (tests.test_rna.Parsing.test_raw_multiline) ... ok
test_size_limits (tests.test_rna.Parsing.test_size_limits) ... ok
test_t_conversion_and_lowercase (tests.test_rna.Parsing.test_t_conversion_and_lowercase) ... ok

----------------------------------------------------------------------
Ran 114 tests in 14.416s

OK
```
</details>

## Command-line entry points

```
$ python main_module1_2.py
==================================================
RNA SEQUENCE ANALYSIS REPORT
==================================================

Input RNA Sequence:
CCCAUGGCUACGUAAGGGUGACCC

GENE DETECTION
--------------
• Start codon detected (frame 0): Yes
• Codons identified (frame 0): ['CCC', 'AUG', 'GCU', 'ACG', 'UAA', 'GGG', 'UGA', 'CCC']
• Open Reading Frame (DFA scan, frames 0-2): Present
    frame 0: [3:15] AUGGCUACGUAA
• Entire frame-0 sequence is an ORF chain: No
  (syntactic pattern: START ... in-frame STOP; not a gene prediction)

SEQUENCE PROPERTIES
-------------------
• Contains AUG: Yes
• Even length: Yes
• Intersection property: True
• Union property: True
• Complement property: False

AUTOMATON OPTIMIZATION
-----------------------
• Original DFA states: 4
• Minimized DFA states: 2

PATTERN ANALYSIS
----------------
• Alternative start codons detected: Yes
• ε-transitions eliminated: Yes
• Equivalent DFA states generated: 15

RNA TRANSFORMATIONS
-------------------
• Complementary RNA:
GGGUACCGAUGCAUUCCCACUGGG

• Codon Boundary Map:
100100100100100100100100

• Purine/Pyrimidine Encoding:
YYYRYRRYYRYRYRRRRRYRRYYY

FINAL RESULT
------------
RNA analysis completed successfully.
```

## Manual browser verification

Every page was also opened in headless Chromium (Playwright) at 1360 px, 768 px and 390 px, in light and dark themes, and checked for:
no console errors, no page-level horizontal overflow, keyboard stepping in the trace player (→ ← Home End), node dragging with Reset layout,
file upload of a two-record FASTA, reopening an entry from History, and the print-report layout (rendered to PDF).

## Not verified here

- **Windows PowerShell setup** was not executed (the build environment is Linux). The commands in the README are standard `venv`/`pip` usage, and the code has no OS-specific paths (`pathlib` throughout); please run the README steps once before the demo.
- **A clean `pip install -r requirements.txt`** could not be run, because the package index was unreachable from the build environment. The app was tested against the versions listed above.
- **Printing**: the print layout was rendered to PDF in headless Chromium and checked; printing on a physical printer was not tested.
