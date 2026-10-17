// The context-handoff view: what one session learned from another's work, and why it knew it.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var root = document.getElementById("handoff");
  var seen = null, signature = "";

  function chip(role) {
    var c = el("span", { "class": "chip" }, role);
    c.style.background = MC.color(role);
    return c;
  }

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
    box.appendChild(el("h3", {}, "Memory: own work vs learned from others"));
    var top = 1;
    state.roles.forEach(function (r) { top = Math.max(top, r.requests + r.decisions + r.edits + (learned[r.role] || 0)); });
    state.roles.forEach(function (r) {
      var own = r.requests + r.decisions + r.edits, got = learned[r.role] || 0;
      var row = el("div", { "class": "mem-row" }), bar = el("div", { "class": "bar" });
      row.appendChild(chip(r.role));
      var a = el("i"), b = el("i");
      a.style.width = (own / top * 100) + "%"; a.style.background = MC.color(r.role);
      b.style.width = (got / top * 100) + "%"; b.style.background = "#fbbf24";
      bar.appendChild(a); bar.appendChild(b); row.appendChild(bar);
      row.appendChild(el("span", {}, own + " own · " + got + " learned"));
      box.appendChild(row);
    });
    return box;
  }

  function card(h, fresh) {
    var c = el("div", { "class": "card" + (fresh ? " fresh" : "") });
    var route = el("div", { "class": "route" });
    route.appendChild(chip(h.reader)); route.appendChild(el("span", { "class": "arrow" }, "◀ read the work of"));
    route.appendChild(chip(h.author)); c.appendChild(route);
    c.appendChild(el("p", { "class": "asked" }, "Their request: " + h.request));
    if (!h.decisions.length) { c.appendChild(el("p", { "class": "none" }, "No decision was recorded for that work.")); return c; }
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
    cards.appendChild(el("h3", {}, "Hand-offs, newest first"));
    if (!state.handoffs.length) cards.appendChild(el("p", { "class": "none" }, "No session has read another's work yet."));
    state.handoffs.forEach(function (h) {
      var fresh = !firstDraw && !seen[key(h)]; seen[key(h)] = true;
      cards.appendChild(card(h, fresh));
    });
    root.appendChild(cards);
  }

  MC.views.handoff = { update: update };
})();
