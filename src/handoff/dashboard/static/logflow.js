// The log as a workflow: one column per session, one dot per event, newest on top and rows shared
// across columns so what happened first reads off the page. A click opens that event as a card,
// with buttons to step to the same session's earlier or later event. Text goes in as textContent.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el, SHOWN = 40;
  var chart = document.getElementById("flow"), detail = document.getElementById("flow-detail");
  var events = [], selected = null, seen = null, signature = "";

  function chip(role) {
    var c = el("span", { "class": "chip" }, role); c.style.setProperty("--c", MC.color(role)); return c;
  }

  function sameLane(e) { return events.filter(function (x) { return x.role === e.role; }); }

  function show(e) {
    selected = e.key; MC.clear(detail);
    var card = el("div", { "class": "node-card" }), head = el("div", { "class": "link-head" });
    head.appendChild(chip(e.role));
    head.appendChild(el("span", { "class": "kind k-" + e.kind.toLowerCase() }, e.kind.toLowerCase()));
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
    chart.querySelectorAll(".flow-node").forEach(function (n) { n.classList.toggle("on", n.getAttribute("data-key") === e.key); });
  }

  function draw(roles) {
    MC.clear(chart);
    chart.style.gridTemplateColumns = "repeat(" + roles.length + ", minmax(160px, 1fr))";
    roles.forEach(function (role, c) {
      var head = el("div", { "class": "flow-head" }); head.appendChild(chip(role)); head.style.gridColumn = String(c + 1); head.style.gridRow = "1";
      chart.appendChild(head);
      var line = el("div", { "class": "flow-line" }); line.style.gridColumn = String(c + 1); line.style.gridRow = "2 / span " + Math.max(1, events.length);
      line.style.setProperty("--c", MC.color(role)); chart.appendChild(line);
    });
    events.forEach(function (e, r) {
      var node = el("button", { type: "button", "class": "flow-node k-" + e.kind.toLowerCase() + (seen && !seen[e.key] ? " fresh" : ""), "data-key": e.key });
      node.style.gridColumn = String(roles.indexOf(e.role) + 1); node.style.gridRow = String(r + 2);
      node.appendChild(el("span", { "class": "dot" }));
      node.appendChild(el("span", { "class": "when" }, MC.clock(e.at) + " "));
      node.appendChild(el("span", { "class": "kind" }, e.kind.toLowerCase()));
      node.appendChild(el("span", { "class": "peek" }, e.text.replace(/\s+/g, " ")));
      node.addEventListener("click", function () { show(e); });
      chart.appendChild(node);
    });
  }

  function update(state) {
    var recent = state.events.slice(-SHOWN).reverse();
    var sig = recent.map(function (e) { return e.key; }).join("|");
    if (sig === signature) return;
    events = recent; signature = sig;
    var roles = Object.keys(events.reduce(function (m, e) { m[e.role] = 1; return m; }, {})).sort();
    if (!roles.length) { MC.clear(chart); chart.appendChild(el("p", { "class": "dim" }, "nothing has landed in the graph yet")); return; }
    draw(roles);
    seen = seen || {};
    events.forEach(function (e) { seen[e.key] = true; });
    var keep = events.filter(function (e) { return e.key === selected; })[0] || events[0];
    show(keep);
  }

  MC.views.log = { update: update };
})();
