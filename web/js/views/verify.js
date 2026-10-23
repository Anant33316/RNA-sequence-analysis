import { h, fill, word } from "../dom.js";
import { AutomatonGraph } from "../graph.js";
import { errorBox, examplePicker, transitionTable, loading, stat, workspace, TracePlayer, busy, badge } from "../components.js";
import * as api from "../api.js";

export const title = "Verification lab";

export async function render(root, params) {
  const state = { A: null, B: null };
  const hosts = { A: h("div", {}), B: h("div", {}) };
  const out = h("div", {});
  const maxLen = h("input", { type: "number", id: "v-len", min: 0, max: 12, value: 6 });
  const randCount = h("input", { type: "number", id: "v-rand", min: 0, max: 5000, value: 200 });
  const input = h("input", { type: "text", id: "v-in", class: "mono", value: "AAUG", spellcheck: "false" });
  const eqBtn = h("button", { class: "btn", type: "button", onclick: () => equivalence() }, "Prove or refute equivalence");
  const bBtn = h("button", { class: "btn ghost", type: "button", onclick: () => bounded() }, "Run bounded tests");
  const cBtn = h("button", { class: "btn ghost", type: "button", onclick: () => compareRun(input.value) }, "Compare on this input");

  const set = (slot, spec) => {
    state[slot] = spec;
    workspace.set(slot, spec);
    fill(hosts[slot], h("p", { class: "small" }, h("strong", {}, `${slot}: `), `${spec.name || spec.type} (${spec.type}, ${spec.states.length} states)`), h("div", {}));
    new AutomatonGraph(hosts[slot].lastChild, { compact: true }).setSpec(spec);
  };
  const pickerFor = async (slot, def) => h("div", { class: "row" },
    await examplePicker({ label: `Load ${slot}`, selected: def, onPick: (ex) => set(slot, ex.automaton) }),
    h("button", { class: "btn ghost small", type: "button", onclick: () => { const s = workspace.get("current"); if (s) set(slot, s); } }, "Use playground"));

  root.append(
    h("header", { class: "view-head" }, h("h1", {}, "Verification lab"),
      h("p", {}, "Two kinds of evidence, kept apart. The exhaustive check explores the product of both automata and is a proof: it either shows ",
        "the languages are equal or returns the shortest string they disagree on. Bounded testing only samples strings — agreement there is not a proof.")),
    h("div", { class: "grid-2" },
      h("section", { class: "panel" }, await pickerFor("A", "aug_dfa"), hosts.A),
      h("section", { class: "panel" }, await pickerFor("B", "aug_buggy_dfa"), hosts.B)),
    h("section", { class: "panel" },
      h("div", { class: "row" }, eqBtn, badge("proof", "proof")),
      h("div", { class: "inline-fields", style: { marginTop: "14px" } },
        h("div", { class: "field" }, h("label", { for: "v-len" }, "All strings up to length"), maxLen),
        h("div", { class: "field" }, h("label", { for: "v-rand" }, "Random longer strings"), randCount),
        h("div", { class: "row" }, bBtn, badge("evidence only", "evidence"))),
      h("div", { class: "inline-fields", style: { marginTop: "14px" } },
        h("div", { class: "field" }, h("label", { for: "v-in" }, "Input to trace in both"), input), cBtn)),
    out);

  if (params.pair && workspace.get("A") && workspace.get("B")) { set("A", workspace.get("A")); set("B", workspace.get("B")); }
  else {
    set("A", (await api.example("aug_dfa")).automaton);
    set("B", (await api.example("aug_buggy_dfa")).automaton);
  }

  async function equivalence() {
    fill(out, loading("Exploring the product automaton…"));
    try {
      const r = await busy(eqBtn, () => api.post("/api/automata/equivalence", { a: state.A, b: state.B, save: true }));
      const traces = h("div", {});
      fill(out, h("section", { class: "panel" },
        h("div", { class: "row" }, h("h2", { style: { margin: 0 } }, r.equivalent ? "L(A) = L(B)" : "L(A) ≠ L(B)"), badge(r.method, "proof")),
        h("div", { class: "stats", style: { marginTop: "12px" } },
          stat("A as complete DFA", `${r.a_dfa_states} states`), stat("B as complete DFA", `${r.b_dfa_states} states`),
          stat("Product pairs explored", r.explored_pairs)),
        r.equivalent ? h("div", { class: "verdict yes" }, h("span", { class: "verdict-word" }, "Equivalent"),
          h("p", {}, "No reachable pair of states disagrees on acceptance, so no string can distinguish the automata."))
          : h("div", { class: "verdict no" }, h("span", { class: "verdict-word" }, "Not equivalent"),
            h("p", {}, "Shortest counterexample ", h("code", {}, r.counterexample_text), `: accepted by ${r.accepted_by} only. `,
              `Re-running both machines on it confirms: A ${r.verification.a ? "accepts" : "rejects"}, B ${r.verification.b ? "accepts" : "rejects"}.`)),
        h("ol", {}, r.steps.map((s) => h("li", {}, s))),
        r.path ? h("details", { open: true }, h("summary", {}, "Path through the product"), h("div", { class: "table-wrap" }, h("table", {},
          h("thead", {}, h("tr", {}, h("th", {}, "After reading"), h("th", {}, "State of A"), h("th", {}, "State of B"))),
          h("tbody", {}, r.path.map(([p, q], i) => h("tr", {}, h("td", { class: "mono" }, word(r.counterexample.slice(0, i))),
            h("td", { class: "mono" }, p), h("td", { class: "mono" }, q))))))) : null),
        traces);
      if (!r.equivalent) compareRun(r.counterexample, traces);
    } catch (e) { fill(out, errorBox(e)); }
  }

  async function bounded() {
    fill(out, loading("Testing strings…"));
    try {
      const r = await busy(bBtn, () => api.post("/api/automata/bounded-test", { a: state.A, b: state.B,
        max_length: Number(maxLen.value), random_count: Number(randCount.value) }));
      fill(out, h("section", { class: "panel" },
        h("div", { class: "row" }, h("h2", { style: { margin: 0 } }, r.disagreement_found ? "Disagreement found" : "No disagreement found"),
          badge(r.method, "evidence")),
        h("div", { class: "stats", style: { marginTop: "12px" } }, stat("Strings tested", r.tested.toLocaleString()),
          stat("Exhaustive up to length", r.exhaustive_up_to_length, `${r.exhaustive_strings.toLocaleString()} strings`),
          stat("Random strings", r.random_strings, `seed ${r.random_seed}`), stat("Mismatches", r.mismatch_count)),
        h("p", {}, r.explanation),
        r.mismatches.length ? h("div", { class: "table-wrap" }, h("table", {},
          h("thead", {}, h("tr", {}, h("th", {}, "Input"), h("th", {}, "A"), h("th", {}, "B"), h("th", {}, ""))),
          h("tbody", {}, r.mismatches.map((m) => h("tr", {}, h("td", { class: "mono" }, m.input),
            h("td", {}, m.a ? "accepts" : "rejects"), h("td", {}, m.b ? "accepts" : "rejects"),
            h("td", {}, h("button", { class: "btn ghost small", type: "button", onclick: () => { input.value = m.input === "ε" ? "" : m.input; compareRun(input.value); } }, "Trace both"))))))) : null));
    } catch (e) { fill(out, errorBox(e)); }
  }

  async function compareRun(value, host = null) {
    const target = host || out;
    fill(target, loading("Running both automata…"));
    try {
      const r = await api.post("/api/automata/compare", { a: state.A, b: state.B, input: value });
      const ga = h("div", {}), gb = h("div", {}), pa = h("div", {}), pb = h("div", {});
      const s = r.stats;
      fill(target,
        h("section", { class: "panel" }, h("h3", { class: "panel-title" }, `Both automata on `, h("code", {}, word(Array.isArray(value) ? value : (r.runs.a || r.runs.b || { input: [] }).input))),
          h("p", { class: r.runs.agree ? "good" : "bad" }, h("strong", {}, r.runs.agree ? "They agree on this input." : "They disagree on this input.")),
          h("div", { class: "grid-2" },
            h("div", {}, h("h4", {}, "A"), ga, r.runs.a ? pa : h("p", { class: "bad" }, "The input uses a symbol outside A's alphabet: rejected.")),
            h("div", {}, h("h4", {}, "B"), gb, r.runs.b ? pb : h("p", { class: "bad" }, "The input uses a symbol outside B's alphabet: rejected.")))),
        h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Side-by-side comparison"),
          h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, ""), h("th", {}, "A"), h("th", {}, "B"))),
            h("tbody", {}, [["Type", "type"], ["States", "states"], ["Transitions", "transitions"], ["Accepting states", "accepting"]].map(([l, k]) =>
              h("tr", {}, h("th", {}, l), h("td", {}, s.a[k]), h("td", {}, s.b[k])))))),
          h("div", { class: "grid-2", style: { marginTop: "14px" } }, transitionTable(r.a_table), transitionTable(r.b_table))));
      const gA = new AutomatonGraph(ga, { compact: true }).setSpec(r.a);
      const gB = new AutomatonGraph(gb, { compact: true }).setSpec(r.b);
      if (r.runs.a) new TracePlayer(pa, gA).load(r.runs.a);
      if (r.runs.b) new TracePlayer(pb, gB).load(r.runs.b);
    } catch (e) { fill(target, errorBox(e)); }
  }
}
