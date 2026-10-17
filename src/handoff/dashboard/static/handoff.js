// The context-handoff view: what one session learned from another's work, and why it knew it.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var root = document.getElementById("handoff");
  var seen = null, signature = "";


  function stat(label, value) {
    var box = el("div", { "class": "stat" }), n = el("b", {}, "0");
    box.appendChild(n); box.appendChild(el("span", {}, label));
    MC.countTo(n, value, "handoff:" + label);
    return box;
  }

  function memoryRows(state) {
    var learned = Object.create(null);
    state.handoffs.forEach(function (h) { learned[h.reader] = (learned[h.reader] || 0) + h.decisions.length; });
    var box = el("div", { "class": "memory" });
    box.appendChild(el("h3", {}, "memory: own work (solid) vs learned from others (hatched)"));
    var top = 1;
    state.roles.forEach(function (r) { top = Math.max(top, r.requests + r.decisions + r.edits + (learned[r.role] || 0)); });
    state.roles.forEach(function (r) {
      var own = r.requests + r.decisions + r.edits, got = learned[r.role] || 0;
      var row = el("div", { "class": "mem-row" }), bar = el("div", { "class": "bar" });
      row.appendChild(el("span", {}, r.role));
      var a = el("i", { "class": "own" }), b = el("i", { "class": "got" });
      a.style.width = (own / top * 100) + "%";
      b.style.width = (got / top * 100) + "%";
      bar.appendChild(a); bar.appendChild(b); row.appendChild(bar);
      row.appendChild(el("span", {}, own + " own · " + got + " learned"));
      box.appendChild(row);
    });
    return box;
  }

  function card(h, fresh) {
    var c = el("div", { "class": "card" + (fresh ? " fresh" : "") });
    var route = el("div", { "class": "route" });
    route.textContent = h.reader + " ← read the work of " + h.author; c.appendChild(route);
    c.appendChild(el("p", { "class": "asked" }, "their request: " + h.request));
    if (!h.decisions.length) { c.appendChild(el("p", { "class": "none" }, "no decision was recorded for that work.")); return c; }
    var list = el("ul");
    h.decisions.forEach(function (d) {
      var li = el("li", {}, d.text);
      li.appendChild(el("div", { "class": "why" }, "why: " + d.reason));
      list.appendChild(li);
    });
    c.appendChild(list);
    return c;
  }

  function update(state) {
    var key = function (h) { return h.reader + ">" + h.author + "@" + h.at; };
    var sig = JSON.stringify([state.handoffs, state.roles.map(function (r) { return [r.role, r.requests, r.decisions, r.edits]; }), state.flows]);
    if (sig === signature) return;
    signature = sig;
    var firstDraw = seen === null; seen = seen || {};
    MC.clear(root);
    var carried = state.handoffs.reduce(function (n, h) { return n + h.decisions.length; }, 0);
    var sent = state.flows.reduce(function (n, f) { return n + (f.kind === "read" || f.kind === "need" ? 0 : f.count); }, 0);
    var stats = el("div", { "class": "stats" });
    stats.appendChild(stat("reads of another session's work", state.handoffs.length));
    stats.appendChild(stat("decisions that travelled, with their reasons", carried));
    stats.appendChild(stat("messages between sessions", sent));
    root.appendChild(stats);
    root.appendChild(memoryRows(state));
    var cards = el("div", { "class": "cards" });
    cards.appendChild(el("h3", {}, "hand-offs, newest first"));
    if (!state.handoffs.length) cards.appendChild(el("p", { "class": "none" }, "no session has read another's work yet."));
    state.handoffs.forEach(function (h) {
      var fresh = !firstDraw && !seen[key(h)]; seen[key(h)] = true;
      cards.appendChild(card(h, fresh));
    });
    root.appendChild(cards);
  }

  MC.views.handoff = { update: update };
})();
