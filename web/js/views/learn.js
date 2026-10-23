import { h } from "../dom.js";

export const title = "Learn & docs";

const sec = (t, ...c) => [h("h2", {}, t), ...c];
const p = (...c) => h("p", {}, ...c);
const ul = (...items) => h("ul", {}, items.map((i) => h("li", {}, i)));

export async function render(root) {
  root.append(h("article", { class: "prose" },
    h("h1", {}, "Learn & docs"),
    h("p", { class: "lede" }, "How the lab works, what each model can and cannot tell you, and how the explanations are produced."),

    ...sec("How explanations are produced",
      p("Explanations are never guessed. Each algorithm in the original modules records a structured trace while it runs: the DFA records state, ",
        "symbol and next state; the NFA records the active set, each state's moves and the ε-edges followed; subset construction records every ",
        "subset and the move/closure that produced it; minimization records each marked pair with the symbol and the earlier pair that justify it."),
      p("A deterministic layer (engine/ in the code) turns those records into sentences that name the actual states, positions and values. ",
        "The diagrams are drawn from the automaton definition, and their highlights come from the same trace.")),

    ...sec("Finite automata",
      ul(h("span", {}, h("strong", {}, "DFA"), " — exactly one move per state and symbol. A missing move (a partial DFA) rejects: formally it goes to an implicit dead state."),
        h("span", {}, h("strong", {}, "NFA"), " — any number of moves, including ε-moves that read nothing. The machine is simulated by tracking the SET of states it could be in; it accepts if any path accepts."),
        h("span", {}, h("strong", {}, "ε-closure"), " — all states reachable using ε-moves only. ε-cycles are fine: each state is visited once."),
        h("span", {}, h("strong", {}, "Subset construction"), " — each DFA state is a set of NFA states. Only subsets reachable from the start closure are built, so the result is usually far below 2ⁿ (see the “3rd symbol from the end is G” example for a case that needs all 8 = 2³)."),
        h("span", {}, h("strong", {}, "Minimization"), " — unreachable states are removed, the DFA is completed with a trap state if needed, and table-filling marks distinguishable pairs. Unmarked pairs merge. The result is the unique minimal complete DFA."))),

    ...sec("Proof versus evidence",
      p("The verification lab's equivalence check builds the product of both complete DFAs and searches every reachable pair. If no pair has exactly one ",
        "accepting component, the symmetric difference is empty and the languages are equal: that is a proof. Otherwise the breadth-first search returns ",
        "the SHORTEST distinguishing string, which is re-run on both machines as a check."),
      p("Bounded testing runs every string up to a length plus seeded random strings. Finding a disagreement disproves equivalence; finding none proves nothing.")),

    ...sec("What the RNA results mean",
      ul("Validation accepts A, C, G, U (T optionally read as U). Invalid characters are reported with 0-based positions, ignoring whitespace.",
        "An ORF is a syntactic pattern: AUG followed by an in-frame stop codon, found by the codon-level ORF DFA in each forward frame. It is not a gene prediction; no reverse-strand or splicing analysis is done.",
        "Motifs are regular expressions compiled by the project's own regex → ε-NFA → DFA pipeline. All overlapping matches are reported; a match is not a functional annotation.",
        "The complement, codon-boundary and purine/pyrimidine outputs come from the original Mealy and Moore machines.")),

    ...sec("Beyond regular — experimental",
      ul("CFG folding maximizes the number of nested base pairs (Nussinov = CYK on the structure grammar). It ignores energies, so it is not a structure predictor.",
        "The Turing machine decides complementary palindromes; such a string is only a hairpin stem candidate.")),

    ...sec("Limits",
      ul("RNA analysis: up to 100,000 nt (uploads up to 2 MB).", "CFG folding: up to 200 nt (O(n³)).", "Hairpin scans: up to 1,000 nt.",
        "Automata: up to 200 states, 64 symbols and 5,000 transitions; step-by-step runs up to 5,000 symbols.", "Request bodies: 3 MB.")),

    ...sec("Keyboard",
      ul(h("span", {}, "In a trace player (focus it first): ", h("kbd", {}, "→"), " step, ", h("kbd", {}, "←"), " back, ", h("kbd", {}, "Space"), " play/pause, ",
        h("kbd", {}, "Home"), " / ", h("kbd", {}, "End"), " jump."), h("span", {}, "In tab bars: ", h("kbd", {}, "←"), " ", h("kbd", {}, "→"), " switch tabs."),
        h("span", {}, h("kbd", {}, "Esc"), " closes the navigation drawer on small screens."))),

    ...sec("REST API",
      p("Every screen uses the same JSON API, served by the app at /api. Errors share one shape: ", h("code", {}, '{"error": {"code", "message", "field"}}'), "."),
      h("div", { class: "table-wrap" }, h("table", {}, h("tbody", {}, [
        ["GET", "/api/health", "server status"], ["GET", "/api/examples[/{id}]", "built-in automata"],
        ["POST", "/api/automata/validate", "checks + transition table"], ["POST", "/api/automata/run", "step-by-step trace"],
        ["POST", "/api/automata/epsilon-eliminate", "ε-NFA → NFA"], ["POST", "/api/automata/subset", "NFA → DFA"],
        ["POST", "/api/automata/minimize", "table-filling"],
        ["POST", "/api/automata/equivalence", "exhaustive proof + counterexample"], ["POST", "/api/automata/bounded-test", "sampling"],
        ["POST", "/api/automata/compare", "side-by-side runs"],
        ["POST", "/api/rna/analyze | /upload | /orf-trace", "sequence analysis"], ["POST", "/api/motif/compile", "regex pipeline"],
        ["POST", "/api/advanced/fold | hairpins", "experimental models"], ["GET/DELETE", "/api/history[/{id}]", "saved analyses"],
      ].map(([m, path, d]) => h("tr", {}, h("td", { class: "mono" }, m), h("td", { class: "mono" }, path), h("td", {}, d))))))),
  ));
}
