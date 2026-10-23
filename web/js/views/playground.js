import { h, clear, append, downloadJSON, fill } from "../dom.js";
import { AutomatonGraph } from "../graph.js";
import { AutomatonEditor, TracePlayer, examplePicker, transitionTable, errorBox, busy, notice, workspace, toast, badge } from "../components.js";
import * as api from "../api.js";

export const title = "Automata playground";

const BLANK = { type: "NFA", name: "my automaton", states: ["q0", "q1"], alphabet: ["A", "C", "G", "U"], start: "q0",
  accept: ["q1"], transitions: [{ from: "q0", symbol: "A", to: "q1" }] };

export async function render(root, params) {
  const editorHost = h("div", {});
  const graphHost = h("div", {});
  const factsHost = h("div", {});
  const tableHost = h("div", {});
  const playerHost = h("div", {});
  const runMsg = h("div", {});
  const samples = h("div", { class: "row small" });
  const input = h("input", { type: "text", id: "pg-input", class: "mono", spellcheck: "false", autocomplete: "off",
    placeholder: "e.g. CCAUGG  (or START SENSE STOP for codon alphabets)" });
  const runBtn = h("button", { class: "btn", type: "submit" }, "Run");
  const applyBtn = h("button", { class: "btn", type: "button" }, "Apply changes");

  const picker = await examplePicker({ onPick: (ex) => load(ex.automaton, ex.sample_inputs), selected: params.example || "" });

  root.append(
    h("header", { class: "view-head" },
      h("h1", {}, "Automata playground"),
      h("p", {}, "Define a DFA or NFA, then run it on an input one symbol at a time. The diagram is drawn from your definition; ",
        "the highlighted states and edges come from the server's execution trace. For an NFA the whole set of active states is shown, ",
        "because an NFA follows every possible path at once.")),
    h("div", { class: "row", style: { marginBottom: "14px" } }, picker,
      h("button", { class: "btn ghost", type: "button", onclick: () => load(BLANK, []) }, "Start blank"),
      h("span", { class: "muted small", style: { marginLeft: "auto" } }, "Send this automaton to:"),
      sendBtn("Conversions", "convert"), sendBtn("Minimization", "minimize"),
      sendBtn("Verification (A)", "verify", "A"), sendBtn("Verification (B)", "verify", "B"),
      h("button", { class: "btn ghost small", type: "button", onclick: () => { try { downloadJSON("automaton.json", editor.getSpec()); } catch (e) { toast(e.message, "error"); } } }, "Export JSON")),
    h("div", { class: "split" },
      h("div", {},
        h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Definition"), editorHost,
          h("div", { class: "row", style: { marginTop: "12px" } }, applyBtn)),
        factsHost),
      h("div", {},
        h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "State diagram"), graphHost),
        h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Run an input"),
          h("form", { class: "row", onsubmit: (e) => { e.preventDefault(); runInput(); } },
            h("label", { class: "label", for: "pg-input" }, "Input"), h("div", { style: { flex: "1 1 220px" } }, input), runBtn),
          samples, runMsg, playerHost),
        h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Transition table"), tableHost))),
  );

  const editor = new AutomatonEditor(editorHost);
  const graph = new AutomatonGraph(graphHost, { height: 240 });
  let player = null;
  let current = null;

  function sendBtn(label, route, slot = "current") {
    return h("button", { class: "btn ghost small", type: "button", onclick: () => {
      if (!current) { toast("Apply a valid automaton first.", "error"); return; }
      workspace.set(slot, current);
      location.hash = `#/${route}?slot=${slot}`;
    } }, label);
  }

  async function load(spec, inputs) {
    editor.setSpec(spec);
    clear(samples);
    if (inputs && inputs.length) {
      append(samples, h("span", { class: "muted" }, "Try:"),
        inputs.map((x) => h("button", { class: "btn ghost small", type: "button", onclick: () => { input.value = x; runInput(); } },
          x === "" ? "ε (empty)" : x.length > 24 ? x.slice(0, 22) + "…" : x)));
      input.value = inputs[0];
    }
    await apply();
    if (inputs && inputs.length) runInput();
  }

  async function apply() {
    let spec;
    try { spec = editor.getSpec(); }
    catch (e) { fill(factsHost, errorBox(e)); return false; }
    try {
      const res = await busy(applyBtn, () => api.post("/api/automata/validate", { automaton: spec }));
      current = res.automaton;
      workspace.set("current", current);
      graph.setSpec(current);
      fill(tableHost, transitionTable(res.table));
      clear(playerHost); clear(runMsg);
      player = null;
      renderFacts(res.facts);
      return true;
    } catch (e) {
      fill(factsHost, errorBox(e));
      return false;
    }
  }
  applyBtn.addEventListener("click", apply);

  function renderFacts(f) {
    fill(factsHost, h("section", { class: "panel flat" },
      h("h3", { class: "panel-title" }, "Checks"),
      h("div", { class: "row" }, badge(f.kind), badge(`${f.state_count} states`), badge(`${f.transition_count} transitions`),
        badge(`|Σ| = ${f.alphabet_size}`), f.kind === "DFA" ? badge(f.complete ? "complete" : "partial") : null,
        badge(f.accepts_empty_string ? "accepts ε" : "rejects ε")),
      f.notes.length ? h("ul", { class: "small", style: { marginBottom: 0 } }, f.notes.map((n) => h("li", {}, n)))
        : h("p", { class: "small muted", style: { margin: "8px 0 0" } }, "Valid. Every state is reachable and no warnings apply.")));
  }

  async function runInput() {
    if (!current && !(await apply())) return;
    clear(runMsg);
    try {
      const res = await busy(runBtn, () => api.post("/api/automata/run", { automaton: current, input: input.value }));
      if (!player) player = new TracePlayer(playerHost, graph);
      player.load(res);
      player.root.focus({ preventScroll: true });
    } catch (e) { fill(runMsg, errorBox(e)); }
  }

  if (params.slot && workspace.get(params.slot)) await load(workspace.get(params.slot), []);
  else if (params.example) {
    try {
      const ex = await api.example(params.example);
      const inputs = params.input !== undefined ? [params.input, ...ex.sample_inputs] : ex.sample_inputs;
      await load(ex.automaton, inputs);
    } catch (e) { fill(factsHost, errorBox(e)); }
  }
  else if (workspace.get("current")) {
    await load(workspace.get("current"), []);
    runMsg.append(notice("info", null, "Restored the automaton you were last working on."));
  } else {
    const ex = await api.example("aug_dfa");
    await load(ex.automaton, ex.sample_inputs);
  }
}
