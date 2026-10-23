// SVG state-diagram renderer. The picture is computed ONLY from the automaton
// specification passed in (states, start, accept, transitions) and from the
// highlight data of a real execution trace — nothing is hard-coded.
//
// Layout: breadth-first layers from the start state (columns), unreachable
// states in a last column, rows ordered by the barycentre of predecessors to
// reduce crossings. Nodes can be dragged; "Reset layout" restores the
// automatic layout.

import { h, s, clear, fill } from "./dom.js";

let uid = 0;
const COL_GAP = 150;
const ROW_GAP = 96;

function radiusFor(label) {
  return Math.max(21, Math.min(40, 9 + label.length * 4.3));
}

function shortLabel(label, max = 12) {
  return label.length > max ? label.slice(0, max - 1) + "…" : label;
}

export function autoLayout(spec) {
  const states = spec.states;
  const out = new Map(states.map((q) => [q, []]));
  const inn = new Map(states.map((q) => [q, []]));
  for (const t of spec.transitions) {
    if (t.from === t.to) continue;
    if (out.has(t.from) && !out.get(t.from).includes(t.to)) out.get(t.from).push(t.to);
    if (inn.has(t.to) && !inn.get(t.to).includes(t.from)) inn.get(t.to).push(t.from);
  }
  const depth = new Map([[spec.start, 0]]);
  const order = [spec.start];
  for (let i = 0; i < order.length; i++) {
    for (const nxt of out.get(order[i]) || []) {
      if (!depth.has(nxt)) { depth.set(nxt, depth.get(order[i]) + 1); order.push(nxt); }
    }
  }
  const maxDepth = Math.max(0, ...depth.values());
  const unreachable = states.filter((q) => !depth.has(q));
  const cols = [];
  for (const q of order) (cols[depth.get(q)] ||= []).push(q);
  if (unreachable.length) cols[maxDepth + 1] = unreachable;

  // barycentre ordering passes
  for (let pass = 0; pass < 3; pass++) {
    for (let c = 1; c < cols.length; c++) {
      const prevIndex = new Map();
      cols.slice(0, c).forEach((col) => col.forEach((q, i) => prevIndex.set(q, i - (col.length - 1) / 2)));
      const score = (q) => {
        const ps = inn.get(q).filter((p) => prevIndex.has(p));
        return ps.length ? ps.reduce((a, p) => a + prevIndex.get(p), 0) / ps.length : 0;
      };
      cols[c] = cols[c].map((q, i) => [q, score(q), i]).sort((a, b) => a[1] - b[1] || a[2] - b[2]).map((x) => x[0]);
    }
  }
  const pos = {};
  const tallest = Math.max(...cols.map((c) => (c ? c.length : 0)));
  cols.forEach((col, ci) => {
    if (!col) return;
    const offset = ((tallest - col.length) * ROW_GAP) / 2;
    col.forEach((q, ri) => { pos[q] = { x: 80 + ci * COL_GAP, y: 70 + offset + ri * ROW_GAP }; });
  });
  return { pos, unreachable: new Set(unreachable) };
}

export class AutomatonGraph {
  constructor(container, { height = null, compact = false } = {}) {
    this.id = ++uid;
    this.root = h("div", { class: "graph" + (compact ? " compact" : "") });
    this.svgHost = h("div", { class: "graph-canvas" });
    if (height) this.svgHost.style.minHeight = height + "px";
    this.resetBtn = h("button", { class: "btn ghost small", type: "button", hidden: true, onclick: () => this.resetLayout() },
      "Reset layout");
    this.root.append(
      this.svgHost,
      h("div", { class: "graph-tools" },
        h("span", { class: "graph-hint" }, "Drag states to rearrange"),
        this.resetBtn,
        h("button", { class: "btn ghost small", type: "button", onclick: () => this.downloadSVG() }, "Download SVG")),
    );
    fill(container, this.root);
    this.spec = null;
    this.hl = {};
  }

  setSpec(spec, opts = {}) {
    this.spec = spec;
    this.opts = opts;
    const lay = autoLayout(spec);
    this.auto = lay;
    this.pos = Object.fromEntries(Object.entries(lay.pos).map(([k, v]) => [k, { ...v }]));
    this.resetBtn.hidden = true;
    this.render();
    return this;
  }

  resetLayout() {
    this.pos = Object.fromEntries(Object.entries(this.auto.pos).map(([k, v]) => [k, { ...v }]));
    this.resetBtn.hidden = true;
    this.render();
  }

  highlight(hl = {}) {
    this.hl = hl;
    this.render();
  }

  render() {
    const spec = this.spec;
    if (!spec) return;
    const hl = this.hl || {};
    const opts = this.opts || {};
    const active = new Set(hl.active || []);
    const takenKeys = new Set((hl.edges || []).map((e) => `${e.from}\u0000${e.to}`));
    const takenSymbols = new Map();
    for (const e of hl.edges || []) takenSymbols.set(`${e.from}\u0000${e.to}`, e.symbol);
    const classes = hl.classes || {};
    const dim = new Set(hl.dim || []);
    const accept = new Set(spec.accept || []);
    const descriptions = spec.descriptions || {};
    const nodeLabel = opts.nodeLabel || ((q) => q);
    const R = {};
    for (const q of spec.states) R[q] = radiusFor(shortLabel(nodeLabel(q)));

    // group parallel transitions into one edge per (from, to)
    const groups = new Map();
    for (const t of spec.transitions) {
      const key = `${t.from}\u0000${t.to}`;
      if (!groups.has(key)) groups.set(key, { from: t.from, to: t.to, labels: [], eps: true });
      const g = groups.get(key);
      const lab = t.label ?? t.symbol;
      if (!g.labels.includes(lab)) g.labels.push(lab);
      if (t.symbol !== "ε") g.eps = false;
    }

    const id = this.id;
    const svg = s("svg", { class: "automaton", role: "img",
      "aria-label": `${spec.type || ""} diagram with ${spec.states.length} states: ${spec.states.join(", ")}` });
    const defs = s("defs", {},
      s("marker", { id: `arr${id}`, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 8, markerHeight: 8,
        orient: "auto-start-reverse", markerUnits: "userSpaceOnUse" }, s("path", { d: "M0,0 L10,5 L0,10 z", class: "arrowhead" })),
      s("marker", { id: `arrA${id}`, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 10, markerHeight: 10,
        orient: "auto-start-reverse", markerUnits: "userSpaceOnUse" }, s("path", { d: "M0,0 L10,5 L0,10 z", class: "arrowhead taken" })));
    svg.append(defs);
    const edgeLayer = s("g", { class: "edges" });
    const labelLayer = s("g", { class: "edge-labels" });
    const nodeLayer = s("g", { class: "nodes" });
    svg.append(edgeLayer, nodeLayer, labelLayer);

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    const grow = (x, y, pad = 0) => {
      minX = Math.min(minX, x - pad); maxX = Math.max(maxX, x + pad);
      minY = Math.min(minY, y - pad); maxY = Math.max(maxY, y + pad);
    };

    for (const g of groups.values()) {
      const key = `${g.from}\u0000${g.to}`;
      const taken = takenKeys.has(key);
      const a = this.pos[g.from], b = this.pos[g.to];
      if (!a || !b) continue;
      let text = g.labels.join(", ");
      const full = text;
      if (text.length > 22) text = text.slice(0, 20) + "…";
      const cls = "edge" + (taken ? " taken" : "") + (g.eps ? " eps" : "") +
        (dim.has(g.from) || dim.has(g.to) ? " dim" : "");
      const marker = `url(#${taken ? "arrA" : "arr"}${id})`;
      let d, lx, ly;
      if (g.from === g.to) {
        const r = R[g.from];
        const p1 = { x: a.x + r * Math.cos(-2.1), y: a.y + r * Math.sin(-2.1) };
        const p2 = { x: a.x + r * Math.cos(-1.04), y: a.y + r * Math.sin(-1.04) };
        d = `M${p1.x},${p1.y} C${a.x - r * 1.3},${a.y - r * 2.7} ${a.x + r * 1.3},${a.y - r * 2.7} ${p2.x},${p2.y}`;
        lx = a.x; ly = a.y - r * 2.2 - 8;
        grow(a.x, a.y - r * 2.6 - 14, r * 1.4);
      } else {
        const dx = b.x - a.x, dy = b.y - a.y;
        const len = Math.hypot(dx, dy) || 1;
        const nx = dy / len, ny = -dx / len;
        let curve = 0;
        if (groups.has(`${g.to}\u0000${g.from}`)) curve = 24;
        else {
          for (const q of spec.states) {
            if (q === g.from || q === g.to || !this.pos[q]) continue;
            const p = this.pos[q];
            const tt = ((p.x - a.x) * dx + (p.y - a.y) * dy) / (len * len);
            if (tt <= 0 || tt >= 1) continue;
            // distance from the other state's centre to the straight edge
            const perp = Math.abs((p.x - a.x) * dy - (p.y - a.y) * dx) / len;
            if (perp < R[q] + 10) { curve = 46 + Math.min(60, len / 8); break; }
          }
        }
        const mx = (a.x + b.x) / 2 + nx * curve, my = (a.y + b.y) / 2 + ny * curve;
        const ra = R[g.from], rb = R[g.to];
        const da = Math.hypot(mx - a.x, my - a.y) || 1, db = Math.hypot(mx - b.x, my - b.y) || 1;
        const sx = a.x + ((mx - a.x) / da) * ra, sy = a.y + ((my - a.y) / da) * ra;
        const ex = b.x + ((mx - b.x) / db) * (rb + 1), ey = b.y + ((my - b.y) / db) * (rb + 1);
        d = curve ? `M${sx},${sy} Q${mx},${my} ${ex},${ey}` : `M${sx},${sy} L${ex},${ey}`;
        lx = 0.25 * sx + 0.5 * mx + 0.25 * ex;
        ly = 0.25 * sy + 0.5 * my + 0.25 * ey - (curve ? 0 : 7);
        grow(mx, my, 12);
      }
      const path = s("path", { d, class: cls, "marker-end": marker });
      edgeLayer.append(path);
      const label = s("text", { x: lx, y: ly, class: "edge-label" + (taken ? " taken" : ""), "text-anchor": "middle" },
        text, s("title", {}, `${g.from} → ${g.to} on ${full}`));
      labelLayer.append(label);
      grow(lx, ly, text.length * 4 + 6);
    }

    for (const q of spec.states) {
      const p = this.pos[q];
      if (!p) continue;
      const r = R[q];
      const lab = shortLabel(nodeLabel(q));
      const cls = ["node", active.has(q) ? "active" : "", accept.has(q) ? "accepting" : "",
        this.auto.unreachable.has(q) ? "unreachable" : "", dim.has(q) ? "dim" : "", classes[q] || ""].join(" ");
      const g = s("g", { class: cls, transform: `translate(${p.x},${p.y})`, "data-state": q });
      g.append(s("circle", { r, class: "ring" }));
      if (accept.has(q)) g.append(s("circle", { r: r - 4.5, class: "inner" }));
      g.append(s("text", { class: "node-label", "text-anchor": "middle", dy: "0.35em" }, lab));
      const desc = descriptions[q];
      g.append(s("title", {}, `${q}${accept.has(q) ? " (accepting)" : ""}${q === spec.start ? " (start)" : ""}` +
        `${this.auto.unreachable.has(q) ? " (unreachable)" : ""}${desc ? "\n" + desc : ""}`));
      this.enableDrag(g, q, svg);
      nodeLayer.append(g);
      grow(p.x, p.y, r + 6);
      if (q === spec.start) {
        edgeLayer.append(s("path", { d: `M${p.x - r - 38},${p.y} L${p.x - r - 1},${p.y}`, class: "edge start",
          "marker-end": `url(#arr${id})` }));
        grow(p.x - r - 42, p.y, 4);
      }
    }
    const pad = 16;
    const w = Math.max(120, maxX - minX + pad * 2), hgt = Math.max(90, maxY - minY + pad * 2);
    svg.setAttribute("viewBox", `${minX - pad} ${minY - pad} ${w} ${hgt}`);
    svg.setAttribute("width", w);
    svg.setAttribute("height", hgt);
    this.svg = svg;
    fill(this.svgHost, svg);
  }

  enableDrag(g, q, svg) {
    g.addEventListener("pointerdown", (ev) => {
      ev.preventDefault();
      const ctm = svg.getScreenCTM();
      if (!ctm) return;
      const inv = ctm.inverse();
      const pt = svg.createSVGPoint();
      const start = { ...this.pos[q] };
      pt.x = ev.clientX; pt.y = ev.clientY;
      const p0 = pt.matrixTransform(inv);
      const vb = svg.viewBox.baseVal;
      const frozen = { x: vb.x, y: vb.y, w: vb.width, h: vb.height };
      const move = (e) => {
        pt.x = e.clientX; pt.y = e.clientY;
        const p1 = pt.matrixTransform(inv);
        this.pos[q] = { x: start.x + p1.x - p0.x, y: start.y + p1.y - p0.y };
        this.resetBtn.hidden = false;
        this.render();
        // keep the viewport steady while dragging so the node follows the pointer
        this.svg.setAttribute("viewBox", `${frozen.x} ${frozen.y} ${frozen.w} ${frozen.h}`);
        this.svg.setAttribute("width", frozen.w);
        this.svg.setAttribute("height", frozen.h);
      };
      const up = () => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", up);
        this.render();
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", up);
    });
  }

  downloadSVG() {
    if (!this.svg) return;
    const clone = this.svg.cloneNode(true);
    const css = getComputedStyle(document.documentElement);
    const v = (n) => css.getPropertyValue(n).trim();
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    clone.insertBefore(s("style", {}, `
      .edge{fill:none;stroke:${v("--ink-2")};stroke-width:1.5}.edge.eps{stroke-dasharray:5 4}
      .edge.taken{stroke:${v("--primary")};stroke-width:3}.arrowhead{fill:${v("--ink-2")}}.arrowhead.taken{fill:${v("--primary")}}
      .node .ring{fill:${v("--surface")};stroke:${v("--ink")};stroke-width:1.6}.node .inner{fill:none;stroke:${v("--ink")};stroke-width:1.3}
      .node.active .ring{fill:${v("--primary")}}.node.active .node-label{fill:${v("--on-primary")}}
      text{font-family:${v("--font-mono")};font-size:12px;fill:${v("--ink")}}.edge-label{font-size:11px}`), clone.firstChild);
    const blob = new Blob([new XMLSerializer().serializeToString(clone)], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = h("a", { href: url, download: `${(this.spec.name || "automaton").replace(/[^\w-]+/g, "_")}.svg` });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}
