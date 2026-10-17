// The handoff page as a workflow: each session is a node, each read of another session's work is an
// arrow from its author to its reader, labelled with how many decisions travelled. Click an arrow
// or a node and the hand-offs behind it open as cards on the right.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el, W = 600, H = 300, NODE_W = 160, NODE_H = 56;
  var svg = document.getElementById("hf-graph"), detail = document.getElementById("hf-detail"), stats = document.getElementById("hf-stats");
  var layers = { edges: el("g"), nodes: el("g"), live: el("g") }, selected = null, signature = "", last = null;
  var where = {}, paths = {}, rings = {};
  svg.appendChild(layers.edges); svg.appendChild(layers.nodes); svg.appendChild(layers.live);

  function place(roles) {
    var pos = Object.create(null), names = roles.map(function (r) { return r.role; }).sort();
    names.forEach(function (role, i) {
      if (names.length === 1) { pos[role] = { x: W / 2, y: 60 }; return; }
      var angle = (-90 + 360 / names.length * i) * Math.PI / 180;
      pos[role] = { x: W / 2 + 215 * Math.cos(angle), y: 150 + 110 * Math.sin(angle) };
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

  function pill(g, p, x, y) {
    var w = 122, hgt = 30, route = p.author + " → " + p.reader;
    g.appendChild(el("rect", { "class": "pill-box", x: x - w / 2, y: y - hgt / 2, width: w, height: hgt, rx: 6 }));
    g.appendChild(el("text", { "class": "hf-route", x: x - w / 2 + 7, y: y - 3 }, route));
    g.appendChild(el("text", { "class": "hf-dec", x: x - w / 2 + 7, y: y + 10 }, "◆ " + p.decisions + (p.decisions === 1 ? " decision" : " decisions")));
    g.appendChild(el("text", { "class": "hf-rd", x: x + w / 2 - 7, y: y + 10, "text-anchor": "end" }, "╌╌ " + p.list.length));
  }

  function drawEdges(state, pos) {
    MC.clear(layers.edges); paths = {};
    var all = pairs(state.handoffs), has = {};
    all.forEach(function (q) { has[q.author + ">" + q.reader] = true; });
    all.forEach(function (p) {
      var a = pos[p.author], b = pos[p.reader]; if (!a || !b || a === b) return;
      var s = exit(a, b), t = exit(b, a), dx = t.x - s.x, dy = t.y - s.y, len = Math.hypot(dx, dy) || 1, off = has[p.reader + ">" + p.author] ? 52 : 24;
      var mx = (s.x + t.x) / 2 - dy / len * off, my = (s.y + t.y) / 2 + dx / len * off;
      var on = selected && selected.pair && selected.pair.author === p.author && selected.pair.reader === p.reader;
      var d = "M" + s.x + "," + s.y + " Q" + mx + "," + my + " " + t.x + "," + t.y;
      var g = el("g", { "class": "hf-edge" + (on ? " on" : ""), role: "button", tabindex: "0", "aria-label": p.author + " to " + p.reader + ": " + p.decisions + " decisions, " + p.list.length + " reads" });
      paths[p.author + ">" + p.reader] = d;
      g.appendChild(el("path", { d: d, "class": "hf-line", "stroke-width": String(Math.min(2.4, 1 + p.decisions * 0.1)), "marker-end": "url(#hfa)" }));
      g.appendChild(el("path", { d: d, "class": "hf-hit" }));
      pill(g, p, (s.x + 2 * mx + t.x) / 4, (s.y + 2 * my + t.y) / 4);
      var open = function () { select({ pair: p }, state); };
      g.addEventListener("click", open);
      g.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); open(); } });
      layers.edges.appendChild(g);
    });
  }

  function drawNodes(state, pos) {
    MC.clear(layers.nodes); rings = {};
    state.roles.forEach(function (r) {
      var p = pos[r.role], x = p.x - NODE_W / 2, y = p.y - NODE_H / 2, colour = MC.color(r.role);
      var g = el("g", { "class": "hf-node" + (selected && selected.role === r.role ? " on" : ""), role: "button", tabindex: "0", "aria-label": r.role + " session, open its hand-offs" });
      var learned = state.handoffs.reduce(function (n, h) { return n + (h.reader === r.role ? h.decisions.length : 0); }, 0), own = r.requests + r.decisions + r.edits;
      rings[r.role] = el("rect", { x: x, y: y, width: NODE_W, height: NODE_H, rx: 6, "class": "node-ring", stroke: colour }); g.appendChild(rings[r.role]);
      g.appendChild(el("rect", { x: x, y: y, width: NODE_W, height: NODE_H, rx: 6, "class": "card-box" }));
      g.appendChild(el("rect", { x: x, y: y, width: 4, height: NODE_H, fill: colour }));
      var mac = el("g", { transform: "translate(" + (x + 6) + "," + (y + 10) + ")" }); mac.appendChild(MC.critter.draw(0, 0, colour, state.now - r.last_seen_at <= 120000)); g.appendChild(mac);
      g.appendChild(el("text", { x: x + 52, y: y + 22, "class": "card-title hf-name" }, r.role));
      g.appendChild(el("text", { x: x + 52, y: y + 36, "class": "card-line dim" }, own + " own · " + learned + " learned"));
      g.appendChild(el("rect", { x: x + 52, y: y + 42, width: 96, height: 4, rx: 2, "class": "hf-bar" }));
      g.appendChild(el("rect", { x: x + 52, y: y + 42, width: 96 * (own + learned ? learned / (own + learned) : 0), height: 4, rx: 2, fill: MC.css("--green") }));
      var open = function () { select({ role: r.role }, state); };
      g.addEventListener("click", open);
      g.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); open(); } });
      layers.nodes.appendChild(g);
    });
  }

  function draw(state) {
    var pos = where = place(state.roles);
    svg.setAttribute("viewBox", "0 0 " + W + " " + (state.roles.length > 2 ? 300 : 140));
    drawEdges(state, pos); drawNodes(state, pos);
  }

  function floatLabel(role, text) {
    var p = where[role]; if (!p) return;
    var t = el("text", { x: p.x, y: p.y - NODE_H / 2 - 6, "class": "float" }, text);
    layers.live.appendChild(t); setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 1700);
  }
  function pulse(role) {
    var ring = rings[role]; if (!ring) return;
    ring.classList.remove("pulse"); void ring.getBoundingClientRect(); ring.classList.add("pulse");
  }

  // A read happening now: a green square rides the arrow from the author to the reader.
  function travel(from, to, then) {
    var d = paths[from + ">" + to];
    if (!d || MC.reduced) { then(); return; }
    var path = el("path", { d: d, fill: "none" }), dot = el("rect", { width: "8", height: "8", fill: MC.css("--green") });
    layers.live.appendChild(dot);
    var len = path.getTotalLength(), start = performance.now();
    (function frame(now) {
      var t = Math.min(1, (now - start) / 1100), pt = path.getPointAtLength(len * t);
      dot.setAttribute("x", pt.x - 4); dot.setAttribute("y", pt.y - 4);
      if (t < 1) requestAnimationFrame(frame); else { dot.remove(); then(); }
    })(start);
  }

  function play(ev) {
    var r = MC.route(ev);
    if (ev.kind === "READ" && r && where[r.from] && where[r.to]) {
      floatLabel(r.from, "read"); travel(r.from, r.to, function () { pulse(r.to); floatLabel(r.to, "learned"); });
    } else if (where[ev.role]) { pulse(ev.role); floatLabel(ev.role, ev.kind.toLowerCase()); }
  }

  function counters(state) {
    MC.clear(stats);
    var carried = state.handoffs.reduce(function (n, h) { return n + h.decisions.length; }, 0);
    [[state.handoffs.length, "reads of another session's work"], [carried, "decisions that travelled"]].forEach(function (s) {
      var box = el("div", { "class": "stat" }), n = el("b", {}, "0"); box.appendChild(n); box.appendChild(el("span", {}, s[1]));
      MC.countTo(n, s[0], "handoff:" + s[1]); stats.appendChild(box);
    });
  }

  function update(state, fresh) {
    (fresh || []).forEach(function (ev, i) { setTimeout(function () { play(ev); }, i * 350); });
    var sig = JSON.stringify([state.handoffs, state.roles.map(function (r) { return [r.role, r.requests, r.decisions, r.edits]; })]);
    if (sig === signature) return;
    signature = sig; last = state; counters(state);
    if (!state.roles.length) { MC.clear(layers.edges); MC.clear(layers.nodes); return; }
    var first = state.handoffs[0];
    var keep = selected && (selected.role || (selected.pair && state.handoffs.some(function (h) { return h.author === selected.pair.author && h.reader === selected.pair.reader; })));
    var next = keep ? selected : (first ? { pair: { author: first.author, reader: first.reader } } : { role: state.roles[0].role });
    select(next, state);
  }

  MC.views.handoff = { update: update, play: play };
})();
