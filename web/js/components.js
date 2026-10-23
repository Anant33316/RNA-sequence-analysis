// Reusable UI pieces shared by the views.

import { h, clear, fmtSet, word, store, prefersReducedMotion, fill } from "./dom.js";
import * as api from "./api.js";

// ------------------------------------------------------------------ feedback

export function errorBox(err) {
  const field = err && err.field ? h("div", { class: "err-field" }, "Where: ", h("code", {}, err.field)) : null;
  const details = err && err.details && err.details.length > 1
    ? h("ul", { class: "err-details" }, err.details.slice(0, 6).map((d) => h("li", {}, h("code", {}, d.loc), " ", d.message)))
    : null;
  return h("div", { class: "alert error", role: "alert" },
    h("strong", {}, err && err.status === 0 ? "Server unreachable" : "Couldn't complete that"),
    h("p", {}, (err && err.message) || String(err)), field, details);
}

export function showError(container, err) {
  fill(container, errorBox(err));
}

export function notice(kind, title, text) {
  return h("div", { class: `alert ${kind}`, role: kind === "error" ? "alert" : "status" },
    title ? h("strong", {}, title) : null, text ? h("p", {}, text) : null);
}

let toastHost;
export function toast(message, kind = "ok") {
  toastHost ||= document.getElementById("toasts");
  const t = h("div", { class: `toast ${kind}`, role: "status" }, message);
  toastHost.append(t);
  setTimeout(() => t.classList.add("leaving"), 2600);
  setTimeout(() => t.remove(), 3100);
}

export async function busy(button, fn) {
  const label = button.textContent;
  button.disabled = true;
  button.classList.add("loading");
  button.setAttribute("aria-busy", "true");
  try { return await fn(); }
  finally {
    button.disabled = false;
    button.classList.remove("loading");
    button.removeAttribute("aria-busy");
    button.textContent = label;
  }
}

export function loading(text = "Running…") {
  return h("div", { class: "loading-row", role: "status" }, h("span", { class: "spinner", "aria-hidden": "true" }), text);
}

export function verdict(accepted, text) {
  return h("div", { class: "verdict " + (accepted ? "yes" : "no"), role: "status" },
    h("span", { class: "verdict-word" }, accepted ? "Accepted" : "Rejected"),
    h("p", {}, text));
}

// ------------------------------------------------------------------ layout

export function panel(title, ...children) {
  return h("section", { class: "panel" }, title ? h("h3", { class: "panel-title" }, title) : null, ...children);
}

export function tabs(items, { onChange, initial } = {}) {
  const bar = h("div", { class: "tabs", role: "tablist" });
  const body = h("div", { class: "tab-body" });
  const buttons = items.map((it, i) => {
    const b = h("button", { class: "tab", role: "tab", type: "button", id: `tab-${it.id}`, "aria-selected": "false",
      onclick: () => select(it.id) }, it.label);
    b.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      const next = items[(i + (e.key === "ArrowRight" ? 1 : items.length - 1)) % items.length];
      select(next.id); document.getElementById(`tab-${next.id}`).focus();
    });
    bar.append(b);
    return b;
  });
  function select(id) {
    items.forEach((it, i) => {
      const on = it.id === id;
      buttons[i].setAttribute("aria-selected", String(on));
      buttons[i].tabIndex = on ? 0 : -1;
    });
    const it = items.find((x) => x.id === id) || items[0];
    fill(body, it.render());
    if (onChange) onChange(id);
  }
  select(initial || items[0].id);
  return { el: h("div", { class: "tabset" }, bar, body), select };
}

export function stat(label, value, note) {
  return h("div", { class: "stat" }, h("div", { class: "stat-value" }, value), h("div", { class: "stat-label" }, label),
    note ? h("div", { class: "stat-note" }, note) : null);
}

export function badge(text, kind = "") {
  return h("span", { class: `badge ${kind}` }, text);
}

// ------------------------------------------------------------------ automata

export function transitionTable(table, { activeRow = null } = {}) {
  const head = h("tr", {}, h("th", { scope: "col" }, "State"), table.symbols.map((a) => h("th", { scope: "col" }, a)));
  const rows = table.rows.map((r) => h("tr", { class: r.state === activeRow ? "current" : "" },
    h("th", { scope: "row" },
      r.start ? h("span", { class: "mark", title: "start state" }, "→") : null,
      r.accepting ? h("span", { class: "mark acc", title: "accepting state" }, "*") : null,
      r.state),
    table.symbols.map((a) => {
      const cell = r.cells[a] || [];
      return h("td", { class: cell.length ? "" : "empty" }, cell.length ? (cell.length === 1 && table.symbols.indexOf("ε") < 0
        ? cell[0] : fmtSet(cell)) : "—");
    })));
  return h("div", { class: "table-wrap" },
    h("table", { class: "ttable" }, h("caption", {}, "Transition table — → start, * accepting, — no transition"),
      h("thead", {}, head), h("tbody", {}, rows)));
}

export async function examplePicker({ onPick, filter = () => true, label = "Load example", selected = "" } = {}) {
  const list = (await api.examples()).filter(filter);
  const groups = {};
  for (const e of list) (groups[e.category] ||= []).push(e);
  const sel = h("select", { "aria-label": label },
    h("option", { value: "" }, `${label}…`),
    Object.entries(groups).map(([cat, items]) => h("optgroup", { label: cat },
      items.map((e) => h("option", { value: e.id, selected: e.id === selected }, `${e.name} (${e.type}, ${e.state_count})`)))));
  sel.addEventListener("change", async () => {
    if (!sel.value) return;
    const ex = await api.example(sel.value);
    onPick(ex);
  });
  return sel;
}

// Workspace slots shared between views ("current", "A", "B"), kept in localStorage.
export const workspace = {
  get(slot) { return store.get("ws:" + slot, null); },
  set(slot, spec) { store.set("ws:" + slot, spec); },
};

// ------------------------------------------------------------------ editor

function specToText(spec) {
  return spec.transitions.map((t) => `${t.from} ${t.symbol} ${t.to}`).join("\n");
}

function parseList(text) {
  return text.split(/[,\s]+/).map((x) => x.trim()).filter(Boolean);
}

export class AutomatonEditor {
  constructor(container, { onChange } = {}) {
    this.onChange = onChange;
    this.type = h("select", { id: "ed-type" }, h("option", { value: "DFA" }, "DFA"), h("option", { value: "NFA" }, "NFA (ε allowed)"));
    this.name = h("input", { id: "ed-name", type: "text", maxlength: 120 });
    this.states = h("input", { id: "ed-states", type: "text", spellcheck: "false" });
    this.alphabet = h("input", { id: "ed-alpha", type: "text", spellcheck: "false" });
    this.start = h("input", { id: "ed-start", type: "text", spellcheck: "false" });
    this.accept = h("input", { id: "ed-accept", type: "text", spellcheck: "false" });
    this.trans = h("textarea", { id: "ed-trans", rows: 9, spellcheck: "false", class: "mono" });
    this.json = h("textarea", { rows: 12, spellcheck: "false", class: "mono", hidden: true, "aria-label": "Automaton JSON" });
    this.jsonToggle = h("button", { class: "btn ghost small", type: "button", onclick: () => this.toggleJSON() }, "Edit as JSON");
    const field = (id, label, input, hint) => h("div", { class: "field" }, h("label", { for: id }, label), input,
      hint ? h("div", { class: "hint" }, hint) : null);
    this.form = h("div", { class: "editor-grid" },
      field("ed-type", "Type", this.type),
      field("ed-name", "Name", this.name),
      field("ed-states", "States", this.states, "Separated by spaces or commas"),
      field("ed-alpha", "Alphabet Σ", this.alphabet, "e.g. A C G U"),
      field("ed-start", "Start state", this.start),
      field("ed-accept", "Accepting states", this.accept),
      h("div", { class: "field wide" }, h("label", { for: "ed-trans" }, "Transitions"), this.trans,
        h("div", { class: "hint" }, "One per line: ", h("code", {}, "from symbol to"), ". Use ", h("code", {}, "ε"),
          " (or ", h("code", {}, "eps"), ") for an ε-transition in an NFA. Lines starting with # are ignored.")));
    container.append(h("div", { class: "editor" }, this.form, this.json, h("div", { class: "row" }, this.jsonToggle)));
  }

  toggleJSON() {
    const showing = !this.json.hidden;
    if (showing) {
      try { this.setSpec(JSON.parse(this.json.value)); }
      catch (e) { toast("The JSON is not valid: " + e.message, "error"); return; }
    } else {
      this.json.value = JSON.stringify(this.getSpec(), null, 2);
    }
    this.json.hidden = showing;
    this.form.hidden = !showing;
    this.jsonToggle.textContent = showing ? "Edit as JSON" : "Back to form";
  }

  setSpec(spec) {
    this.descriptions = spec.descriptions || {};
    this.type.value = spec.type;
    this.name.value = spec.name || "";
    this.states.value = spec.states.join(" ");
    this.alphabet.value = spec.alphabet.join(" ");
    this.start.value = spec.start;
    this.accept.value = (spec.accept || []).join(" ");
    this.trans.value = specToText(spec);
    if (!this.json.hidden) this.json.value = JSON.stringify(spec, null, 2);
  }

  getSpec() {
    if (!this.json.hidden) return JSON.parse(this.json.value);
    const transitions = [];
    this.trans.value.split("\n").forEach((line) => {
      const t = line.trim();
      if (!t || t.startsWith("#")) return;
      const parts = t.split(/\s+/);
      if (parts.length !== 3) throw Object.assign(new Error(`Transition line "${t}" must have exactly 3 parts: from symbol to`),
        { field: "transitions" });
      transitions.push({ from: parts[0], symbol: parts[1], to: parts[2] });
    });
    const states = parseList(this.states.value);
    const descriptions = Object.fromEntries(Object.entries(this.descriptions || {}).filter(([k]) => states.includes(k)));
    return { type: this.type.value, name: this.name.value.trim() || this.type.value, states,
      alphabet: parseList(this.alphabet.value), start: this.start.value.trim(), accept: parseList(this.accept.value),
      transitions, descriptions };
  }
}

// ------------------------------------------------------------------ trace player

export function tape(symbols, index, { label = "Input" } = {}) {
  const cells = symbols.length
    ? symbols.map((x, i) => h("span", { class: "cell" + (i === index ? " current" : i < index ? " read" : "") }, x))
    : [h("span", { class: "cell empty" }, "ε")];
  return h("div", { class: "tape", "aria-label": `${label} tape` }, cells);
}

export class TracePlayer {
  constructor(container, graph, { onFrame, finalView } = {}) {
    this.graph = graph;
    this.onFrame = onFrame;
    this.finalView = finalView;   // optional: replaces the accept/reject verdict (e.g. transducers)
    this.k = -1;
    this.timer = null;
    this.root = h("div", { class: "player", tabindex: "0", "aria-label": "Execution trace player. Arrow keys step, space plays." });
    this.tapeHost = h("div", {});
    this.status = h("div", { class: "player-status", "aria-live": "polite" });
    this.progress = h("progress", { max: 1, value: 0, "aria-label": "Execution progress" });
    this.explain = h("p", { class: "explain" });
    this.final = h("div", {});
    this.btn = {
      reset: h("button", { class: "btn ghost", type: "button", title: "Reset (Home)", onclick: () => this.go(-1) }, "Reset"),
      back: h("button", { class: "btn ghost", type: "button", title: "Step back (←)", onclick: () => this.go(this.k - 1) }, "Back"),
      step: h("button", { class: "btn", type: "button", title: "Step forward (→)", onclick: () => this.go(this.k + 1) }, "Step"),
      play: h("button", { class: "btn ghost", type: "button", title: "Play / pause (Space)", onclick: () => this.toggle() }, "Play"),
      end: h("button", { class: "btn ghost", type: "button", title: "Jump to end (End)", onclick: () => this.go(this.n - 1) }, "End"),
    };
    this.speed = h("select", { "aria-label": "Playback speed" },
      h("option", { value: "1100" }, "Slow"), h("option", { value: "650", selected: true }, "Normal"), h("option", { value: "250" }, "Fast"));
    this.stepsTable = h("div", { class: "steps-table" });
    this.root.append(
      h("div", { class: "player-head" }, this.tapeHost, this.status),
      this.progress,
      h("div", { class: "controls" }, Object.values(this.btn), this.speed),
      this.explain, this.final, this.stepsTable);
    this.root.addEventListener("keydown", (e) => {
      if (e.target !== this.root) return;
      const map = { ArrowRight: () => this.go(this.k + 1), ArrowLeft: () => this.go(this.k - 1), Home: () => this.go(-1),
        End: () => this.go(this.n - 1), " ": () => this.toggle() };
      if (map[e.key]) { e.preventDefault(); map[e.key](); }
    });
    fill(container, this.root);
  }

  load(run) {
    this.stop();
    this.run = run;
    this.n = run.steps.length;
    this.progress.max = Math.max(1, this.n);
    this.renderTable();
    this.go(-1);
  }

  frame(k) {
    const run = this.run;
    if (k < 0) {
      return { active: run.initial_active, edges: (run.initial_epsilon_edges || []).map((e) => ({ ...e, symbol: "ε" })),
        text: run.initial_explanation, index: 0, stuck: null };
    }
    const st = run.steps[k];
    let edges = [];
    if (run.kind === "DFA") {
      if (st.exists) edges = [{ from: st.state, to: st.next, symbol: st.symbol }];
    } else {
      for (const m of st.moves) for (const t of m.to) edges.push({ from: m.from, to: t, symbol: st.symbol });
      for (const e of st.epsilon_edges) edges.push({ ...e, symbol: "ε" });
    }
    return { active: st.next_active, edges, text: st.explanation, index: k + 1,
      stuck: run.kind === "DFA" && !st.exists ? st.state : null };
  }

  go(k) {
    if (!this.run) return;
    k = Math.max(-1, Math.min(this.n - 1, k));
    this.k = k;
    const f = this.frame(k);
    const classes = f.stuck ? { [f.stuck]: "stuck" } : {};
    this.graph.highlight({ active: f.active, edges: f.edges, classes });
    fill(this.tapeHost, tape(this.run.input, k));
    this.progress.value = k + 1;
    const where = k < 0 ? "Before reading input" : `Read ${k + 1} of ${this.n} symbol${this.n === 1 ? "" : "s"}`;
    fill(this.status, h("span", {}, where),
      h("span", { class: "active-set" }, this.run.kind === "NFA" ? "Active set " : "State ",
        h("code", {}, this.run.kind === "NFA" ? fmtSet(f.active) : (f.active[0] || (f.stuck ? `${f.stuck} (stuck)` : "—")))));
    this.explain.textContent = f.text;
    const done = k === this.n - 1;
    clear(this.final);
    if (done) this.final.append(this.finalView ? this.finalView(this.run) : verdict(this.run.accepted, this.run.verdict));
    this.btn.back.disabled = k < 0;
    this.btn.reset.disabled = k < 0;
    this.btn.step.disabled = done;
    this.btn.end.disabled = done;
    this.stepsTable.querySelectorAll("tr[data-k]").forEach((tr) => tr.classList.toggle("current", Number(tr.dataset.k) === k));
    if (done) this.stop();
    if (this.onFrame) this.onFrame(k, f);
  }

  toggle() {
    if (this.timer) { this.stop(); return; }
    if (this.k >= this.n - 1) this.go(-1);
    this.btn.play.textContent = "Pause";
    const tick = () => {
      if (this.k >= this.n - 1) { this.stop(); return; }
      this.go(this.k + 1);
      this.timer = setTimeout(tick, prefersReducedMotion() ? 1400 : Number(this.speed.value));
    };
    this.timer = setTimeout(tick, 150);
  }

  stop() {
    clearTimeout(this.timer);
    this.timer = null;
    this.btn.play.textContent = "Play";
  }

  renderTable() {
    const run = this.run;
    const nfa = run.kind === "NFA";
    const rows = [h("tr", { "data-k": "-1", onclick: () => this.go(-1) },
      h("td", {}, "start"), h("td", {}, "—"), h("td", {}, "—"), h("td", {}, h("code", {}, nfa ? fmtSet(run.initial_active) : run.initial_active[0])))];
    run.steps.forEach((st, k) => rows.push(h("tr", { "data-k": String(k), onclick: () => this.go(k) },
      h("td", {}, k), h("td", {}, h("code", {}, st.symbol)),
      h("td", {}, h("code", {}, nfa ? fmtSet(st.active) : st.state)),
      h("td", {}, nfa ? h("code", {}, fmtSet(st.next_active)) :
        st.exists ? h("code", {}, st.next) : h("span", { class: "bad" }, "no transition")))));
    fill(this.stepsTable, h("details", {},
      h("summary", {}, `Full trace (${run.steps.length} step${run.steps.length === 1 ? "" : "s"}) for input `, h("code", {}, word(run.input))),
      h("div", { class: "table-wrap" }, h("table", { class: "trace" },
        h("thead", {}, h("tr", {}, h("th", {}, "Pos"), h("th", {}, "Symbol"), h("th", {}, nfa ? "Active set" : "State"),
          h("th", {}, nfa ? "Next active set" : "Next state"))),
        h("tbody", {}, rows)))));
  }
}
