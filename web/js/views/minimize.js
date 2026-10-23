import { h, clear, fill } from "../dom.js";
import { AutomatonGraph } from "../graph.js";
import { errorBox, examplePicker, transitionTable, loading, stat, workspace, notice } from "../components.js";
import * as api from "../api.js";

export const title = "DFA minimization";

export async function render(root, params) {
  const out = h("div", {});
  const picker = await examplePicker({ filter: (e) => e.type === "DFA", label: "Load a DFA example", onPick: (ex) => run(ex.automaton) });
  root.append(
    h("header", { class: "view-head" }, h("h1", {}, "DFA minimization"),
      h("p", {}, "The project's table-filling algorithm, now with unreachable-state removal. Round 0 separates accepting from non-accepting states; ",
        "round k marks pairs that some symbol sends to a pair marked earlier, so a pair marked in round k is told apart by a string of length k. ",
        "Every marked pair comes with that distinguishing string.")),
    h("div", { class: "row", style: { marginBottom: "12px" } }, picker,
      h("button", { class: "btn ghost", type: "button", onclick: () => {
        const s = workspace.get("current");
        if (s) run(s); else fill(out, notice("info", null, "Nothing in the playground yet."));
      } }, "Use the playground automaton")),
    out);

  async function run(spec) {
    fill(out, loading("Minimizing…"));
    let r;
    try { r = await api.post("/api/automata/minimize", { automaton: spec, save: false }); }
    catch (e) { fill(out, errorBox(e)); return; }
    const beforeHost = h("div", {}), afterHost = h("div", {}), roundHost = h("div", {}), pairHost = h("div", {});
    const roundBtns = h("div", { class: "row" });
    fill(out, 
      h("div", { class: "stats" }, stat("Original states", r.counts.original), stat("Unreachable removed", r.counts.unreachable_removed.length,
        r.counts.unreachable_removed.join(", ") || "none"), stat("Trap state added", r.counts.trap_added.length ? "yes" : "no"),
        stat("Minimized states", r.counts.minimized)),
      h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Preparation"), h("ol", {}, r.preprocessing.map((p) => h("li", {}, p)))),
      h("div", { class: "grid-2" },
        h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Original DFA, coloured by current partition"), beforeHost),
        h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Refinement rounds"), roundBtns, roundHost)),
      h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Pair table"),
        h("p", { class: "small muted" }, "× k: marked distinguishable in round k (hover for the distinguishing string). ≡: never marked, so the two states are equivalent."),
        pairHost),
      h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Minimized DFA"), afterHost,
        h("p", {}, r.merge_explanation), h("p", { class: "small" }, r.summary),
        h("div", { class: "row" },
          h("button", { class: "btn ghost small", type: "button", onclick: () => { workspace.set("A", r.before); workspace.set("B", r.after); location.hash = "#/verify?pair=1"; } }, "Verify original ≡ minimized"),
          h("button", { class: "btn ghost small", type: "button", onclick: () => { workspace.set("current", r.after); location.hash = "#/playground?slot=current"; } }, "Open in playground"))),
      h("section", { class: "panel" }, h("div", { class: "grid-2" },
        h("div", {}, h("h4", {}, "Before"), transitionTable(r.before_table)), h("div", {}, h("h4", {}, "After"), transitionTable(r.after_table)))));

    const before = new AutomatonGraph(beforeHost).setSpec(r.before);
    const removed = new Set(r.counts.unreachable_removed);
    const colour = (partition) => {
      const classes = {};
      partition.forEach((block, i) => block.forEach((q) => { classes[q] = `cls-${i % 8}`; }));
      return classes;
    };
    const after = new AutomatonGraph(afterHost).setSpec(r.after);
    const afterClasses = {};
    r.classes.forEach((c, i) => { afterClasses[c[0]] = `cls-${i % 8}`; });
    after.highlight({ classes: afterClasses });

    const pick = (k) => {
      const rd = r.rounds[k];
      roundBtns.querySelectorAll("button").forEach((b, i) => b.className = i === k ? "btn small" : "btn ghost small");
      before.highlight({ classes: colour(rd.partition), dim: [...removed] });
      fill(roundHost, 
        h("p", { class: "explain" }, rd.explanation),
        h("p", { class: "small" }, "Blocks: ", rd.partition.map((b, i) => h("span", { style: { marginRight: "10px" } },
          h("i", { class: `swatch cls-${i % 8}` }), `{${b.join(", ")}}`))),
        rd.marked.length ? h("div", { class: "table-wrap", style: { maxHeight: "300px" } }, h("table", {},
          h("thead", {}, h("tr", {}, h("th", {}, "Pair"), h("th", {}, "Witness"), h("th", {}, "Why"))),
          h("tbody", {}, rd.marked.map((m) => h("tr", {}, h("td", { class: "mono" }, `(${m.pair.join(", ")})`),
            h("td", { class: "mono" }, m.witness), h("td", { class: "small" }, m.reason))))))
          : h("p", { class: "small muted" }, "No pair was marked in this round."),
        k === r.rounds.length - 1 ? h("p", { class: "small" }, "This is the last round that marked anything; the next round would change nothing, so the partition is final.") : null);
    };
    r.rounds.forEach((rd, k) => roundBtns.append(h("button", { class: "btn ghost small", type: "button", onclick: () => pick(k) }, `Round ${rd.round}`)));
    pick(0);
    pairHost.append(pairTable(r));
  }

  if (params.slot && workspace.get(params.slot)) run(workspace.get(params.slot));
  else { const ex = await api.example("redundant_dfa"); run(ex.automaton); }
}

function pairTable(r) {
  const states = r.table_states;
  if (states.length > 30) return h("p", { class: "muted small" }, `The table has ${states.length * (states.length - 1) / 2} pairs; shown only for up to 30 states.`);
  const cell = new Map(r.pair_table.map((c) => [c.pair.join("\u0000"), c]));
  const get = (a, b) => cell.get(`${a}\u0000${b}`) || cell.get(`${b}\u0000${a}`);
  return h("div", { class: "table-wrap" }, h("table", { class: "ttable", style: { width: "auto" } },
    h("tbody", {}, states.slice(1).map((q, i) => h("tr", {}, h("th", {}, q),
      states.slice(0, i + 1).map((p) => {
        const c = get(p, q);
        return h("td", { class: c.distinguishable ? "" : "good", title: c.distinguishable
          ? `${p} and ${q} are distinguished by '${c.witness}' (round ${c.round})` : `${p} ≡ ${q}` },
        c.distinguishable ? `× ${c.round}` : "≡");
      }))),
    h("tr", {}, h("th", {}, ""), states.slice(0, -1).map((p) => h("th", {}, p))))));
}
