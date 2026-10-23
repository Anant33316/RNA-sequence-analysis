import { h, fill } from "../dom.js";
import { errorBox, loading, badge, workspace, toast } from "../components.js";
import * as api from "../api.js";

export const title = "History";

const KINDS = { "": "All", rna: "RNA analyses", equivalence: "Equivalence checks", minimize: "Minimizations",
  subset: "Subset constructions", run: "Automaton runs", fold: "CFG folds" };

export async function render(root) {
  const kind = h("select", { "aria-label": "Filter by kind" }, Object.entries(KINDS).map(([v, l]) => h("option", { value: v }, l)));
  const list = h("div", {});
  const clearBtn = h("button", { class: "btn danger", type: "button" }, "Clear history");
  root.append(
    h("header", { class: "view-head" }, h("h1", {}, "History"),
      h("p", {}, "Analyses saved on this computer in a local SQLite file (data/history.db). Nothing leaves your machine. ",
        "RNA analyses are saved when “Save to history” is ticked; equivalence checks are always saved.")),
    h("div", { class: "row", style: { marginBottom: "12px" } }, kind, clearBtn),
    list);

  kind.addEventListener("change", load);
  clearBtn.addEventListener("click", async () => {
    if (!confirm("Delete every saved entry? This cannot be undone.")) return;
    try { const r = await api.del("/api/history"); toast(`Deleted ${r.deleted} entr${r.deleted === 1 ? "y" : "ies"}.`); load(); }
    catch (e) { fill(list, errorBox(e)); }
  });

  async function load() {
    fill(list, loading("Loading…"));
    try {
      const { entries } = await api.get(`/api/history?limit=200${kind.value ? `&kind=${kind.value}` : ""}`);
      if (!entries.length) {
        fill(list, h("div", { class: "panel flat" }, h("p", { style: { margin: 0 } }, "Nothing saved yet. ",
          h("a", { href: "#/rna" }, "Analyze a sequence"), " or ", h("a", { href: "#/verify" }, "check two automata for equivalence"), " to start a history.")));
        return;
      }
      fill(list, h("section", { class: "panel" }, entries.map(item)));
    } catch (e) { fill(list, errorBox(e)); }
  }

  function item(e) {
    const summary = Object.entries(e.summary || {}).filter(([, v]) => v !== null && v !== undefined)
      .map(([k, v]) => `${k.replace(/_/g, " ")}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(" · ");
    return h("div", { class: "history-item" },
      h("div", {}, h("h4", {}, e.title), h("div", { class: "small muted" }, badge(e.kind), " ", new Date(e.created_at).toLocaleString()),
        summary ? h("div", { class: "small" }, summary) : null),
      h("div", { class: "row" },
        h("button", { class: "btn ghost small", type: "button", onclick: () => open(e) }, "Open"),
        h("button", { class: "btn ghost small danger", type: "button", onclick: async () => {
          try { await api.del(`/api/history/${e.id}`); toast("Entry deleted."); load(); } catch (err) { toast(err.message, "error"); }
        } }, "Delete")));
  }

  async function open(e) {
    if (e.kind === "rna") { location.hash = `#/rna?history=${e.id}`; return; }
    try {
      const full = await api.get(`/api/history/${e.id}`);
      const p = full.payload;
      if (e.kind === "equivalence") { workspace.set("A", p.a); if (p.b) workspace.set("B", p.b); location.hash = "#/verify?pair=1"; }
      else if (e.kind === "fold") location.hash = "#/rna";
      else { workspace.set("current", p.automaton); location.hash = `#/${e.kind === "minimize" ? "minimize" : e.kind === "subset" ? "convert" : "playground"}?slot=current`; }
    } catch (err) { toast(err.message, "error"); }
  }

  load();
}
