import { h, clear, append, downloadJSON, store, fill } from "../dom.js";
import { AutomatonGraph } from "../graph.js";
import { errorBox, busy, notice, stat, tabs, badge, loading, toast } from "../components.js";
import { compositionBars, gcChart, arcDiagram, dpHeat } from "../rnaviz.js";
import * as api from "../api.js";

export const title = "RNA analyzer";

const SAMPLES = [
  ["Report demo", "CCCAUGGCUACGUAAGGGUGACCC"],
  ["mRNA-like with motifs", ">demo_mrna synthetic sequence for demonstration\nGGCAGGAGGUAACCAUGGCUGCUAAAGCUGGUAGCUAAUAAAGGCAUUUAUUUAGCGCGCAAUAAAGGG"],
  ["Hairpin", "GGGAGCCAUCGAAAGAUGGCUCCC"],
  ["Two FASTA records", ">rec1 first record\nAUGGCCUAA\n>rec2 second record\nGGGAUGAAACCCUGAUUU"],
  ["Invalid input", "AUGGCNNAXUUA-GC"],
];
const PAGE = 1200;
const ROW = 60;

export async function render(root, params) {
  const text = h("textarea", { id: "rna-text", rows: 8, class: "mono", spellcheck: "false",
    placeholder: "Paste an RNA sequence (A, C, G, U) or a FASTA record…" });
  const fileInput = h("input", { type: "file", accept: ".fa,.fasta,.fna,.ffn,.frn,.txt,.seq,.rna", hidden: true });
  const fileInfo = h("div", { class: "small muted" });
  const recordSel = h("select", { "aria-label": "FASTA record", hidden: true, style: { display: "block" } });
  const convertT = h("input", { type: "checkbox", checked: true, id: "rna-t" });
  const minOrf = h("input", { type: "number", min: 0, max: 10000, value: 0, id: "rna-minorf" });
  const motifsText = h("textarea", { id: "rna-motifs", rows: 2, class: "mono", spellcheck: "false",
    placeholder: "Optional: up to 5 patterns, one per line, e.g.  UAUAAA  or  GC-box: (G|C)(G|C)(G|C)" });
  const save = h("input", { type: "checkbox", checked: store.get("rna:save", true), id: "rna-save" });
  const analyzeBtn = h("button", { class: "btn", type: "submit" }, "Analyze sequence");
  const out = h("div", {});
  const drop = h("div", { class: "dropzone" }, "Drop a FASTA or text file here, or ",
    h("button", { class: "linkish", type: "button", onclick: () => fileInput.click() }, "choose a file"),
    h("div", { class: "hint" }, ".fa .fasta .fna .txt .seq — up to 2 MB, read on the server and never stored as a file"));

  root.append(
    h("header", { class: "view-head" }, h("h1", {}, "RNA analyzer"),
      h("p", {}, "Validates the sequence, then runs the project's automata over it: the ORF DFA in all three forward frames, ",
        "regex-compiled DFAs for motifs, and Moore/Mealy transducers. Results are syntactic pattern matches, not biological annotations.")),
    h("form", { class: "panel", onsubmit: (e) => { e.preventDefault(); analyze(); } },
      h("div", { class: "grid-2" },
        h("div", { class: "stack" },
          h("div", { class: "field" }, h("label", { for: "rna-text" }, "Sequence"), text),
          h("div", { class: "row small" }, h("span", { class: "muted" }, "Samples:"),
            SAMPLES.map(([name, seq]) => h("button", { class: "btn ghost small", type: "button",
              onclick: () => { text.value = seq; recordSel.hidden = true; fileInfo.textContent = ""; } }, name)))),
        h("div", { class: "stack" },
          drop, fileInput, fileInfo, recordSel,
          h("label", { class: "check" }, convertT, "Treat T as U (accept DNA input)"),
          h("div", { class: "inline-fields" },
            h("div", { class: "field" }, h("label", { for: "rna-minorf" }, "Minimum ORF length (codons, incl. start & stop)"), minOrf)),
          h("div", { class: "field" }, h("label", { for: "rna-motifs" }, "Custom motifs (regex: | * + ? and parentheses)"), motifsText),
          h("label", { class: "check" }, save, "Save to history"))),
      h("div", { class: "row", style: { marginTop: "14px" } }, analyzeBtn)),
    out);

  save.addEventListener("change", () => store.set("rna:save", save.checked));
  fileInput.addEventListener("change", () => fileInput.files[0] && uploadFile(fileInput.files[0]));
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault(); drop.classList.remove("over");
    if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0]);
  });

  async function uploadFile(file) {
    fill(fileInfo, loading(`Reading ${file.name}…`));
    try {
      const r = await api.upload("/api/rna/upload", file);
      text.value = r.text;
      fill(fileInfo, `${r.filename}: ${r.format.toUpperCase()}, ${r.record_count} record(s).`);
      clear(recordSel);
      if (r.record_count > 1) {
        append(recordSel, r.records.map((rec, i) => h("option", { value: i },
          `${rec.id} — ${rec.length} nt${rec.valid ? "" : `, ${rec.invalid_count} invalid`}`)));
        recordSel.hidden = false;
      } else recordSel.hidden = true;
    } catch (e) { fill(fileInfo, errorBox(e)); }
  }

  function parseMotifs() {
    return motifsText.value.split("\n").map((l) => l.trim()).filter(Boolean).map((l) => {
      const m = l.match(/^([^:]+):\s*(.+)$/);
      return m ? { name: m[1].trim(), pattern: m[2].trim() } : { pattern: l };
    });
  }

  async function analyze(extra = {}) {
    const body = { text: text.value, convert_t: convertT.checked, min_orf_codons: Number(minOrf.value) || 0,
      motifs: parseMotifs(), save: save.checked, record_index: recordSel.hidden ? 0 : Number(recordSel.value || 0), ...extra };
    fill(out, loading("Running the automata over the sequence…"));
    try {
      const res = await busy(analyzeBtn, () => api.post("/api/rna/analyze", body));
      if (res.records && res.records.length > 1 && recordSel.hidden) {
        clear(recordSel);
        append(recordSel, res.records.map((rec, i) => h("option", { value: i, selected: i === res.record_index }, `${rec.id} — ${rec.raw_length} chars`)));
        recordSel.hidden = false;
      }
      showResult(out, res);
      if (res.valid && res.history_id) toast("Analysis saved to history.");
    } catch (e) { fill(out, errorBox(e)); }
  }

  if (params.history) {
    try {
      const entry = await api.get(`/api/history/${encodeURIComponent(params.history)}`);
      const p = entry.payload;
      text.value = p.text || "";
      convertT.checked = p.convert_t !== false;
      minOrf.value = p.min_orf_codons || 0;
      motifsText.value = (p.motifs || []).map((m) => (m.name ? `${m.name}: ${m.pattern}` : m.pattern)).join("\n");
      await analyze({ save: false, record_index: p.record_index || 0 });
    } catch (e) { fill(out, errorBox(e)); }
  } else {
    text.value = SAMPLES[1][1];
  }
}

// ------------------------------------------------------------------ results

function showResult(out, res) {
  clear(out);
  if (!res.valid) {
    const v = res.validation;
    out.append(h("section", { class: "panel" },
      h("h2", {}, "The sequence did not pass validation"),
      notice("error", null, res.error),
      h("div", { class: "table-wrap" }, h("table", { style: { minWidth: "560px" } },
        h("thead", {}, h("tr", {}, h("th", {}, "Character"), h("th", { class: "num" }, "Count"), h("th", {}, "Positions (0-based, whitespace ignored)"), h("th", {}, "Why it is rejected"))),
        h("tbody", {}, v.invalid.map((i) => h("tr", {}, h("td", {}, h("code", {}, i.char)), h("td", { class: "num" }, i.count),
          h("td", { class: "mono" }, i.positions.join(", ") + (i.more_positions ? ` … (+${i.more_positions})` : "")),
          h("td", {}, i.reason)))))),
      v.warnings.length ? h("p", { class: "small muted" }, v.warnings.join(" ")) : null,
      h("p", { class: "small" }, "Allowed symbols are A, C, G and U. Remove or replace the characters above and analyze again.")));
    return;
  }
  const c = res.composition;
  const starts = res.codon_positions.start.length, stops = res.codon_positions.stop.length;
  const motifHits = res.motifs.reduce((a, m) => a + m.count, 0);
  const viewerHost = h("div", {});
  const viewer = new SeqViewer(viewerHost, res);

  append(out,
    h("div", { class: "row", style: { justifyContent: "space-between", margin: "8px 0 12px" } },
      h("h2", { style: { margin: 0 } }, `Results for ${res.record_id}`),
      h("div", { class: "row" },
        h("button", { class: "btn ghost", type: "button", onclick: () => downloadJSON(`${res.record_id}-analysis.json`, res) }, "Export JSON"),
        h("button", { class: "btn ghost", type: "button", onclick: () => printReport(res) }, "Print report"))),
    h("div", { class: "stats" },
      stat("Length", `${res.length.toLocaleString()} nt`, res.format === "fasta" ? `FASTA record ${res.record_index + 1} of ${res.records.length}` : "raw text"),
      stat("GC content", `${c.gc_percent}%`, `AU ${c.au_percent}%`),
      stat("Open reading frames", res.orfs.length, res.min_orf_codons ? `≥ ${res.min_orf_codons} codons` : "any length"),
      stat("Start / stop codons", `${starts} / ${stops}`, "AUG / UAA·UAG·UGA, all frames"),
      stat("Motif matches", motifHits, `${res.motifs.length} patterns`)),
    (res.validation.warnings || []).concat(res.warnings || []).length
      ? notice("warn", "Note", (res.validation.warnings || []).concat(res.warnings || []).join(" ")) : null,
    notice("info", "How to read these results", res.disclaimer),
    h("div", { class: "grid-2" },
      h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Nucleotide composition"), compositionBars(c)),
      h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "GC content along the sequence"), gcChart(res.gc_profile, c.gc_percent))),
    h("section", { class: "panel" }, h("h3", { class: "panel-title" }, "Sequence"), viewerHost),
    featureTabs(res, viewer),
  );
}

class SeqViewer {
  constructor(host, res) {
    this.res = res;
    this.seq = res.sequence;
    this.page = 0;
    this.sel = null;
    this.frame = "none";
    this.show = { orf: true, motif: true, codon: true };
    this.pages = Math.ceil(this.seq.length / PAGE);
    this.body = h("div", { class: "seqview", role: "region", "aria-label": "Colour-coded sequence" });
    this.pageInfo = h("span", { class: "small muted" });
    this.jump = h("input", { type: "number", min: 0, max: this.seq.length - 1, placeholder: "position", style: { width: "9em" },
      "aria-label": "Jump to position (0-based)" });
    const toggle = (key, label) => {
      const cb = h("input", { type: "checkbox", checked: true });
      cb.addEventListener("change", () => { this.show[key] = cb.checked; this.draw(); });
      return h("label", { class: "check small" }, cb, label);
    };
    const frameSel = h("select", { "aria-label": "Codon boundaries" }, h("option", { value: "none" }, "No codon marks"),
      [0, 1, 2].map((f) => h("option", { value: f }, `Codons, frame ${f}`)));
    frameSel.addEventListener("change", () => { this.frame = frameSel.value; this.draw(); });
    this.prev = h("button", { class: "btn ghost small", type: "button", onclick: () => this.goto((this.page - 1) * PAGE) }, "Previous");
    this.next = h("button", { class: "btn ghost small", type: "button", onclick: () => this.goto((this.page + 1) * PAGE) }, "Next");
    host.append(
      h("div", { class: "row", style: { marginBottom: "8px" } }, toggle("orf", "ORFs"), toggle("motif", "Motifs"),
        toggle("codon", "Start/stop codons"), frameSel,
        h("form", { class: "row", style: { marginLeft: "auto" }, onsubmit: (e) => { e.preventDefault(); const p = Number(this.jump.value);
          if (Number.isInteger(p) && p >= 0 && p < this.seq.length) this.select(p, p + 1); else toast(`Enter a position from 0 to ${this.seq.length - 1}.`, "error"); } },
          this.jump, h("button", { class: "btn ghost small", type: "submit" }, "Go"))),
      h("div", { class: "seq-legend" },
        ["A", "C", "G", "U"].map((b) => h("span", { class: `nt-${b}` }, h("strong", {}, b))),
        h("span", {}, h("i", { class: "lg orf" }), "ORF"), h("span", {}, h("i", { class: "lg motif" }), "motif match"),
        h("span", {}, h("i", { class: "lg start" }), "start codon"), h("span", {}, h("i", { class: "lg stop" }), "stop codon"),
        h("span", {}, h("i", { class: "lg sel" }), "selected")),
      this.body,
      h("div", { class: "row", style: { marginTop: "8px" } }, this.prev, this.next, this.pageInfo));
    this.draw();
  }

  goto(pos) {
    this.page = Math.max(0, Math.min(this.pages - 1, Math.floor(pos / PAGE)));
    this.draw();
  }

  select(start, end) {
    this.sel = [start, end];
    this.goto(start);
    const el = this.body.querySelector(`[data-pos="${start}"]`);
    if (el) {
      el.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }

  draw() {
    const p0 = this.page * PAGE, p1 = Math.min(this.seq.length, p0 + PAGE);
    const cls = new Array(p1 - p0).fill("");
    const mark = (s, e, c) => { for (let i = Math.max(s, p0); i < Math.min(e, p1); i++) cls[i - p0] += " " + c; };
    if (this.show.orf) for (const o of this.res.orfs) if (o.end > p0 && o.start < p1) mark(o.start, o.end, "f-orf");
    if (this.show.motif) for (const m of this.res.motifs) for (const x of m.matches) if (x.end > p0 && x.start < p1) mark(x.start, x.end, "f-motif");
    if (this.show.codon) {
      for (const x of this.res.codon_positions.start) if (x.pos + 3 > p0 && x.pos < p1) mark(x.pos, x.pos + 3, "f-start");
      for (const x of this.res.codon_positions.stop) if (x.pos + 3 > p0 && x.pos < p1) mark(x.pos, x.pos + 3, "f-stop");
    }
    if (this.sel) mark(this.sel[0], this.sel[1], "f-sel");
    const rows = [];
    for (let r = p0; r < p1; r += ROW) {
      const blocks = [];
      for (let b = r; b < Math.min(r + ROW, p1); b += 10) {
        const spans = [];
        for (let i = b; i < Math.min(b + 10, p1); i++) {
          const base = this.seq[i];
          const edge = this.frame !== "none" && i >= Number(this.frame) && (i - Number(this.frame)) % 3 === 0 ? " codon-edge" : "";
          spans.push(h("span", { class: `b ${base}${cls[i - p0]}${edge}`, "data-pos": i, title: `${base} at ${i}` }, base));
        }
        blocks.push(h("span", { class: "seqblock" }, spans));
      }
      rows.push(h("div", { class: "seqrow" }, h("span", { class: "seqpos" }, r), h("span", { class: "seqbases" }, blocks)));
    }
    fill(this.body, ...rows);
    this.pageInfo.textContent = this.pages > 1 ? `Positions ${p0}–${p1 - 1} (page ${this.page + 1} of ${this.pages})` : `Positions 0–${p1 - 1}`;
    this.prev.disabled = this.page === 0;
    this.next.disabled = this.page >= this.pages - 1;
    this.prev.hidden = this.next.hidden = this.pages <= 1;
  }
}

function posLink(viewer, start, end, label) {
  return h("button", { class: "linkish", type: "button", onclick: () => viewer.select(start, end),
    title: "Show in the sequence" }, label ?? `${start}–${end - 1}`);
}

function featureTabs(res, viewer) {
  const t = tabs([
    { id: "orfs", label: `ORFs (${res.orfs.length})`, render: () => orfTab(res, viewer) },
    { id: "motifs", label: "Motifs", render: () => motifTab(res, viewer) },
    { id: "codons", label: "Start & stop codons", render: () => codonTab(res, viewer) },
    { id: "frames", label: "Reading frames", render: () => frameTab(res) },
    { id: "langs", label: "Formal languages", render: () => languageTab(res) },
    { id: "trans", label: "Transducers", render: () => transducerTab(res) },
    { id: "structure", label: "Structure (experimental)", render: () => structureTab(res, viewer) },
  ]);
  return h("section", { class: "panel" }, t.el);
}

function orfTab(res, viewer) {
  const traceHost = h("div", {});
  if (!res.orfs.length) {
    return h("div", {}, h("p", {}, "No open reading frame was found: no AUG is followed by an in-frame stop codon in any of the three forward frames",
      res.min_orf_codons ? ` with at least ${res.min_orf_codons} codons.` : "."));
  }
  return h("div", {},
    h("p", { class: "small muted" }, "An ORF is recognised when the ORF DFA (START (SENSE)* STOP, read codon by codon) reaches its accepting state. ",
      "Scanning starts at the first AUG outside an ORF; inner AUGs are read as methionine. Translation uses the standard genetic code (* = stop)."),
    h("div", { class: "table-wrap feature-list" }, h("table", {},
      h("thead", {}, h("tr", {}, h("th", {}, "Frame"), h("th", {}, "Positions"), h("th", { class: "num" }, "Length"),
        h("th", { class: "num" }, "Codons"), h("th", {}, "Translation"), h("th", {}, ""))),
      h("tbody", {}, res.orfs.slice(0, 500).map((o) => h("tr", {},
        h("td", {}, o.frame), h("td", {}, posLink(viewer, o.start, o.end)), h("td", { class: "num" }, `${o.length_nt} nt`),
        h("td", { class: "num" }, o.codons), h("td", { class: "mono", style: { overflowWrap: "anywhere" } }, o.translation),
        h("td", {}, h("button", { class: "btn ghost small", type: "button", onclick: () => orfTrace(res, o, traceHost, viewer) }, "DFA trace"))))))),
    res.orfs.length > 500 ? h("p", { class: "small muted" }, `Showing the first 500 of ${res.orfs.length}. Export JSON for all.`) : null,
    traceHost);
}

async function orfTrace(res, orf, host, viewer) {
  fill(host, loading("Tracing the ORF DFA…"));
  try {
    const [tr, ex] = await Promise.all([
      api.post("/api/rna/orf-trace", { sequence: res.sequence, frame: orf.frame }),
      api.example("orf_dfa")]);
    const steps = tr.steps.filter((s) => s.pos >= orf.start - 3 && s.pos < orf.end + 3);
    const gHost = h("div", {});
    const expl = h("p", { class: "explain" }, "Select a codon to see the DFA state after reading it.");
    fill(host, h("h3", { style: { marginTop: "18px" } }, `ORF DFA trace, frame ${orf.frame}, positions ${orf.start}–${orf.end - 1}`),
      h("div", { class: "grid-2" }, gHost,
        h("div", {}, expl, h("div", { class: "table-wrap feature-list" }, h("table", { class: "trace" },
          h("thead", {}, h("tr", {}, h("th", {}, "Pos"), h("th", {}, "Codon"), h("th", {}, "Class"), h("th", {}, "State"), h("th", {}, "Action"))),
          h("tbody", {}, steps.map((s) => {
            const tr_ = h("tr", { tabindex: 0 }, h("td", {}, s.pos), h("td", { class: "mono" }, s.codon), h("td", {}, s.class),
              h("td", { class: "mono" }, `${s.state_before} → ${s.state_after}`), h("td", {}, s.action));
            const pick = () => {
              host.querySelectorAll("tr.current").forEach((x) => x.classList.remove("current"));
              tr_.classList.add("current");
              const from = s.state_before === "scan" ? "q0" : s.state_before;
              graph.highlight({ active: s.state_after === "scan" ? [] : [s.state_after],
                edges: s.action === "skip" ? [] : [{ from, to: s.state_after }] });
              expl.textContent = s.explanation;
              viewer.select(s.pos, s.pos + 3);
            };
            tr_.addEventListener("click", pick);
            tr_.addEventListener("keydown", (e) => { if (e.key === "Enter") pick(); });
            return tr_;
          })))))));
    const graph = new AutomatonGraph(gHost, { compact: true }).setSpec(ex.automaton);
  } catch (e) { fill(host, errorBox(e)); }
}

function motifTab(res, viewer) {
  const pipeHost = h("div", {});
  return h("div", {},
    h("p", { class: "small muted" }, "Each pattern is compiled by the project's regex engine: Thompson construction to an ε-NFA, then subset construction to a DFA, ",
      "which is run from every start position. Overlapping matches are all reported."),
    res.motifs.map((m) => h("details", { open: m.count > 0 && m.count < 40 },
      h("summary", {}, h("strong", {}, m.name), " ", h("code", {}, m.pattern), ` — ${m.count} match${m.count === 1 ? "" : "es"}`,
        m.custom ? " " : null, m.custom ? badge("custom") : null),
      h("p", { class: "small" }, m.note, ` Search DFA: ${m.dfa_states} states. `,
        h("button", { class: "linkish", type: "button", onclick: () => motifPipeline(m.pattern, pipeHost) }, "Show its automata")),
      m.count ? h("div", { class: "row small", style: { marginBottom: "10px" } },
        m.matches.slice(0, 300).map((x) => posLink(viewer, x.start, x.end, `${x.start}:${x.text}`)),
        m.truncated || m.matches.length > 300 ? h("span", { class: "muted" }, `… ${m.count} in total`) : null) : null)),
    pipeHost);
}

async function motifPipeline(pattern, host) {
  fill(host, loading("Compiling the pattern…"));
  try {
    const r = await api.post("/api/motif/compile", { pattern });
    const a = h("div", {}), b = h("div", {}), c = h("div", {});
    fill(host, h("h3", { style: { marginTop: "18px" } }, `/${r.pattern}/: regex → ε-NFA → DFA → minimal DFA`),
      h("p", { class: "small muted" }, r.note),
      h("div", { class: "grid-3" },
        h("div", {}, h("h4", {}, `Thompson ε-NFA (${r.counts.nfa} states)`), a),
        h("div", {}, h("h4", {}, `Subset-construction DFA (${r.counts.dfa})`), b),
        h("div", {}, h("h4", {}, `Minimized, completed (${r.counts.minimized})`), c)));
    new AutomatonGraph(a, { compact: true }).setSpec(r.nfa);
    new AutomatonGraph(b, { compact: true }).setSpec(r.dfa);
    new AutomatonGraph(c, { compact: true }).setSpec(r.minimized);
  } catch (e) { fill(host, errorBox(e)); }
}

function codonTab(res, viewer) {
  const list = (items, label) => h("div", {}, h("h4", {}, `${label} (${items.length})`),
    items.length ? h("div", { class: "row small feature-list" }, items.slice(0, 600).map((x) =>
      posLink(viewer, x.pos, x.pos + 3, `${x.codon}@${x.pos} f${x.frame}`))) : h("p", { class: "muted small" }, "None."));
  return h("div", {},
    h("p", { class: "small muted" }, "Every occurrence in every frame (frame = position mod 3). Select one to highlight it."),
    h("div", { class: "grid-2" }, list(res.codon_positions.start, "Start codons AUG"), list(res.codon_positions.stop, "Stop codons")));
}

function frameTab(res) {
  return h("div", { class: "grid-3" }, res.frames.map((f) => h("div", {},
    h("h4", {}, `Frame ${f.frame}`),
    h("p", { class: "small" }, `${f.codon_count} complete codon(s). ${f.incomplete_note}`),
    h("p", { class: "mono small", style: { overflowWrap: "anywhere" } }, f.preview.join(" "), f.codon_count > 40 ? " …" : ""),
    h("details", {}, h("summary", {}, "Codon usage"),
      h("div", { class: "table-wrap", style: { maxHeight: "260px" } }, h("table", {},
        h("tbody", {}, Object.entries(f.usage).map(([cod, n]) => h("tr", {}, h("td", { class: "mono" }, cod), h("td", { class: "num" }, n))))))))));
}

function languageTab(res) {
  return h("div", {},
    h("p", { class: "small muted" }, "Membership of the WHOLE sequence in languages recognised by the project's automata. ",
      "The last two rows are derived by the closure constructions (product and complement)."),
    h("div", { class: "table-wrap" }, h("table", {},
      h("thead", {}, h("tr", {}, h("th", {}, "Language"), h("th", {}, "Machine"), h("th", {}, "Result"), h("th", {}, ""))),
      h("tbody", {}, res.language_properties.map((p) => h("tr", {},
        h("td", {}, p.language), h("td", {}, p.machine),
        h("td", {}, h("strong", { class: p.accepted ? "good" : "bad" }, p.accepted ? "Accepted" : "Rejected")),
        h("td", {}, p.example && res.length <= 5000 ? h("a", { href: `#/playground?example=${p.example}&input=${encodeURIComponent(res.sequence)}` }, "Trace it")
          : p.example ? h("span", { class: "muted small" }, "too long to trace") : null)))))));
}

function transducerTab(res) {
  const t = res.transducers;
  const row = (label, value, note) => h("div", { style: { marginBottom: "14px" } }, h("h4", {}, label),
    h("div", { class: "transduced" }, value.length > 3000 ? value.slice(0, 3000) + " …" : value), h("p", { class: "small muted" }, note));
  return h("div", {},
    t.truncated_to ? notice("warn", null, `Computed on the first ${t.truncated_to} nt.`) : null,
    row("Complementary strand", t.complement, t.notes.complement),
    row("Reverse complement", t.reverse_complement, t.notes.reverse_complement),
    row("Codon boundaries (frame 0)", t.codon_boundaries, t.notes.codon_boundaries),
    row("Purine / pyrimidine encoding", t.ry, t.notes.ry));
}

function structureTab(res, viewer) {
  const host = h("div", {});
  const foldBtn = h("button", { class: "btn", type: "button" }, "Fold with the CFG");
  const hairBtn = h("button", { class: "btn ghost", type: "button" }, "Scan for hairpin stems (TM)");
  const tooLong = res.length > 200;
  foldBtn.disabled = tooLong;
  hairBtn.disabled = res.length > 1000;
  foldBtn.addEventListener("click", async () => {
    fill(host, loading("Parsing with the CYK-style dynamic program…"));
    try {
      const f = await busy(foldBtn, () => api.post("/api/advanced/fold", { sequence: res.sequence, min_loop: 3 }));
      fill(host, foldView(f));
    } catch (e) { fill(host, errorBox(e)); }
  });
  hairBtn.addEventListener("click", async () => {
    fill(host, loading("Running the Turing machine on every window…"));
    try {
      const r = await busy(hairBtn, () => api.post("/api/advanced/hairpins", { sequence: res.sequence, min_len: 4, max_len: 12 }));
      fill(host, h("p", {}, r.explanation),
        h("div", { class: "row small" }, r.hits.slice(0, 400).map((x) => posLink(viewer, x.start, x.end, `${x.start}:${x.text}`))),
        h("p", { class: "small muted" }, "Complementary palindromes are stem candidates only — see the Turing machine page for the step-by-step tape."));
    } catch (e) { fill(host, errorBox(e)); }
  });
  return h("div", {},
    notice("warn", "Experimental", "These models are educational. The CFG maximizes the number of nested base pairs and ignores energetics; it is not a validated structure predictor."),
    h("div", { class: "row" }, foldBtn, hairBtn,
      tooLong ? h("span", { class: "small muted" }, "Folding is O(n³) and limited to 200 nt.") : null),
    host);
}

export function foldView(f) {
  return h("div", { class: "stack", style: { marginTop: "12px" } },
    h("p", {}, h("strong", {}, `${f.pair_count} base pair(s)`), ` (minimum loop ${f.min_loop}). `,
      f.pair_types.filter((p) => p.type === "wobble").length ? `${f.pair_types.filter((p) => p.type === "wobble").length} G–U wobble pair(s).` : ""),
    h("div", { class: "dotbracket" }, f.sequence + "\n" + f.structure),
    arcDiagram(f.sequence.length, f.pairs, { sequence: f.sequence }),
    h("ul", { class: "small" }, f.explanation.map((x) => h("li", {}, x))),
    h("details", {}, h("summary", {}, `Leftmost derivation (${f.derivation.length - 1} steps${f.derivation_truncated ? ", truncated" : ""})`),
      h("div", { class: "table-wrap derivation" }, h("table", {}, h("tbody", {},
        f.derivation.map((d, i) => h("tr", {}, h("td", {}, i), h("td", {}, d.production), h("td", {}, "⇒ " + d.form))))))),
    f.dp_table ? h("details", {}, h("summary", {}, "Dynamic-programming table best[i][j]"), dpHeat(f.dp_table, f.sequence)) : null,
    notice("warn", null, f.disclaimer));
}

// ------------------------------------------------------------------ print

function printReport(res) {
  const root = document.getElementById("print-root");
  const c = res.composition;
  fill(root, 
    h("h1", {}, `RNA analysis report — ${res.record_id}`),
    h("p", {}, `Generated ${new Date().toLocaleString()} by RNA × Theory of Computation. Length ${res.length} nt; GC ${c.gc_percent}%.`),
    h("p", { class: "note" }, res.disclaimer),
    h("h2", {}, "Composition"),
    h("table", {}, h("tbody", {}, ["A", "C", "G", "U"].map((b) => h("tr", {}, h("td", {}, b), h("td", {}, c.counts[b]), h("td", {}, `${c.percent[b]}%`))))),
    h("h2", {}, `Open reading frames (${res.orfs.length})`),
    res.orfs.length ? h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "Frame"), h("th", {}, "Start"), h("th", {}, "End"), h("th", {}, "nt"), h("th", {}, "Translation"))),
      h("tbody", {}, res.orfs.slice(0, 200).map((o) => h("tr", {}, h("td", {}, o.frame), h("td", {}, o.start), h("td", {}, o.end - 1), h("td", {}, o.length_nt), h("td", {}, o.translation)))))
      : h("p", {}, "None found."),
    h("h2", {}, "Motifs"),
    h("table", {}, h("tbody", {}, res.motifs.map((m) => h("tr", {}, h("td", {}, m.name), h("td", {}, m.pattern), h("td", {}, m.count),
      h("td", {}, m.matches.slice(0, 20).map((x) => x.start).join(", ") + (m.count > 20 ? " …" : "")))))),
    h("h2", {}, "Formal language membership"),
    h("table", {}, h("tbody", {}, res.language_properties.map((p) => h("tr", {}, h("td", {}, p.language), h("td", {}, p.machine), h("td", {}, p.accepted ? "accepted" : "rejected"))))),
    h("h2", {}, "Sequence"),
    h("div", { class: "seqprint" }, res.sequence.length > 20000 ? res.sequence.slice(0, 20000) + " … (truncated)" : res.sequence));
  window.print();
}
