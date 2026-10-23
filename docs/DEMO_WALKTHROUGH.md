# Demo walkthrough (about 10 minutes)

Start the app before the viva with `python run_app.py --open`, then
use **Theme** in the top right to choose light or dark to suit the projector. Each step
says what to click and what to say.

## 1. Overview: the idea in one screen (1 min)
- The hero DFA is the project's KMP construction for "contains AUG". Type `CCAUGG`, then
  `CCAUCG`. The states light up as each base is read.
- **Say:** "Nothing on screen is drawn by hand. The diagram is generated from the automaton
  definition and the highlights come from the server's execution trace."
- Point at the Chomsky-hierarchy strip: regular → context-free → context-sensitive → TM, each mapped to an RNA problem.

## 2. RNA analyzer (3 min)
- Click the **Invalid input** sample, then **Analyze sequence**. The table lists each bad character
  with its position and the reason (`N` is an IUPAC code, `-` is a gap, …).
- Click **mRNA-like with motifs** → **Analyze**. Walk through the stats, composition bars and GC profile.
- **ORFs tab** → **DFA trace**. Click the `AUG` row and then the `UAA` row: the ORF DFA moves
  `q0 → q1 → q2` (accepting) and the codon is highlighted in the sequence.
- **Say:** "An ORF here is a syntactic pattern recognised by a DFA, not a gene prediction."
- **Motifs tab** → *Show its automata* on the stop-codon motif: regex → Thompson ε-NFA → DFA → minimal DFA.
- **Formal languages tab**: the whole sequence run through the project's DFA, ε-NFA, product and complement.
- **Export JSON**, then **Print report**.

## 3. Automata playground: NFA vs DFA (2 min)
- Load **3rd symbol from the end is G**, input `GGA`, press **Step** three times.
- **Say:** "An NFA keeps a *set* of active states; here {p0, p1} after the first G. It accepts because p3 is in the final set."
- Load **(AU)* with an ε-cycle** and run the empty string: accepted through the ε-closure {p, q, f}.
- Load **exactly AUG (partial DFA)** and run `AUC`: the run halts on the missing transition and the stuck state is outlined in red.

## 4. NFA → DFA (1.5 min)
- **ε-elimination & NFA→DFA**, with the alternative-start ε-NFA preloaded. Click several subsets in
  *Construction steps*. The NFA states inside the subset light up on the left and the new DFA state on the right.
- Load **3rd symbol from the end is G**: 8 DFA states = 2³, the exponential blow-up.

## 5. Minimization (1.5 min)
- **DFA minimization** with the redundant "ends in A" DFA: round 0 colours {q0, q2} and {q1, q3}, giving 4 → 2 states.
- Load **ends in G (with unreachable copies)**. Step 1 removes s2, s3, u9.
- In the pair table, hover a "× k" cell to see its distinguishing string.

## 6. Verification lab: proof vs evidence (1.5 min)
- A = KMP "contains AUG", B = the buggy version. Click **Prove or refute equivalence**.
- **Say:** "This explores the product automaton exhaustively. It found the *shortest* string that separates them, `AAUG`, and re-ran both machines on it to confirm."
- Replay both traces side by side: B forgets that the second `A` can start a new match.
- Run **bounded tests** and point at the "evidence only" label.

## 7. Beyond regular (1 min, labelled experimental)
- In the **RNA analyzer**, open the **Structure (experimental)** tab.
- **Fold with the CFG**: dot-bracket, arc diagram, leftmost derivation. **Say:** "This maximizes pairs; it is not an energy model."
- **Scan for hairpin stems (TM)**: every window is run through the Turing machine; select a hit to highlight it in the sequence.

## Likely viva questions and where to point
| Question | Show |
|---|---|
| How do you know the conversion is correct? | Verification lab: NFA vs its DFA → "equivalent" by exhaustive product search; 104 automated tests |
| Why is GⁿCⁿ not regular? | Run `python module1_dfa/regular_vs_nonregular.py` (pumping-lemma proof) |
| Difference between Moore and Mealy? | RNA analyzer, Transducers tab, and `python module2_nfa/moore_mealy.py`: output on transition (Mealy) vs on state (Moore, n + 1 outputs) |
| What did you fix in your earlier code? | CHANGELOG.md: TM always accepting after one pair, CFG off-by-one, minimization without unreachable removal |
| Are the explanations AI-generated? | No: Learn page, "How explanations are produced", and docs/ARCHITECTURE.md |
