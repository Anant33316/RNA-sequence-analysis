import { h, clear, debounce, prefersReducedMotion, fill } from "../dom.js";
import { AutomatonGraph } from "../graph.js";
import { tape, errorBox } from "../components.js";
import * as api from "../api.js";

export const title = "Overview";

const MODULES = [
  ["rna", "RNA analyzer", "Validate a sequence, then find codons, open reading frames and motifs with automata; export a report."],
  ["playground", "Automata playground", "Build or load a DFA/NFA, then step through its execution with the active states highlighted."],
  ["convert", "ε-elimination & NFA→DFA", "See every ε-closure and every subset the construction creates, and why it accepts."],
  ["minimize", "DFA minimization", "Table-filling, round by round, with a distinguishing string for every marked pair."],
  ["verify", "Verification lab", "Prove two automata equivalent, or get the shortest string they disagree on."],
];

export async function render(root) {
  const input = h("input", { class: "hero-input", type: "text", value: "CCAUGG", maxlength: 40, spellcheck: "false",
    "aria-label": "RNA bases for the live DFA", autocomplete: "off" });
  const graphHost = h("div", {});
  const tapeHost = h("div", { class: "hero-tape" });
  const out = h("div", { class: "hero-out", "aria-live": "polite" });

  root.append(
    h("section", { class: "hero" },
      h("div", {},
        h("h1", {}, "Read RNA the way an automaton does"),
        h("p", { class: "lede" }, "Every result in this lab comes from running a real algorithm, and every step can be explained. ",
          "Type bases below: the four-state DFA built by the project's KMP construction decides whether the start codon AUG occurs."),
        h("label", { class: "label", for: "hero-in" }, "Bases (A, C, G, U)"),
        Object.assign(input, { id: "hero-in" }),
        h("div", { class: "row", style: { marginTop: "12px" } },
          h("a", { class: "btn", href: "#/rna" }, "Analyze a sequence"),
          h("a", { class: "btn ghost", href: "#/playground?example=aug_dfa" }, "Open this DFA in the playground"))),
      h("div", {}, graphHost, tapeHost, out)),
    h("h2", {}, "Where each model sits"),
    h("p", { class: "muted" }, "The Chomsky hierarchy, mapped to the parts of RNA analysis each level can express."),
    h("div", { class: "hierarchy" },
      level("Regular", "DFA, NFA, ε-NFA, regex", ["Codons, start/stop scanning", "Open reading frames", "Motif search", "Transducers (Moore/Mealy)"]),
      level("Context-free", "CFG / pushdown automaton", ["Nested base pairs (stems)", "Not regular: GⁿCⁿ via pumping lemma"]),
      level("Context-sensitive", "LBA-style tape checker", ["Crossing pairs (pseudoknots) — checking a given pairing only"]),
      level("Decidable by TM", "Single-tape Turing machine", ["Complementary palindromes (hairpin stem candidates)"])),
    h("h2", {}, "Modules"),
    h("nav", { class: "module-list", "aria-label": "Modules" },
      MODULES.map(([route, name, text]) => h("a", { href: `#/${route}` }, h("h3", {}, name), h("p", {}, text)))),
  );

  let graph, timer;
  try {
    const ex = await api.example("aug_dfa");
    graph = new AutomatonGraph(graphHost, { compact: true }).setSpec(ex.automaton);
  } catch (e) { fill(graphHost, errorBox(e)); return; }

  const run = debounce(async () => {
    clearTimeout(timer);
    const value = input.value.toUpperCase().replace(/T/g, "U");
    const bad = value.split("").findIndex((c) => !"ACGU".includes(c));
    if (bad >= 0) {
      fill(out, h("p", { class: "bad" }, `'${value[bad]}' at position ${bad} is not a base. Use A, C, G or U.`));
      return;
    }
    let res;
    try { res = await api.post("/api/automata/run", { automaton: graph.spec, input: value }); }
    catch (e) { fill(out, errorBox(e)); return; }
    let k = prefersReducedMotion() ? res.steps.length - 1 : -1;
    const show = () => {
      const st = k >= 0 ? res.steps[k] : null;
      graph.highlight({ active: st ? st.next_active : res.initial_active,
        edges: st && st.exists ? [{ from: st.state, to: st.next }] : [] });
      fill(tapeHost, tape(res.input, k));
      clear(out);
      if (k === res.steps.length - 1) {
        out.append(h("p", { class: res.accepted ? "good" : "bad" }, h("strong", {}, res.accepted ? "Accepted. " : "Rejected. "),
          res.verdict));
      } else if (st) {
        out.append(h("p", { class: "muted" }, st.explanation));
      } else out.append(h("p", { class: "muted" }, res.initial_explanation));
      if (k < res.steps.length - 1) { k++; timer = setTimeout(show, 420); }
    };
    show();
  }, 250);
  input.addEventListener("input", run);
  run();
}

function level(name, machine, items) {
  return h("div", {}, h("h4", {}, name), h("div", { class: "machine" }, machine), h("ul", {}, items.map((i) => h("li", {}, i))));
}
