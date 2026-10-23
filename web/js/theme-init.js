// Applied before first paint so a saved theme never flashes.
(function () {
  try {
    var t = JSON.parse(localStorage.getItem("rnatoc:theme") || '"system"');
    if (t === "light" || t === "dark") document.documentElement.setAttribute("data-theme", t);
  } catch (e) { /* storage unavailable: follow the system theme */ }
})();
