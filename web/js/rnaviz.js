// Small, dependency-free RNA visualisations (all drawn from API data).

import { h, s } from "./dom.js";

export function compositionBars(comp) {
  return h("div", { class: "comp-bars", role: "list", "aria-label": "Nucleotide composition" },
    ["A", "C", "G", "U"].map((b) => h("div", { class: "comp-bar", role: "listitem" },
      h("span", { class: `lab nt-${b}` }, b),
      h("div", { class: "track", "aria-hidden": "true" }, h("div", { class: `fill ${b}`, style: { width: `${comp.percent[b]}%` } })),
      h("span", { class: "num" }, `${comp.percent[b].toFixed(1)}% · ${comp.counts[b]}`))));
}

export function gcChart(profile, overall) {
  if (!profile.points.length) return h("p", { class: "muted small" }, "A GC profile needs at least 20 nt.");
  const W = 560, H = 170, L = 34, B = 24, T = 10, R = 10;
  const pts = profile.points;
  const maxX = pts[pts.length - 1].start + profile.window;
  const x = (v) => L + ((W - L - R) * v) / maxX;
  const y = (v) => T + ((H - T - B) * (100 - v)) / 100;
  const d = pts.map((p, i) => `${i ? "L" : "M"}${x(p.start + profile.window / 2).toFixed(1)},${y(p.gc).toFixed(1)}`).join(" ");
  const ticks = [0, 25, 50, 75, 100];
  return h("figure", { style: { margin: 0 } },
    s("svg", { class: "chart", viewBox: `0 0 ${W} ${H}`, width: "100%", role: "img",
      "aria-label": `GC content along the sequence, window ${profile.window} nt; overall ${overall}%` },
      ticks.map((t) => [s("line", { class: "axis", x1: L, x2: W - R, y1: y(t), y2: y(t), "stroke-opacity": t % 50 ? .4 : 1 }),
        s("text", { x: L - 6, y: y(t) + 4, "text-anchor": "end" }, `${t}%`)]),
      s("line", { class: "ref", x1: L, x2: W - R, y1: y(overall), y2: y(overall) }),
      s("path", { class: "line", d }),
      s("text", { x: L, y: H - 6 }, "0"),
      s("text", { x: W - R, y: H - 6, "text-anchor": "end" }, `${maxX} nt`)),
    h("figcaption", { class: "small muted" }, `Sliding window of ${profile.window} nt (step ${profile.step}). Dashed line: overall GC ${overall}%.`));
}

// Arc diagram: bases on a line, each pair (i, j) an arc above. Pairs listed
// in `crossing` are drawn in the alert colour; `types` (optional) gives the
// bracket-type index per pair for colouring pseudoknot layers.
export function arcDiagram(length, pairs, { sequence = null, crossing = new Set(), types = null } = {}) {
  const W = Math.max(240, Math.min(1100, length * 16));
  const step = (W - 20) / Math.max(1, length);
  const maxSpan = Math.max(1, ...pairs.map(([i, j]) => j - i));
  const H = Math.min(260, 30 + (maxSpan * step) / 2) + 30;
  const base = H - 26;
  const xs = (i) => 10 + step * (i + 0.5);
  return s("svg", { class: "arc-svg", viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img",
    "aria-label": `Arc diagram with ${pairs.length} base pairs${crossing.size ? `, ${crossing.size} crossing` : ""}` },
    s("line", { x1: 10, x2: W - 10, y1: base, y2: base, stroke: "currentColor", "stroke-opacity": .25 }),
    pairs.map(([i, j], k) => {
      const x1 = xs(i), x2 = xs(j), r = (x2 - x1) / 2;
      const hgt = Math.min(base - 8, r);
      const cls = crossing.has(`${i},${j}`) ? "cross" : types ? `t${types[k] || 0}` : "";
      return s("path", { d: `M${x1},${base} C${x1},${base - hgt * 1.33} ${x2},${base - hgt * 1.33} ${x2},${base}`, class: cls },
        s("title", {}, `pair (${i}, ${j})${sequence ? ` ${sequence[i]}–${sequence[j]}` : ""}`));
    }),
    sequence && length <= 120 ? sequence.split("").map((b, i) => s("text", { x: xs(i), y: base + 16, class: `nt-${b}`,
      fill: "currentColor" }, b)) : null);
}

export function dpHeat(table, sequence) {
  const n = table.length;
  let max = 1;
  table.forEach((row) => row.forEach((v) => { if (v !== null && v > max) max = v; }));
  return h("div", { class: "table-wrap" }, h("table", { class: "heat", "aria-label": "Dynamic-programming table best[i][j]" },
    h("thead", {}, h("tr", {}, h("th", {}, ""), sequence.split("").map((b) => h("th", {}, b)))),
    h("tbody", {}, table.map((row, i) => h("tr", {}, h("th", {}, sequence[i]),
      row.map((v, j) => h("td", {
        title: v === null ? "" : `best[${i}][${j + 1}] = ${v} pair(s) in bases ${i}..${j}`,
        style: v === null ? {} : { background: `color-mix(in srgb, var(--primary) ${Math.round((v / max) * 85) + 6}%, var(--surface))`,
          color: v / max > .55 ? "var(--on-primary)" : "var(--ink-2)" },
      }, v === null ? "" : v)))))));
}
