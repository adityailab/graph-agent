// The handoff page as a workflow: each session is a node, each read of another session's work is an
// arrow from its author to its reader, labelled with how many decisions travelled. Click an arrow
// or a node and the hand-offs behind it open as cards on the right.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el, W = 760, H = 400, NODE_W = 196, NODE_H = 64;
  var svg = document.getElementById("hf-graph"), detail = document.getElementById("hf-detail"), stats = document.getElementById("hf-stats");
  var layers = { edges: el("g"), nodes: el("g") }, selected = null, signature = "", last = null;
  svg.appendChild(layers.edges); svg.appendChild(layers.nodes);

  function place(roles) {
    var pos = Object.create(null), names = roles.map(function (r) { return r.role; }).sort();
    names.forEach(function (role, i) {
      if (names.length === 1) { pos[role] = { x: W / 2, y: H / 2 }; return; }
      var angle = (-90 + 360 / names.length * i) * Math.PI / 180;
      pos[role] = { x: W / 2 + 280 * Math.cos(angle), y: H / 2 + 135 * Math.sin(angle) };
    });
    return pos;
  }

  // Where the straight line from one node's centre toward another's leaves the node's box.
  function exit(c, to) {
    var dx = to.x - c.x, dy = to.y - c.y, t = Math.min((NODE_W / 2 + 4) / (Math.abs(dx) || 1e-6), (NODE_H / 2 + 4) / (Math.abs(dy) || 1e-6));
    return { x: c.x + dx * t, y: c.y + dy * t };
  }

  function pairs(handoffs) {
    var by = Object.create(null);
    handoffs.forEach(function (h) {
      var k = h.author + ">" + h.reader, p = by[k] || (by[k] = { author: h.author, reader: h.reader, list: [], decisions: 0 });
      p.list.push(h); p.decisions += h.decisions.length;
    });
    return Object.keys(by).map(function (k) { return by[k]; });
  }

  function select(sel, state) {
    selected = sel;
    var mine = state.handoffs.filter(function (h) {
      return sel.pair ? (h.author === sel.pair.author && h.reader === sel.pair.reader) : (h.author === sel.role || h.reader === sel.role);
    });
    MC.handoffCards.render(detail, sel.pair ? sel.pair.reader + " read " + sel.pair.author + "'s work" : "everything " + sel.role + " gave or took", mine);
    draw(state);
  }

  function drawEdges(state, pos) {
    MC.clear(layers.edges);
    pairs(state.handoffs).forEach(function (p, i) {
      var a = pos[p.author], b = pos[p.reader]; if (!a || !b || a === b) return;
      var s = exit(a, b), t = exit(b, a), dx = t.x - s.x, dy = t.y - s.y, len = Math.hypot(dx, dy) || 1, off = 26;
      var mx = (s.x + t.x) / 2 - dy / len * off, my = (s.y + t.y) / 2 + dx / len * off;
      var on = selected && selected.pair && selected.pair.author === p.author && selected.pair.reader === p.reader;
      var d = "M" + s.x + "," + s.y + " Q" + mx + "," + my + " " + t.x + "," + t.y;
      var g = el("g", { "class": "hf-edge" + (on ? " on" : "") });
      g.appendChild(el("path", { d: d, "class": "hf-line", "marker-end": "url(#hf-arrow)" }));
      g.appendChild(el("path", { d: d, "class": "hf-hit" }));
      // the curve's own midpoint, nudged outward, so the two directions' labels never meet
      var label = el("text", { x: (s.x + 2 * mx + t.x) / 4 - dy / len * 10, y: (s.y + 2 * my + t.y) / 4 + dx / len * 10 + 3, "class": "hf-label", "text-anchor": "middle" },
        p.decisions + (p.decisions === 1 ? " decision" : " decisions") + " · " + p.list.length + (p.list.length === 1 ? " read" : " reads"));
      g.appendChild(label);
      g.addEventListener("click", function () { select({ pair: p }, state); });
      layers.edges.appendChild(g);
    });
  }

  function drawNodes(state, pos) {
    MC.clear(layers.nodes);
    state.roles.forEach(function (r) {
      var p = pos[r.role], x = p.x - NODE_W / 2, y = p.y - NODE_H / 2, colour = MC.color(r.role), g = el("g", { "class": "hf-node" + (selected && selected.role === r.role ? " on" : "") });
      var learned = state.handoffs.reduce(function (n, h) { return n + (h.reader === r.role ? h.decisions.length : 0); }, 0);
      g.appendChild(el("rect", { x: x, y: y, width: NODE_W, height: NODE_H, rx: 4, "class": "card-box" }));
      g.appendChild(el("rect", { x: x, y: y, width: 5, height: NODE_H, fill: colour }));
      g.appendChild(MC.critter.draw(x + 12, y + 16, colour, state.now - r.last_seen_at <= 120000));
      g.appendChild(el("text", { x: x + 62, y: y + 26, "class": "card-title hf-name" }, r.role));
      g.appendChild(el("text", { x: x + 62, y: y + 43, "class": "card-line dim" }, (r.requests + r.decisions + r.edits) + " own · " + learned + " learned"));
      g.addEventListener("click", function () { select({ role: r.role }, state); });
      layers.nodes.appendChild(g);
    });
  }

  function draw(state) {
    var pos = place(state.roles);
    drawEdges(state, pos); drawNodes(state, pos);
  }

  function counters(state) {
    MC.clear(stats);
    var carried = state.handoffs.reduce(function (n, h) { return n + h.decisions.length; }, 0);
    [[state.handoffs.length, "reads of another session's work"], [carried, "decisions that travelled"]].forEach(function (s) {
      var box = el("div", { "class": "stat" }), n = el("b", {}, "0"); box.appendChild(n); box.appendChild(el("span", {}, s[1]));
      MC.countTo(n, s[0], "handoff:" + s[1]); stats.appendChild(box);
    });
  }

  function update(state) {
    var sig = JSON.stringify([state.handoffs, state.roles.map(function (r) { return [r.role, r.requests, r.decisions, r.edits]; })]);
    if (sig === signature) return;
    signature = sig; last = state; counters(state);
    if (!state.roles.length) { MC.clear(layers.edges); MC.clear(layers.nodes); return; }
    var first = state.handoffs[0];
    var keep = selected && (selected.role || (selected.pair && state.handoffs.some(function (h) { return h.author === selected.pair.author && h.reader === selected.pair.reader; })));
    var next = keep ? selected : (first ? { pair: { author: first.author, reader: first.reader } } : { role: state.roles[0].role });
    select(next, state);
  }

  MC.views.handoff = { update: update };
})();
