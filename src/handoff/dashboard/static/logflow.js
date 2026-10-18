// The log as a time-aligned swimlane: one column per session, one row per moment. An empty cell
// means that session did nothing then, and a "n min later" rule marks a quiet stretch. A click opens
// an event as a card with buttons to its session's earlier or later event. Text goes in as textContent.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el, ROWS = 24;
  var chart = document.getElementById("flow"), detail = document.getElementById("flow-detail");
  var bar = document.getElementById("log-kinds");
  var KINDS = ["asked", "decided", "edited", "message", "needs", "read"];
  var events = [], selected = null, seen = null, signature = "", last = null;
  var shownRows = ROWS, off = Object.create(null);

  function chip(role) {
    var c = el("span", { "class": "chip" }, role); c.style.setProperty("--c", MC.color(role)); return c;
  }
  function kindOf(e) { return e.kind.toLowerCase(); }
  function visible() { return events.filter(function (e) { return !off[kindOf(e)]; }); }
  function sameLane(e) { return visible().filter(function (x) { return x.role === e.role; }); }

  function show(e) {
    selected = e.key; MC.clear(detail);
    var card = el("div", { "class": "node-card" }), head = el("div", { "class": "link-head" });
    card.style.setProperty("--c", MC.color(e.role));
    head.appendChild(chip(e.role));
    head.appendChild(el("span", { "class": "kind k-" + kindOf(e) }, kindOf(e)));
    head.appendChild(el("span", { "class": "when" }, MC.clock(e.at)));
    card.appendChild(head); card.appendChild(MC.rich(el("p", { "class": "full" }), e.text));
    detail.appendChild(card);
    var lane = sameLane(e), i = lane.indexOf(e), steps = el("div", { "class": "flow-steps" });
    [["← earlier in " + e.role, lane[i + 1]], ["later in " + e.role + " →", lane[i - 1]]].forEach(function (s) {
      var b = el("button", { type: "button", "class": "connect" }, s[0]); b.disabled = !s[1];
      b.addEventListener("click", function () { show(s[1]); });
      steps.appendChild(b);
    });
    detail.appendChild(steps);
    chart.querySelectorAll(".flow-node").forEach(function (n) {
      n.classList.toggle("on", n.getAttribute("data-key") === e.key);
    });
  }

  function node(e, col, row) {
    var n = el("button", { type: "button", "class": "flow-node k-" + kindOf(e) + (seen && !seen[e.key] ? " fresh" : ""), "data-key": e.key });
    n.style.gridColumn = String(col); n.style.gridRow = String(row);
    n.appendChild(el("span", { "class": "dot" }));
    n.appendChild(el("span", { "class": "when" }, MC.clock(e.at)));
    n.appendChild(el("span", { "class": "kind" }, kindOf(e)));
    n.appendChild(el("span", { "class": "peek" }, e.text.replace(/\s+/g, " ")));
    n.addEventListener("click", function () { show(e); });
    return n;
  }

  function drawHeads(roles) {
    roles.forEach(function (role, c) {
      var count = events.filter(function (e) { return e.role === role; }).length;
      var head = el("div", { "class": "flow-head" }); head.appendChild(chip(role));
      head.appendChild(el("span", { "class": "dim" }, " " + count + (count === 1 ? " event" : " events")));
      head.style.gridColumn = String(c + 1); head.style.gridRow = "1"; chart.appendChild(head);
    });
  }

  function draw(roles) {
    MC.clear(chart);
    chart.style.gridTemplateColumns = "repeat(" + roles.length + ", minmax(180px, 1fr))";
    var all = MC.logrows.pack(visible()), rows = all.slice(0, shownRows), r = 2;
    drawHeads(roles);
    rows.forEach(function (row, i) {
      roles.forEach(function (role, c) {
        if (row.cells[role]) chart.appendChild(node(row.cells[role], c + 1, r));
        else { var s = el("span", { "class": "slot" }); s.style.gridColumn = String(c + 1); s.style.gridRow = String(r); chart.appendChild(s); }
      });
      r++;
      if (row.gap && i < rows.length - 1) {
        var gap = el("div", { "class": "gap" }, MC.logrows.span(row.gap) + " earlier, nothing in between");
        gap.style.gridColumn = "1 / -1"; gap.style.gridRow = String(r++); chart.appendChild(gap);
      }
    });
    if (all.length > rows.length) {
      var more = el("button", { type: "button", "class": "more" }, "show " + (all.length - rows.length) + " older moments");
      more.style.gridColumn = "1 / -1"; more.style.gridRow = String(r);
      more.addEventListener("click", function () { shownRows += ROWS; refresh(); });
      chart.appendChild(more);
    }
    roles.forEach(function (role, c) {
      var line = el("div", { "class": "flow-line" }); line.style.gridColumn = String(c + 1);
      line.style.gridRow = "2 / " + (r + 1); line.style.setProperty("--c", MC.color(role));
      chart.insertBefore(line, chart.firstChild);
    });
  }

  function drawKinds() {
    MC.clear(bar); bar.appendChild(el("span", { "class": "lbl" }, "show"));
    KINDS.forEach(function (k) {
      var n = events.filter(function (e) { return kindOf(e) === k; }).length;
      var b = el("button", { type: "button", "class": "kf k-" + k, "aria-pressed": off[k] ? "false" : "true" }, k + " ");
      b.appendChild(el("i", {}, String(n)));
      b.addEventListener("click", function () { off[k] = !off[k]; refresh(); });
      bar.appendChild(b);
    });
  }

  function refresh() {
    var roles = Object.keys(events.reduce(function (m, e) { m[e.role] = 1; return m; }, {})).sort();
    drawKinds(); draw(roles);
    var shown = visible(), keep = shown.filter(function (e) { return e.key === selected; })[0] || shown[0];
    if (keep) show(keep); else { MC.clear(detail); detail.appendChild(el("p", { "class": "dim" }, "every kind is hidden")); }
  }

  function update(state) {
    last = state;
    var recent = state.events.slice().reverse();  // newest first
    var sig = recent.map(function (e) { return e.key; }).join("|");
    if (sig === signature) return;
    events = recent; signature = sig;
    if (!events.length) { MC.clear(chart); chart.appendChild(el("p", { "class": "dim" }, "nothing has landed in the graph yet")); return; }
    refresh();
    seen = seen || {};
    events.forEach(function (e) { seen[e.key] = true; });
  }

  MC.views.log = { update: update };
})();
