// The orchestration view: each session as a small terminal window, what moves between them as lines
// (solid = message, dashed = read, dotted = need) and a square that travels along them on each event.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var CX = 400, CY = 210, CARD_W = 280, CARD_H = 112;
  var svg = document.getElementById("orch"), flowsBox = document.getElementById("flows");
  var layers = { edges: el("g"), live: el("g"), nodes: el("g") };
  svg.appendChild(layers.edges); svg.appendChild(layers.live); svg.appendChild(layers.nodes);
  var KIND_VAR = { MESSAGE: "--teal", NUDGE: "--teal", DIGEST: "--teal", QUESTION: "--purple", STANDIN_ANSWER: "--purple", NEEDS: "--red", READ: "--amber", DECIDED: "--green", edited: "--blue", asked: "--ink" };
  var positions = Object.create(null), lanes = Object.create(null), signature = "", rings = {};

  function place(roles) {
    positions = Object.create(null);
    var order = roles.map(function (r) { return r.role; }).sort();
    order.forEach(function (role, i) {
      if (order.length === 1) { positions[role] = { x: CX, y: CY }; return; }
      var angle = (-90 + (360 / order.length) * i) * Math.PI / 180;
      positions[role] = { x: CX + 215 * Math.cos(angle), y: CY + 150 * Math.sin(angle) };
    });
  }

  // Where the line from one card's centre toward another's leaves the card, so arrowheads show.
  function edge(c, to) {
    var dx = to.x - c.x, dy = to.y - c.y;
    var t = Math.min((CARD_W / 2 + 3) / (Math.abs(dx) || 1e-6), (CARD_H / 2 + 3) / (Math.abs(dy) || 1e-6));
    return { x: c.x + dx * t, y: c.y + dy * t };
  }

  // The curve between two cards; `lane` separates lines going opposite ways.
  function geom(a, b, lane) {
    var s = edge(a, b), e = edge(b, a), dx = e.x - s.x, dy = e.y - s.y, len = Math.hypot(dx, dy) || 1, off = 14 + lane * 18;
    return { s: s, e: e, cx: (s.x + e.x) / 2 - dy / len * off, cy: (s.y + e.y) / 2 + dx / len * off, nx: -dy / len, ny: dx / len };
  }
  function curve(a, b, lane) { var g = geom(a, b, lane); return "M" + g.s.x + "," + g.s.y + " Q" + g.cx + "," + g.cy + " " + g.e.x + "," + g.e.y; }

  // One arrow per direction between two sessions; a label says what travels along it.
  function drawEdges(flows) {
    MC.clear(layers.edges); MC.clear(flowsBox);
    var by = Object.create(null); lanes = Object.create(null);
    flows.forEach(function (f) {
      if (!positions[f.source] || !positions[f.target] || f.source === f.target) return;
      var key = f.source + ">" + f.target, p = by[key] || (by[key] = { source: f.source, target: f.target, kinds: [], total: 0 });
      p.kinds.push(f); p.total += f.count; lanes[key + ":" + f.kind] = 0;  // events ride the one drawn line
      var row = el("div", {}, f.source + " → " + f.target + "  "); row.appendChild(el("b", { "class": f.kind }, f.kind + " ×" + f.count)); flowsBox.appendChild(row);
    });
    Object.keys(by).forEach(function (key) {
      var p = by[key], a = positions[p.source], b = positions[p.target], g = geom(a, b, 0), w = 1 + Math.min(3, Math.log2(p.total + 1) * 0.6);
      layers.edges.appendChild(el("path", { d: curve(a, b, 0), "class": "edge flow", "marker-end": "url(#oa-flow)", "stroke-width": String(w) }));
      var mx = (g.s.x + 2 * g.cx + g.e.x) / 4 + g.nx * 12, my = (g.s.y + 2 * g.cy + g.e.y) / 4 + g.ny * 12 + 3;
      var label = el("text", { x: mx, y: my, "class": "orch-label" });
      p.kinds.forEach(function (f, i) {
        if (i) label.appendChild(el("tspan", { "class": "dim-sep" }, " · "));
        label.appendChild(el("tspan", { "class": "k-" + f.kind.toLowerCase() }, f.kind.toLowerCase().replace("_", " ") + " ×" + f.count));
      });
      layers.edges.appendChild(label);
    });
  }

  function lastEvent(role, events) {
    for (var i = events.length - 1; i >= 0; i--) if (events[i].role === role) return events[i];
    return null;
  }

  function drawNodes(state) {
    MC.clear(layers.nodes); rings = {};
    if (!state.roles.length) { layers.nodes.appendChild(el("text", { x: CX, y: CY, "class": "empty" }, "waiting for the first session…")); return; }
    state.roles.forEach(function (r) {
      var p = positions[r.role], x = p.x - CARD_W / 2, y = p.y - CARD_H / 2, g = el("g"), colour = MC.color(r.role);
      var active = state.now - r.last_seen_at <= 120000, last = lastEvent(r.role, state.events);
      rings[r.role] = el("rect", { x: x, y: y, width: CARD_W, height: CARD_H, "class": "node-ring", stroke: colour });
      g.appendChild(rings[r.role]);
      g.appendChild(el("rect", { x: x, y: y, width: CARD_W, height: CARD_H, "class": "card-box" }));
      g.appendChild(el("rect", { x: x, y: y, width: CARD_W, height: 20, "class": "card-bar", fill: colour }));
      g.appendChild(el("text", { x: x + 8, y: y + 14, "class": "card-title" }, r.role));
      var tag = (r.open_needs > 0 ? r.open_needs + " open need" + (r.open_needs > 1 ? "s" : "") + " · " : "") + (active ? "active" : "idle");
      g.appendChild(el("text", { x: x + CARD_W - 8, y: y + 14, "class": "card-title", "text-anchor": "end" }, tag));
      g.appendChild(MC.critter.draw(x + 8, y + 36, colour, active));
      var tx = x + 62, lines = last ? MC.wrap(last.text, 33, 3) : [""];
      var head = el("text", { x: tx, y: y + 37, "class": "card-line" });
      head.appendChild(el("tspan", { "class": "card-prompt" }, "$ "));
      head.appendChild(el("tspan", { "class": "k-" + (last ? last.kind.toLowerCase() : "") }, last ? last.kind.toLowerCase() : ""));
      g.appendChild(head);
      lines.forEach(function (l, i) { g.appendChild(el("text", { x: tx, y: y + 51 + i * 13, "class": "card-line" }, l)); });
      if (active) g.appendChild(el("rect", { x: tx + (lines[lines.length - 1].length) * 6.6 + 3, y: y + 42 + (lines.length - 1) * 13, width: 7, height: 11, "class": "cursor" }));
      g.appendChild(el("text", { x: x + 8, y: y + CARD_H - 7, "class": "card-line dim" }, r.requests + " asks · " + r.decisions + " decisions · " + r.edits + " edits"));
      g.setAttribute("class", "orch-node"); g.addEventListener("click", function () { showDetail(r.role); });
      layers.nodes.appendChild(g);
    });
  }

  // The chosen session as a card: its latest work in full, its counts, and its recent events.
  var detailBox = document.getElementById("orch-detail"), current = null, chosen = null;
  function showDetail(role) {
    chosen = role; MC.clear(detailBox);
    var r = current.roles.filter(function (x) { return x.role === role; })[0]; if (!r) return;
    var mine = current.events.filter(function (e) { return e.role === role; }).slice(-5).reverse();
    var card = el("div", { "class": "node-card" }), head = el("div", { "class": "link-head" });
    var chip = el("span", { "class": "chip" }, role); chip.style.setProperty("--c", MC.color(role)); head.appendChild(chip);
    head.appendChild(el("span", { "class": "when" }, (current.now - r.last_seen_at <= 120000 ? "active" : "idle") + " · " + r.requests + " asks · " + r.decisions + " decisions · " + r.edits + " edits" + (r.open_needs ? " · " + r.open_needs + " open need" + (r.open_needs > 1 ? "s" : "") : "")));
    card.appendChild(head);
    card.appendChild(mine.length ? MC.rich(el("p", { "class": "full" }), mine[0].text) : el("p", { "class": "dim" }, "nothing recorded yet"));
    detailBox.appendChild(card);
    mine.slice(1).forEach(function (e) {
      var c = el("div", { "class": "link-card" }), h = el("div", { "class": "link-head" });
      h.appendChild(el("span", { "class": "kind k-" + e.kind.toLowerCase() }, e.kind.toLowerCase())); h.appendChild(el("span", { "class": "when" }, MC.clock(e.at)));
      c.appendChild(h); c.appendChild(MC.clamp(MC.rich(el("p", { "class": "full" }), e.text))); detailBox.appendChild(c);
    });
  }

  function floatLabel(role, text) {
    var p = positions[role]; if (!p) return;
    var t = el("text", { x: p.x, y: p.y - CARD_H / 2 - 8, "class": "float" }, text);
    layers.live.appendChild(t);
    setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 1700);
  }

  function pulse(role) {
    var ring = rings[role]; if (!ring) return;
    ring.classList.remove("pulse"); void ring.getBoundingClientRect(); ring.classList.add("pulse");
  }

  function travel(from, to, lane, colour, then) {
    var a = positions[from], b = positions[to];
    if (!a || !b || MC.reduced) { then(); return; }
    var path = el("path", { d: curve(a, b, lane), fill: "none" });
    var dot = el("rect", { width: "9", height: "9", fill: colour });
    layers.live.appendChild(dot);
    var len = path.getTotalLength(), start = performance.now(), ms = 1100;
    (function frame(now) {
      var t = Math.min(1, (now - start) / ms), pt = path.getPointAtLength(len * t);
      dot.setAttribute("x", pt.x - 4.5); dot.setAttribute("y", pt.y - 4.5);
      if (t < 1) requestAnimationFrame(frame); else { dot.remove(); then(); }
    })(start);
  }

  // One event happening now: a square travels between roles, or the role itself pulses.
  function play(ev) {
    var r = MC.route(ev);
    if (r && positions[r.from] && positions[r.to]) {
      floatLabel(r.from, ev.kind);
      var lane = lanes[r.from + ">" + r.to + ":" + ev.kind.toLowerCase()] || 0;  // ride the drawn line
      travel(r.from, r.to, lane, MC.css(KIND_VAR[ev.kind] || "--dim"), function () { pulse(r.to); floatLabel(r.to, ev.kind); });
    } else {
      pulse(ev.role); floatLabel(ev.role, ev.kind);
    }
  }

  function update(state, fresh) {
    current = state;
    var mine = state.events.map(function (e) { return e.key; }).slice(-60);
    var sig = JSON.stringify([state.roles.map(function (r) { return [r.role, r.requests, r.decisions, r.edits, r.open_needs]; }), state.flows, Math.floor(state.now / 30000), mine]);
    if (sig !== signature) { signature = sig; place(state.roles); drawEdges(state.flows); drawNodes(state); if (state.roles.length) showDetail(chosen && state.roles.some(function (r) { return r.role === chosen; }) ? chosen : state.roles[0].role); }
    fresh.forEach(function (ev, i) { setTimeout(function () { play(ev); }, i * 350); });
  }

  MC.views.orchestration = { update: update, play: play };
})();
