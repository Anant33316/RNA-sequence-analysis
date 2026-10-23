# Architecture

## Layers

```
 Browser (web/)                      no build step: HTML + CSS + ES-module JavaScript
   views/*.js  ──►  components.js, graph.js (SVG state diagrams), rnaviz.js
        │  fetch JSON
        ▼
 api/app.py   Starlette routes ─ Pydantic schemas (api/schemas.py) ─ SQLite history (api/history.py)
        │  run_in_threadpool
        ▼
 engine/      validation, JSON <-> algorithm objects, deterministic explanations, RNA analysis
        │  plain Python calls
        ▼
 module1_dfa/ module2_nfa/ automata/ grammars/ turing/      ORIGINAL algorithms (single source of truth)
```

Responsibilities are strictly one-directional: the algorithm modules know nothing about
JSON, HTTP or the UI; the engine never re-implements an algorithm; the API only
validates, dispatches and maps errors; the frontend only draws what the API returns.

## The explanation pipeline

1. **Algorithm → structured trace.** The original functions gained an optional
   `trace` argument (or a `run_trace` method) and record what they actually do:
   * `DFA.run_trace`: position, state, symbol, next state, whether the transition exists.
   * `NFA.run_trace`: active set, each state's moves, union, ε-edges followed in the closure, next set.
   * `subset_construction(trace=)`: start closure, each processed subset (FIFO), per-symbol move, ε-edges, result, new/existing, accepting reason.
   * `eliminate_epsilon(trace=)`: closure of each state, inherited accept, inherited moves and their sources.
   * `minimize(trace=)`: unreachable states removed, trap added, round-by-round marked pairs with symbol, successor pair and **witness string**, partition after each round.
   * `product_construction(trace=)` / `complement(trace=)`: each product pair with both component acceptance bits.
   * `TuringMachine.trace`: (state, read, write, move, next state, tape) per step; `LBA.trace`: one record per pass.
   * `find_orfs(trace=)`: codon, class, DFA state before/after, scanner action.
2. **Engine → text.** `engine/simulate.py`, `conversions.py`, `minimize.py`,
   `equivalence.py`, `advanced.py` convert state objects to labels and write sentences
   from the trace fields only (e.g. "δ(q2, C) is NOT defined (partial DFA), so the run halts").
3. **Frontend → visual.** `graph.js` draws the automaton from its specification; the trace
   player highlights `next_active` states and the edges named in the step record.

No language model is used anywhere. If one were added, it should only summarise these
verified traces and be visibly separated from them.

## Verification design

* `engine/equivalence.check_equivalence`: both automata → complete DFAs over the union
  alphabet (NFAs via subset construction) → BFS over reachable product pairs. A pair with
  exactly one accepting component is a witness; parent pointers give the **shortest**
  counterexample, which is then re-run on both original machines. No witness ⇒ the
  symmetric difference is empty ⇒ proof of equivalence.
* `bounded_test` enumerates every string up to a bound plus seeded random strings and is
  always labelled "evidence, not proof".

## Key decisions

| Decision | Reason |
|---|---|
| **Starlette + Pydantic + uvicorn** instead of FastAPI | The package registry was unreachable in the build environment, so FastAPI could not be installed or tested; Starlette (FastAPI's foundation), Pydantic and uvicorn were available, so the API could actually be run and tested. Porting to FastAPI later is mechanical: the handlers are plain functions over Pydantic models. |
| **No-build frontend** (ES modules, own SVG renderer) instead of React + TypeScript + a graph library | npm was unreachable, so no framework or graph library could be installed. A no-build frontend also means `pip install` is the only setup step on Windows, and the app works offline during a viva. The renderer is small (`graph.js`) and draws only from real data. |
| **unittest** test suite (pytest-compatible) | Runs with only the standard library; `pytest` also collects it. API tests use a tiny in-process ASGI client (`tests/asgi_client.py`) because Starlette's TestClient needs `httpx`. |
| Original files kept in place, made into packages with an import fallback | `python module1_dfa/minimization.py` still works *and* `from module1_dfa.minimization import minimize` works; no duplicate class identities. |
| 0-based positions everywhere | Matches the original code and the automaton input positions; the UI states "0-based" wherever positions appear. |
| SQLite via the standard library | Optional local history with no extra dependency; file is git-ignored. |

## API conventions

* JSON in, JSON out; `Content-Type: application/json` required (415 otherwise).
* Errors: `{"error": {"code", "message", "field", "details?"}}`
  * 400 `invalid_input` / `invalid_json` / `empty` / `malformed` / `unsupported_file` — with a `field` path such as `automaton.transitions[3].to`
  * 404 `not_found`, 405 `method_not_allowed`, 413 `too_large` (body > 3 MB, upload > 2 MB, or an algorithm size limit), 415, 422 `validation_error` (Pydantic, with `details`)
  * 500 `internal_error` — logged, never turned into a fake success
* Uploads: extension allow-list, 2 MB cap, NUL-byte and UTF-8 checks; content is parsed in memory and never written to disk.
* Security headers: CSP (`default-src 'self'`), `nosniff`, `no-referrer`; API responses `no-store`. The server binds to 127.0.0.1 by default.
* All DOM is built with `textContent` (a test forbids `innerHTML` assignments), so file contents and state names cannot inject markup.

## Size limits

| Item | Limit | Why |
|---|---|---|
| RNA sequence | 100,000 nt | analysis takes ≈0.6 s at the limit |
| CFG folding | 200 nt | O(n³) dynamic program |
| Hairpin scan | 1,000 nt | each window's TM run is O(n²) |
| Automaton | 200 states, 64 symbols, 5,000 transitions | keeps diagrams and product constructions responsive |
| Step-by-step input | 5,000 symbols | trace size |
| Bounded testing | 60,000 strings | response time |
