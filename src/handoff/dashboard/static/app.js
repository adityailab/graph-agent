// Polls the dashboard's state, tells every view what is new, and runs the tabs, feed and replay.
(function () {
  "use strict";
  var MC = window.MC, POLL_MS = 1500;
  var seenEvents = null, state = null, current = "orchestration";
  var ticker = document.getElementById("ticker"), status = document.getElementById("status");

  function setView(name) {
    current = name;
    document.querySelectorAll(".tabs button").forEach(function (b) { b.setAttribute("aria-current", String(b.getAttribute("data-view") === name)); });
    ["orchestration", "handoff", "graph", "tracks"].forEach(function (v) { document.getElementById("view-" + v).hidden = v !== name; });
    MC.views.graph.setVisible(name === "graph");
    history.replaceState(null, "", "#" + name);
  }

  function addToTicker(ev, fresh) {
    var li = MC.el("li", { "class": fresh ? "fresh" : "" });
    li.style.borderLeftColor = MC.color(ev.role);
    li.appendChild(MC.el("span", { "class": "kind" }, ev.kind));
    var who = MC.el("span", { "class": "who" }, ev.role); who.style.color = MC.color(ev.role);
    li.appendChild(who); li.appendChild(MC.el("span", {}, ev.text.length > 140 ? ev.text.slice(0, 139) + "…" : ev.text));
    ticker.insertBefore(li, ticker.firstChild);
    while (ticker.children.length > 40) ticker.removeChild(ticker.lastChild);
  }

  function apply(s) {
    // The baseline is the first snapshot with events, so a graph that appears later is not replayed.
    var first = seenEvents === null && s.events.length > 0;
    if (first) seenEvents = {};
    var seen = seenEvents || {};
    var fresh = s.events.filter(function (e) { return !seen[e.key]; });
    fresh.forEach(function (e) { seen[e.key] = true; });
    if (first) s.events.slice(-25).forEach(function (e) { addToTicker(e, false); });
    else fresh.forEach(function (e) { addToTicker(e, true); });
    var animate = first ? [] : fresh.slice(-8);
    Object.keys(MC.views).forEach(function (name) { MC.views[name].update(s, animate); });
    document.getElementById("graph-name").textContent = s.graph;
    status.textContent = s.error ? s.error : "live"; status.className = "status " + (s.error ? "down" : "live");
    state = s;
  }

  function poll() {
    fetch("/api/state", { cache: "no-store" }).then(function (r) { return r.json(); }).then(apply)
      .catch(function (e) { status.textContent = "dashboard error: " + e.message; status.className = "status down"; })
      .then(function () { setTimeout(poll, POLL_MS); });
  }

  document.querySelectorAll(".tabs button").forEach(function (b) { b.addEventListener("click", function () { setView(b.getAttribute("data-view")); }); });
  document.getElementById("replay").addEventListener("click", function () {
    if (!state) return;
    setView("orchestration");
    state.events.slice(-12).forEach(function (e, i) { setTimeout(function () { MC.views.orchestration.play(e); addToTicker(e, true); }, i * 700); });
  });

  setView(["orchestration", "handoff", "graph", "tracks"].indexOf(location.hash.slice(1)) >= 0 ? location.hash.slice(1) : current);
  poll();
})();
