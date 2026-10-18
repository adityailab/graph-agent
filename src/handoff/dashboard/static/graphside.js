// The graph's side panel before anything is selected: how big it is, where to start, the sessions
// to narrow it to, and what each kind of relationship means.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;

  function plural(n, w) { return n + " " + w + (n === 1 ? "" : "s"); }

  function pick(colour, lead, rest, text, id, go) {
    var b = el("button", { type: "button", "class": "pick" }), m = el("span", { "class": "m" });
    b.style.setProperty("--c", colour); m.appendChild(el("b", {}, lead)); m.appendChild(document.createTextNode(" · " + rest));
    b.appendChild(m); b.appendChild(el("span", { "class": "t" }, text));
    b.addEventListener("click", function () { go(id); });
    return b;
  }

  // Three places worth opening first: the most-read decision, an open need, a replaced decision.
  function picks(m, go) {
    var out = [], ids = Object.keys(m.nodes), nodes = ids.map(function (id) { return m.nodes[id]; });
    var read = nodes.filter(function (n) { return m.readers[n.id]; }).sort(function (a, b) { return Object.keys(m.readers[b.id]).length - Object.keys(m.readers[a.id]).length; })[0];
    if (read) out.push(pick(MC.color(read.role), "most read", read.role + " · read by " + Object.keys(m.readers[read.id]).join(", "), read.text, read.id, go));
    var need = nodes.filter(function (n) { return n.kind === "Need" && n.status === "open"; }).sort(function (a, b) { return b.at - a.at; })[0];
    if (need) out.push(pick(MC.css("--red"), "open need", need.role + (need.for_role ? " → " + need.for_role : ""), need.text, need.id, go));
    var old = ids.filter(function (id) { return m.replacedBy[id]; })[0];
    if (old) out.push(pick(MC.color(m.nodes[old].role), "replaced", m.nodes[old].role, m.nodes[old].text + " → " + m.nodes[m.replacedBy[old]].text, old, go));
    return out;
  }

  function sessions(m, s, on) {
    var totals = {}, box = el("div", { "class": "chips" });
    Object.keys(m.nodes).forEach(function (id) { var g = MC.graphModel.group(m, m.nodes[id], s.by); if (m.nodes[id].kind !== "Session") totals[g] = (totals[g] || 0) + 1; });
    Object.keys(totals).sort().forEach(function (g) {
      var b = el("button", { type: "button", "aria-pressed": String(s.only === g) }, g + " " + totals[g]);
      b.style.setProperty("--c", s.by === "session" && g !== "shared" ? MC.color(g) : MC.css("--dim")); b.addEventListener("click", function () { on.only(g); }); box.appendChild(b);
    });
    return box;
  }

  function legend(m, on) {
    var tally = {}, ul = el("ul", { "class": "rels" });
    m.edges.forEach(function (e) { tally[e.kind] = (tally[e.kind] || 0) + 1; });
    Object.keys(tally).sort(function (a, b) { return tally[b] - tally[a]; }).forEach(function (k) {
      var li = el("li"), i = el("i");
      li.style.setProperty("--c", on.edgeColour(k)); li.appendChild(i); li.appendChild(document.createTextNode(k.toLowerCase().replace("_", " ")));
      li.appendChild(el("b", {}, String(tally[k]))); ul.appendChild(li);
    });
    return ul;
  }

  function section(title, note) {
    var s = el("div", { "class": "side-sec" }), h = el("h3", {}, title);
    if (note) h.appendChild(el("span", { "class": "n" }, note));
    s.appendChild(h);
    return s;
  }

  // `s` is the view's state; `on.select(id)` opens a node, `on.only(group)` narrows to one group.
  function render(box, m, s, on) {
    MC.clear(box);
    var nodes = Object.keys(m.nodes).length, decisions = Object.keys(m.nodes).filter(function (id) { return m.nodes[id].kind === "Decision"; }).length;
    var travelled = Object.keys(m.readers).reduce(function (t, id) { return t + Object.keys(m.readers[id]).length; }, 0);
    var sum = el("p", { "class": "sumline" }, nodes + " nodes · " + m.edges.length + " relationships"), sec = el("div", { "class": "side-sec" });
    var roles = Object.keys(m.nodes).filter(function (id) { return m.nodes[id].kind === "Session"; }).length;
    if (roles) sum.appendChild(el("small", {}, plural(roles, "session") + " · " + plural(decisions, "decision") + " · " + travelled + " travelled between sessions"));
    sec.appendChild(sum); box.appendChild(sec);
    var start = picks(m, on.select);
    if (start.length) { var st = section("start here"); start.forEach(function (p) { st.appendChild(p); }); box.appendChild(st); }
    if (roles) { var ss = section(s.by === "topic" ? "topics" : "sessions", "click to show only one"); ss.appendChild(sessions(m, s, on)); box.appendChild(ss); }
    var fold = el("details", { "class": "fold" }); fold.appendChild(el("summary", {}, "legend and counts · " + plural(Object.keys(m.edges.reduce(function (o, e) { o[e.kind] = 1; return o; }, {})).length, "relationship")));
    fold.appendChild(legend(m, on)); box.appendChild(fold);
  }

  window.MC.graphSide = { render: render };
})();
