// The selected node as a card, who learned it, and its connections as cards of their own, grouped
// as came from / went to / touched, each with a connect button that walks the graph one link.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el, SHOWN = 8;
  var GROUPS = [["came from", "came"], ["went to", "went"], ["touched", "touched"]];

  function label(kind) { return kind.toLowerCase().replace("_", " "); }
  function chipOf(n) { return MC.chip(n.kind.toLowerCase() + (n.role ? " · " + n.role : ""), n.role ? MC.color(n.role) : null); }
  function when(n) { return n.at ? el("span", { "class": "when" }, MC.clock(n.at)) : null; }

  function textBlock(text) {
    var p = MC.clamp(MC.rich(el("p", { "class": "full" }), text)), b = el("button", { type: "button", "class": "readall" }, "read all ▸");
    b.addEventListener("click", function () { var open = p.classList.toggle("open"); b.textContent = open ? "fold ◂" : "read all ▸"; });
    return [p, b];
  }

  function connection(rel, other, go) {
    var card = el("article", { "class": "item-card conn" }), head = el("div", { "class": "link-head" });
    head.appendChild(el("span", { "class": "rel" }, rel)); head.appendChild(chipOf(other));
    var w = when(other); if (w) head.appendChild(w);
    if (other.id) { var b = el("button", { type: "button", "class": "connect" }, "connect →"); b.addEventListener("click", function () { go(other.id); }); head.appendChild(b); }
    card.appendChild(head); card.appendChild(MC.clamp(MC.rich(el("p", { "class": "full" }), other.text)));
    return card;
  }

  // Every neighbour with the group it belongs to; readers of a decision count as "went to".
  function links(m, n) {
    var out = [];
    m.out[n.id].forEach(function (e) { out.push([e.kind === "TOUCHED" ? "touched" : "went", "→ " + label(e.kind), m.nodes[e.target]]); });
    m.inn[n.id].forEach(function (e) { out.push([e.kind === "TOUCHED" ? "touched" : "came", "← " + label(e.kind), m.nodes[e.source]]); });
    Object.keys(m.readers[n.id] || {}).forEach(function (role) {
      var session = Object.keys(m.nodes).map(function (id) { return m.nodes[id]; }).filter(function (x) { return x.kind === "Session" && x.role === role; })[0];
      out.push(["went", "→ read by", session || { kind: "session", role: role, text: role + " read " + n.role + "'s work.", id: null, at: 0 }]);
    });
    return out;
  }

  function learned(m, n) {
    var read = m.readers[n.id];
    if (!read) return null;
    var row = el("div", { "class": "learned" });
    row.appendChild(el("span", {}, "learned by"));
    Object.keys(read).forEach(function (role) { row.appendChild(MC.chip(role, MC.color(role))); row.appendChild(el("span", { "class": "when" }, MC.clock(read[role]))); });
    return row;
  }

  function card(m, n) {
    var c = el("article", { "class": "node-card" }), head = el("div", { "class": "link-head" });
    c.style.setProperty("--c", n.role ? MC.color(n.role) : MC.css("--blue"));
    head.appendChild(chipOf(n)); var w = when(n); if (w) head.appendChild(w);
    c.appendChild(head); textBlock(n.text).forEach(function (x) { c.appendChild(x); });
    var l = learned(m, n); if (l) c.appendChild(l);
    return c;
  }

  // `on.select(id)` walks to a node, `on.back()` returns to the overview.
  function show(box, m, n, on) {
    MC.clear(box); box.hidden = false;
    var back = el("button", { type: "button", "class": "back" }, "← back to overview"); back.addEventListener("click", on.back);
    box.appendChild(back); box.appendChild(card(m, n));
    var all = links(m, n), sec = el("div", { "class": "side-sec" }), h = el("h3", {}, "connections"), left = SHOWN;
    h.appendChild(el("span", { "class": "n" }, String(all.length))); sec.appendChild(h);
    if (!all.length) sec.appendChild(el("p", { "class": "dim" }, "no relationships in this view"));
    GROUPS.forEach(function (g) {
      var mine = all.filter(function (l) { return l[0] === g[1]; }).slice(0, Math.max(0, left));
      if (!mine.length) return;
      left -= mine.length; sec.appendChild(el("p", { "class": "grp-h" }, g[0]));
      mine.forEach(function (l) { sec.appendChild(connection(l[1], l[2], on.select)); });
    });
    if (all.length > SHOWN) sec.appendChild(el("p", { "class": "dim" }, "showing " + SHOWN + " of " + all.length + " · connect to a node to see its own"));
    box.appendChild(sec);
  }

  // The chain behind the focus bar: what led to the node, the node, who read it.
  function chain(m, n) {
    var parts = [], from = m.inn[n.id].filter(function (e) { return e.kind !== "TOUCHED"; })[0];
    if (from) parts.push(MC.chip(m.nodes[from.source].kind.toLowerCase() + " · " + m.nodes[from.source].role, MC.color(m.nodes[from.source].role)));
    parts.push(MC.chip(n.kind.toLowerCase(), n.role ? MC.color(n.role) : null, true));
    Object.keys(m.readers[n.id] || {}).forEach(function (r) { parts.push(MC.chip("read by " + r, MC.css("--amber"))); });
    return parts;
  }

  window.MC.graphDetail = { show: show, chain: chain };
})();
