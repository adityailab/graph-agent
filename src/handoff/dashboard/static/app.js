// Polls the dashboard's state, tells every view what is new, and runs the tabs, feed and replay.
(function () {
  "use strict";
  var MC = window.MC, POLL_MS = 1500;
  var VIEWS = ["orchestration", "handoff", "memory", "graph", "tracks", "log", "ask"];
  var seenEvents = null, state = null, current = "orchestration";
  var ticker = document.getElementById("ticker"), status = document.getElementById("status");

  function setView(name) {
    current = name;
    document.querySelectorAll(".tabs button").forEach(function (b) { b.setAttribute("aria-current", String(b.getAttribute("data-view") === name)); });
    VIEWS.forEach(function (v) { document.getElementById("view-" + v).hidden = v !== name; });
    MC.views.graph.setVisible(name === "graph");
    history.replaceState(null, "", "#" + name);
  }

  MC.setView = setView;

  function addToTicker(ev, fresh) {
    var li = MC.el("li", { "class": fresh ? "fresh" : "" });
    var meta = MC.el("div", { "class": "meta" });
    meta.appendChild(MC.el("span", { "class": "t" }, MC.clock(ev.at)));
    meta.appendChild(MC.el("span", { "class": "kind k-" + ev.kind.toLowerCase() }, ev.kind.toLowerCase()));
    var who = MC.el("span", { "class": "who" }, ev.role); who.style.color = MC.color(ev.role);
    meta.appendChild(who); li.appendChild(meta);
    li.appendChild(MC.clamp(MC.rich(MC.el("span", { "class": "text" }), ev.text)));
    ticker.insertBefore(li, ticker.firstChild);
    while (ticker.children.length > 60) ticker.removeChild(ticker.lastChild);
  }

  function apply(s) {
    MC.words(s.roles.map(function (r) { return r.role; }));
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
    document.getElementById("graph-ref").textContent = s.graph;
    document.getElementById("clock").textContent = MC.clock(s.now);
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

  document.addEventListener("keydown", function (ev) {
    var names = VIEWS, i = Number(ev.key) - 1, typing = /^(INPUT|TEXTAREA)$/.test(ev.target.tagName);
    if (!typing && !ev.metaKey && !ev.ctrlKey && !ev.altKey && i >= 0 && i < names.length) setView(names[i]);
  });

  // Back/forward and pasted #links change the hash without a reload: follow them.
  window.addEventListener("hashchange", function () {
    var name = location.hash.slice(1);
    if (VIEWS.indexOf(name) >= 0 && name !== current) setView(name);
  });

  setView(VIEWS.indexOf(location.hash.slice(1)) >= 0 ? location.hash.slice(1) : current);
  poll();
})();
