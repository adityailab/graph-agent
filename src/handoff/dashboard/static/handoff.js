// The context-handoff view: what one session learned from another's work, and why it knew it.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var root = document.getElementById("handoff");
  var seen = null, signature = "", showAll = false;


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
    box.appendChild(el("h3", {}, "what each session knows"));
    var key = el("p", { "class": "key-row" }), own = el("span", {}, "its own work: requests, decisions and edits"), got = el("span", {}, "decisions it learned by reading other sessions' work");
    own.style.setProperty("--c", "linear-gradient(90deg, var(--blue), var(--purple), var(--amber))"); got.style.setProperty("--c", MC.css("--green"));
    key.appendChild(own); key.appendChild(got); box.appendChild(key);
    var top = 1;
    state.roles.forEach(function (r) { top = Math.max(top, r.requests + r.decisions + r.edits + (learned[r.role] || 0)); });
    state.roles.forEach(function (r) {
      var own = r.requests + r.decisions + r.edits, got = learned[r.role] || 0;
      var row = el("div", { "class": "mem-row" }), bar = el("div", { "class": "bar" });
      var name = el("span", { "class": "t-role" }, r.role); name.style.color = MC.color(r.role); row.appendChild(name);
      var a = el("i", { "class": "own" }), b = el("i", { "class": "got" });
      a.style.background = MC.color(r.role);
      a.style.width = (own / top * 100) + "%";
      b.style.width = (got / top * 100) + "%";
      bar.appendChild(a); bar.appendChild(b); row.appendChild(bar);
      row.appendChild(el("span", { "class": "dim" }, own + " own + " + got + " learned"));
      box.appendChild(row);
    });
    return box;
  }

  // One hand-off: a line (who read whom, how many decisions travelled), the rest on a click.
  function card(h, fresh, open) {
    var c = el("details", { "class": "card" + (fresh ? " fresh" : "") }), head = el("summary");
    if (open) c.open = true;
    var route = el("span", { "class": "route" });
    var rd = el("span", {}, h.reader), au = el("span", {}, h.author);
    rd.style.color = MC.color(h.reader); au.style.color = MC.color(h.author);
    route.appendChild(rd); route.appendChild(el("span", { "class": "arrow" }, " ← read the work of ")); route.appendChild(au);
    head.appendChild(route); head.appendChild(el("span", { "class": "dim" }, "  · " + h.decisions.length + (h.decisions.length === 1 ? " decision" : " decisions") + " travelled"));
    head.appendChild(el("span", { "class": "peek" }, h.request.length > 110 ? h.request.slice(0, 109) + "…" : h.request));
    c.appendChild(head);
    c.appendChild(MC.rich(el("p", { "class": "asked" }), "their request: " + h.request));
    if (!h.decisions.length) { c.appendChild(el("p", { "class": "none" }, "no decision was recorded for that work.")); return c; }
    var list = el("ul");
    h.decisions.forEach(function (d) {
      var li = MC.rich(el("li"), d.text);
      li.appendChild(MC.rich(el("div", { "class": "why" }), "why: " + d.reason));
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
    var SHOWN = 5;  // the newest few; the rest behind one button
    var more = el("button", { type: "button", "class": "more" }, "show " + Math.max(0, state.handoffs.length - SHOWN) + " older");
    state.handoffs.forEach(function (h, i) {
      var fresh = !firstDraw && !seen[key(h)]; seen[key(h)] = true;
      var c = card(h, fresh, i === 0);
      if (i >= SHOWN && !showAll) c.hidden = true;
      cards.appendChild(c);
    });
    if (state.handoffs.length > SHOWN && !showAll) {
      more.addEventListener("click", function () { showAll = true; signature = ""; update(state); });
      cards.appendChild(more);
    }
    root.appendChild(cards);
  }

  MC.views.handoff = { update: update };
})();
