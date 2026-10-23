import { h, clear, append, fill } from "../dom.js";
import { AutomatonGraph } from "../graph.js";
import { errorBox, examplePicker, transitionTable, tabs, loading, stat, workspace, notice } from "../components.js";
import * as api from "../api.js";

export const title = "ε-elimination & NFA→DFA";

export async function render(root, params) {
  const sourceHost = h("div", {});
  const resultHost = h("div", {});
  let source = null;
  let mode = params.mode || "subset";

  const picker = await examplePicker({ filter: (e) => e.type === "NFA", label: "Load an NFA example",
    onPick: (ex) => setSource(ex.automaton) });
  const fromPg = h("button", { class: "btn ghost", type: "button", onclick: () => {
    const s = workspace.get("current");
    if (s) setSource(s); else fill(resultHost, notice("info", null, "Nothing in the playground yet. Build or load an automaton there first."));
  } }, "Use the playground automaton");
  const deadCb = h("input", { type: "checkbox", checked: true });
  deadCb.addEventListener("change", () => source && run());

  root.append(
    h("header", { class: "view-head" }, h("h1", {}, "ε-elimination and NFA → DFA"),
      h("p", {}, "Both constructions are executed by the project's Module 2 code, which records every ε-closure and every subset. ",
        "Step through them below; the diagrams highlight what each step touches.")),
    h("div", { class: "row", style: { marginBottom: "12px" } }, picker, fromPg),
    sourceHost,
    tabs([
      { id: "subset", label: "Subset construction (NFA → DFA)", render: () => h("div", {},
        h("label", { class: "check small" }, deadCb, "Include the empty set ∅ as an explicit dead state (makes the DFA complete)")) },
      { id: "eps", label: "ε-elimination (ε-NFA → NFA)", render: () => h("p", { class: "small muted" },
        "Each state inherits the moves of every state in its ε-closure; it becomes accepting if its closure contains an accepting state.") },
    ], { initial: mode, onChange: (id) => { mode = id; if (source) run(); } }).el,
    resultHost);

  async function setSource(spec) {
    source = spec;
    fill(sourceHost, h("section", { class: "panel" }, h("h3", { class: "panel-title" }, `Input: ${spec.name || spec.type}`),
      h("div", { id: "src-graph" })));
    run();
  }

  async function run() {
    fill(resultHost, loading());
    try {
      if (mode === "subset") {
        const r = await api.post("/api/automata/subset", { automaton: source, include_dead_state: deadCb.checked });
        showSubset(r);
      } else {
        const r = await api.post("/api/automata/epsilon-eliminate", { automaton: source });
        showEps(r);
      }
    } catch (e) { fill(resultHost, errorBox(e)); }
  }

  function showSubset(r) {
    const nfaGraph = new AutomatonGraph(sourceHost.querySelector("#src-graph"), { compact: true }).setSpec(r.nfa);
    const dfaHost = h("div", {});
    const stepHost = h("div", {});
    const list = h("ol", { class: "steps-list" });
    fill(resultHost, 
      h("div", { class: "stats" }, stat("NFA states", r.counts.nfa_states), stat("DFA states", r.counts.dfa_states),
        r.counts.possible_subsets ? stat("Possible subsets", r.counts.possible_subsets.toLocaleString(), "2ⁿ upper bound") : null),
      h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Resulting DFA"), dfaHost,
        h("p", { class: "small" }, r.summary),
        h("div", { class: "row" },
          h("button", { class: "btn ghost small", type: "button", onclick: () => { workspace.set("current", r.dfa); location.hash = "#/playground?slot=current"; } }, "Open DFA in playground"),
          h("button", { class: "btn ghost small", type: "button", onclick: () => { workspace.set("A", r.nfa); workspace.set("B", r.dfa); location.hash = "#/verify?pair=1"; } }, "Verify NFA ≡ DFA"),
          h("button", { class: "btn ghost small", type: "button", onclick: () => { workspace.set("current", r.dfa); location.hash = "#/minimize?slot=current"; } }, "Minimize this DFA"))),
      h("div", { class: "grid-2" },
        h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Construction steps"),
          h("p", { class: "explain" }, r.start_explanation), list),
        h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Selected step"), stepHost)),
      h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Transition tables"),
        h("div", { class: "grid-2" }, h("div", {}, h("h4", {}, "NFA"), transitionTable(r.nfa_table)),
          h("div", {}, h("h4", {}, "DFA (each state is a set of NFA states)"), transitionTable(r.dfa_table)))));
    const dfaGraph = new AutomatonGraph(dfaHost).setSpec(r.dfa);
    const items = r.steps.map((st, i) => {
      const b = h("button", { class: "linkish", type: "button", onclick: () => pick(i) },
        `${st.state} = {${st.subset.join(", ")}}${st.accepting ? " (accepting)" : ""}`);
      const li = h("li", {}, b);
      list.append(li);
      return li;
    });
    function pick(i) {
      const st = r.steps[i];
      items.forEach((li, k) => li.classList.toggle("current", k === i));
      nfaGraph.highlight({ active: st.subset });
      dfaGraph.highlight({ active: [st.state], edges: st.rows.filter((x) => x.target).map((x) => ({ from: st.state, to: x.target })) });
      fill(stepHost, 
        h("p", { class: "explain" }, st.explanation),
        h("div", { class: "table-wrap" }, h("table", {},
          h("thead", {}, h("tr", {}, h("th", {}, "Symbol"), h("th", {}, "move(S, a)"), h("th", {}, "ε-closure"), h("th", {}, "DFA state"), h("th", {}, ""))),
          h("tbody", {}, st.rows.map((x) => h("tr", {}, h("td", { class: "mono" }, x.symbol),
            h("td", { class: "mono" }, `{${x.move.join(", ")}}`), h("td", { class: "mono" }, x.result.length ? `{${x.result.join(", ")}}` : "∅"),
            h("td", { class: "mono" }, x.target || "—"), h("td", {}, x.status)))))),
        h("div", { class: "row" },
          h("button", { class: "btn ghost small", type: "button", disabled: i === 0, onclick: () => pick(i - 1) }, "Previous subset"),
          h("button", { class: "btn small", type: "button", disabled: i === r.steps.length - 1, onclick: () => pick(i + 1) }, "Next subset")));
    }
    pick(0);
  }

  function showEps(r) {
    new AutomatonGraph(sourceHost.querySelector("#src-graph"), { compact: true }).setSpec(r.before);
    const afterHost = h("div", {});
    fill(resultHost, 
      h("div", { class: "stats" }, stat("States", `${r.counts.states_before} → ${r.counts.states_after}`),
        stat("Transitions", `${r.counts.transitions_before} → ${r.counts.transitions_after}`), stat("ε-transitions removed", r.counts.epsilon_removed)),
      h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "NFA without ε-transitions"), afterHost, h("p", { class: "small" }, r.summary),
        h("button", { class: "btn ghost small", type: "button", onclick: () => { workspace.set("A", r.before); workspace.set("B", r.after); location.hash = "#/verify?pair=1"; } }, "Verify ε-NFA ≡ NFA")),
      h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Per-state derivation"),
        h("div", { class: "table-wrap" }, h("table", {},
          h("thead", {}, h("tr", {}, h("th", {}, "State"), h("th", {}, "ε-closure"), h("th", {}, "Accepting?"), h("th", {}, "Explanation"))),
          h("tbody", {}, r.steps.map((st) => h("tr", {}, h("td", { class: "mono" }, st.state), h("td", { class: "mono" }, `{${st.closure.join(", ")}}`),
            h("td", {}, st.becomes_accepting ? "yes" : "no"), h("td", { class: "small" }, st.explanation))))))),
      h("section", { class: "panel" }, h("div", { class: "grid-2" },
        h("div", {}, h("h4", {}, "Before"), transitionTable(r.before_table)), h("div", {}, h("h4", {}, "After"), transitionTable(r.after_table)))));
    new AutomatonGraph(afterHost).setSpec(r.after);
  }

  if (params.slot && workspace.get(params.slot)) setSource(workspace.get(params.slot));
  else { const ex = await api.example("altstart_enfa"); setSource(ex.automaton); }
}
