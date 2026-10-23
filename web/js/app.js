// Hash router + app chrome (theme, mobile navigation, server status).

import { h, clear, store, fill } from "./dom.js";
import { errorBox } from "./components.js";
import * as api from "./api.js";

const routes = {
  "": () => import("./views/overview.js"),
  rna: () => import("./views/rna.js"),
  playground: () => import("./views/playground.js"),
  convert: () => import("./views/convert.js"),
  minimize: () => import("./views/minimize.js"),
  verify: () => import("./views/verify.js"),
  history: () => import("./views/history.js"),
  learn: () => import("./views/learn.js"),
};

const main = document.getElementById("main");
let renderToken = 0;

export function navigate(route, params = {}) {
  const q = new URLSearchParams(params).toString();
  location.hash = `#/${route}${q ? "?" + q : ""}`;
}

async function render() {
  const raw = location.hash.replace(/^#\/?/, "");
  const [path, query] = raw.split("?");
  const route = routes[path] ? path : "";
  const params = Object.fromEntries(new URLSearchParams(query || ""));
  const token = ++renderToken;
  document.querySelectorAll(".sidebar a").forEach((a) => {
    if (a.dataset.route === route) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  closeNav();
  try {
    const mod = await routes[route]();
    if (token !== renderToken) return;
    clear(main);
    const view = h("div", { class: "view" });
    main.append(view);
    await mod.render(view, params);
    document.title = `${mod.title ? mod.title + " — " : ""}RNA × Theory of Computation`;
    main.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  } catch (err) {
    console.error(err);
    fill(main, h("div", { class: "view" }, errorBox(err)));
  }
}

// ------------------------------------------------------------------ theme
const themeBtn = document.getElementById("theme-toggle");
function applyTheme(t) {
  if (t === "system") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", t);
  themeBtn.textContent = `Theme: ${t}`;
  store.set("theme", t);
}
themeBtn.addEventListener("click", () => {
  const order = ["system", "light", "dark"];
  applyTheme(order[(order.indexOf(store.get("theme", "system")) + 1) % 3]);
});
applyTheme(store.get("theme", "system"));

// ------------------------------------------------------------------ mobile nav
const navToggle = document.querySelector(".nav-toggle");
const sidebar = document.getElementById("sidebar");
function closeNav() { sidebar.classList.remove("open"); navToggle.setAttribute("aria-expanded", "false"); }
navToggle.addEventListener("click", () => {
  const open = !sidebar.classList.contains("open");
  sidebar.classList.toggle("open", open);
  navToggle.setAttribute("aria-expanded", String(open));
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeNav(); });

// ------------------------------------------------------------------ server status
const statusEl = document.getElementById("server-status");
async function checkServer() {
  try {
    const r = await api.get("/api/health");
    statusEl.textContent = `Server v${r.version} online`;
    statusEl.className = "server-status ok";
  } catch {
    statusEl.textContent = "Server offline";
    statusEl.className = "server-status bad";
  }
}
checkServer();
setInterval(checkServer, 30000);

window.addEventListener("hashchange", render);
render();
