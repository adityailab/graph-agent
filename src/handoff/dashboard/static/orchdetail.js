// What sits under the orchestration drawing: a status line, the chosen session (its last message,
// its recent work as cards) and a folded table of every line between sessions.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el, LONG = 150;

  function chip(role, solid) {
    var c = el("span", { "class": "chip" + (solid ? " solid" : "") }, role); c.style.setProperty("--c", MC.color(role)); return c;
  }
  function plural(n, word) { return n + " " + word + (n === 1 ? "" : "s"); }

  // An event split into who it points at and what it says, for "to backend" / "from deploy" heads.
  function parts(ev) {
    var r = MC.route(ev), other = null, way = "", body = ev.text;
    if (r && r.from === ev.role) { way = "to"; other = r.to; body = body.replace(/^(to|from) [\w-]+:\s*/, ""); }
    else if (r) { way = "from"; other = r.from; body = body.replace(/^[\w-]+ work:\s*/, ""); }
    return { way: way, other: other, body: body };
  }

  function head(ev, p) {
    var h = el("div", { "class": "link-head" });
    h.appendChild(el("span", { "class": "kind k-" + ev.kind.toLowerCase() }, ev.kind.toLowerCase()));
    if (p.other) { h.appendChild(el("span", { "class": "dim" }, p.way)); h.appendChild(chip(p.other)); }
    h.appendChild(el("span", { "class": "when" }, MC.clock(ev.at)));
    return h;
  }

  function more(text) {
    var b = el("button", { type: "button", "class": "more" }, "read all ▸");
    b.addEventListener("click", function () { var open = text.classList.toggle("open"); b.textContent = open ? "fold ◂" : "read all ▸"; });
    return b;
  }

  function feedCard(ev) {
    var p = parts(ev), c = el("article", { "class": "link-card" }), text = MC.clamp(MC.rich(el("p", { "class": "full" }), p.body));
    if (ev.kind === "edited") text.classList.add("t-path");
    c.appendChild(head(ev, p)); c.appendChild(text);
    if (p.body.length > LONG) c.appendChild(more(text));
    return c;
  }

  function lastMessage(role, mine) {
    var sent = mine.filter(function (e) { var r = MC.route(e); return r && r.from === role && e.kind !== "NEEDS"; })[0];
    if (!sent) return { node: null, ev: null };
    var p = parts(sent), box = el("div", { "class": "lastmsg" });
    box.style.setProperty("--c", MC.color(role)); box.appendChild(head(sent, p)); box.appendChild(MC.clamp(MC.rich(el("p", { "class": "full" }), p.body)));
    return { node: box, ev: sent };
  }

  function sessionHead(state, r, pick) {
    var h = el("div", { "class": "sess-head" }), counts = el("span", { "class": "counts" }), nav = el("span", { "class": "nav", role: "group", "aria-label": "Choose session" });
    counts.appendChild(el("span", {}, state.now - r.last_seen_at <= 120000 ? "active" : "idle"));
    [["asks", r.requests], ["decisions", r.decisions], ["edits", r.edits]].forEach(function (c) {
      var s = el("span"); s.appendChild(el("b", {}, String(c[1]))); s.appendChild(document.createTextNode(c[0])); counts.appendChild(s);
    });
    if (r.open_needs) counts.appendChild(el("span", { "class": "k-need" }, plural(r.open_needs, "open need")));
    state.roles.forEach(function (o) {
      var b = el("button", { type: "button", "aria-pressed": String(o.role === r.role) }, o.role);
      b.addEventListener("click", function () { pick(o.role); }); nav.appendChild(b);
    });
    h.appendChild(chip(r.role, true)); h.appendChild(counts); h.appendChild(nav);
    return h;
  }

  function show(box, state, role, pick) {
    MC.clear(box);
    var r = state.roles.filter(function (x) { return x.role === role; })[0];
    if (!r) return;
    var mine = state.events.filter(function (e) { return e.role === role; }).reverse(), last = lastMessage(role, mine);
    var section = el("section", { "aria-label": role + " session" });
    section.appendChild(sessionHead(state, r, pick));
    if (last.node) section.appendChild(last.node);
    var feed = el("div", { "class": "feed" });
    mine.filter(function (e) { return e !== last.ev; }).slice(0, 6).forEach(function (e) { feed.appendChild(feedCard(e)); });
    section.appendChild(el("h3", {}, "recent from " + role)); section.appendChild(feed);
    if (!mine.length) feed.appendChild(el("p", { "class": "dim" }, "nothing recorded yet"));
    box.appendChild(section);
  }

  function status(box, state) {
    MC.clear(box);
    var n = state.roles.length, active = state.roles.filter(function (r) { return state.now - r.last_seen_at <= 120000; }).length;
    var needy = state.roles.filter(function (r) { return r.open_needs > 0; }), open = needy.reduce(function (s, r) { return s + r.open_needs; }, 0);
    var a = el("span"); a.appendChild(el("b", {}, String(n))); a.appendChild(document.createTextNode(" " + (n === 1 ? "session" : "sessions") + " · " + (active ? active + " active" : "all idle")));
    box.appendChild(a);
    if (open) box.appendChild(el("span", { "class": "need" }, "● " + plural(open, "open need") + " (" + needy.map(function (r) { return r.role; }).join(", ") + ")"));
    box.appendChild(el("span", {}, plural(state.flows.length, "line") + " between sessions"));
  }

  // Every (from, to) pair once, with what moved on it.
  function table(box, summary, flows) {
    MC.clear(box); summary.textContent = "all lines between sessions (" + flows.length + ")";
    var pairs = Object.create(null);
    flows.forEach(function (f) { (pairs[f.source + ">" + f.target] = pairs[f.source + ">" + f.target] || []).push(f); });
    var t = el("table", { "class": "lines-table" }), hr = el("tr"), tb = el("tbody");
    ["from", "to", "what moved"].forEach(function (c) { hr.appendChild(el("th", { scope: "col" }, c)); });
    t.appendChild(el("thead")).appendChild(hr); t.appendChild(tb);
    Object.keys(pairs).sort().forEach(function (key) {
      var row = el("tr"), cell = el("td"), ends = key.split(">");
      row.appendChild(el("td", {}, ends[0])); row.appendChild(el("td", {}, ends[1]));
      pairs[key].forEach(function (f) { cell.appendChild(el("b", { "class": "k-" + f.kind }, f.kind.replace("_", " ") + " ×" + f.count)); });
      row.appendChild(cell); tb.appendChild(row);
    });
    if (flows.length) box.appendChild(t);
  }

  window.MC.orchDetail = { show: show, status: status, table: table };
})();
