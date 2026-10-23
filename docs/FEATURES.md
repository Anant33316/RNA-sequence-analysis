# Features

## Implemented and tested

**RNA analysis**
- Paste raw text or FASTA; upload `.fa .fasta .fna .ffn .frn .txt .seq .rna` (≤ 2 MB); multi-record FASTA with record selection
- Validation: empty, malformed FASTA, oversized (> 100,000 nt), and invalid characters with 0-based positions and a reason (IUPAC code, DNA `T`, digit, gap, other)
- Optional T→U conversion; lowercase accepted (both reported as warnings)
- Composition (counts, %, GC/AU), sliding-window GC profile
- Colour-coded, paged sequence viewer with position ruler, codon-boundary marks per frame, jump-to-position, feature overlays
- Start and stop codons in all three frames
- ORFs in all three forward frames, found by the codon-level ORF DFA, with a minimum-length filter, translation (standard code) and a codon-by-codon DFA trace
- Motif library (start, stops, alternative starts, poly(A) hexamer, ARE core, Shine–Dalgarno core, GC run) plus up to 5 custom regex motifs, all overlapping matches; view the Thompson ε-NFA, subset DFA and minimal DFA of any motif
- Whole-sequence membership in the project's languages (KMP DFA, even length, ε-NFA, product, complement), with links to trace them
- Transducer outputs: complement, reverse complement, codon boundaries, RY encoding
- Click any result to highlight it in the sequence; JSON export; printable report; save to history

**Automata**
- DFA/NFA editor (form or JSON), 13 built-in examples, import/export JSON
- Validation: unknown states/symbols, duplicates, ε in a DFA, nondeterminism in a DFA (with the conflicting targets), missing transitions, unreachable states, ε-acceptance
- Generated state diagrams: start arrow, accepting double circles, self-loops, merged parallel labels, curved bidirectional and obstacle-avoiding edges, dashed ε-edges, unreachable states dashed, draggable nodes, SVG download
- Trace player: step, back, play/pause with speed, reset, end, progress, keyboard control, full trace table; NFA active sets and ε-closures; missing-transition halts shown
- ε-elimination and subset construction with per-step explanations and linked highlighting; optional explicit dead state; 2ⁿ bound comparison
- Minimization: unreachable removal, completion, table-filling rounds, partition colouring, pair table with distinguishing strings, before/after tables
- Verification: exhaustive equivalence proof with shortest counterexample (re-verified), bounded testing (labelled evidence), side-by-side traces, state/transition statistics, transition tables

**Platform**
- REST API with consistent errors, request limits, safe uploads, security headers
- Local history in SQLite: list, filter, reopen, delete, clear
- Light/dark/system themes; responsive down to 390 px with no page-level horizontal scroll; skip link; visible focus; reduced-motion support; keyboard-operable tabs and players
- Original CLI programs preserved and runnable from any directory

## Experimental (RNA analyzer's Structure tab, clearly labelled in the UI)
- CFG secondary-structure folding (Nussinov/CYK): maximizes the number of nested pairs, no energy model
- Leftmost derivation and DP-table view
- Turing machine for complementary palindromes (hairpin-stem candidates only); window scanning

## Deliberately not implemented
- Thermodynamic folding or pseudoknot prediction — outside the project's models; would need a real energy model
- Reverse-strand ORF search, splicing, gene prediction — would overstate what a syntactic DFA can claim
- Pushdown-automaton simulator for the CFG — the grammar is parsed by CYK; a PDA view was not built
- Regex → automaton for arbitrary alphabets in the UI — motif regexes are over {A, C, G, U}
- Authentication, cloud deployment, AI-generated commentary — not required for a local teaching tool

## Removed in 2.1.0
- Closure Properties page, Moore & Mealy page, and the Grammars/LBA/Turing Machines page (with their API endpoints). The original algorithm modules and the command-line programs that use them are unchanged; see CHANGELOG.md.
