"""
Engine layer for the web application.

The ORIGINAL algorithm modules (module1_dfa, module2_nfa, automata,
grammars, turing) stay the single source of truth for every algorithm.
This package only:

  * converts between JSON specifications and those algorithm objects,
  * validates user input,
  * calls the original algorithms (which emit structured traces),
  * turns traces into deterministic, human-readable explanations.

Nothing here fabricates results: every number, state and verdict shown in
the UI is produced by running an algorithm.
"""
