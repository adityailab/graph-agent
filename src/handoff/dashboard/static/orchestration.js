// The orchestration view: each session as a small terminal window, what moves between them as lines
// (solid = message, dashed = read, dotted = need) and a square that travels along them on each event.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var CX = 400, CY = 215, CARD_W = 236, CARD_H = 78;
  var svg = document.getElementById("orch"), flowsBox = document.getElementById("flows");
  var layers = { edges: el("g"), live: el("g"), nodes: el("g") };
  svg.appendChild(layers.edges); svg.appendChild(layers.live); svg.appendChild(layers.nodes);
  var positions = Object.create(null), lanes = Object.create(null), signature = "", rings = {};

  function place(roles) {
    positions = Object.create(null);
    var order = roles.map(function (r) { return r.role; }).sort();
    order.forEach(function (role, i) {
      if (order.length === 1) { positions[role] = { x: CX, y: CY }; return; }
      var angle = (-90 + (360 / order.length) * i) * Math.PI / 180;
      positions[role] = { x: CX + 225 * Math.cos(angle), y: CY + 150 * Math.sin(angle) };
    });
  }

  // A curve between two nodes; `lane` separates lines of different kinds and directions.
  function curve(a, b, lane) {
    var dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1, off = 14 + lane * 18;
    return "M" + a.x + "," + a.y + " Q" + ((a.x + b.x) / 2 - dy / len * off) + "," + ((a.y + b.y) / 2 + dx / len * off) + " " + b.x + "," + b.y;
  }

  function drawEdges(flows) {
    MC.clear(layers.edges); MC.clear(flowsBox);
    var count = Object.create(null);
    lanes = Object.create(null);
    flows.forEach(function (f) {
      if (!positions[f.source] || !positions[f.target] || f.source === f.target) return;
      var key = f.source + ">" + f.target, lane = count[key] = (count[key] || 0) + 1;
      lanes[key + ":" + f.kind] = lane - 1;
      layers.edges.appendChild(el("path", { d: curve(positions[f.source], positions[f.target], lane - 1),
        "class": "edge " + f.kind, "stroke-width": String(1 + Math.min(3, Math.log2(f.count + 1)) * 0.6) }));
      var row = el("div", {}, f.source + " → " + f.target + "  ");
      row.appendChild(el("b", {}, f.kind + " ×" + f.count)); flowsBox.appendChild(row);
    });
  }

  function lastLine(role, events) {
    for (var i = events.length - 1; i >= 0; i--) if (events[i].role === role) return "$ " + events[i].kind.toLowerCase() + " " + events[i].text;
    return "$";
  }

  function drawNodes(state) {
    MC.clear(layers.nodes); rings = {};
    if (!state.roles.length) { layers.nodes.appendChild(el("text", { x: CX, y: CY, "class": "empty" }, "waiting for the first session…")); return; }
    state.roles.forEach(function (r) {
      var p = positions[r.role], x = p.x - CARD_W / 2, y = p.y - CARD_H / 2, g = el("g");
      var active = state.now - r.last_seen_at <= 120000, line = lastLine(r.role, state.events);
      rings[r.role] = el("rect", { x: x, y: y, width: CARD_W, height: CARD_H, "class": "node-ring" });
      g.appendChild(rings[r.role]);
      g.appendChild(el("rect", { x: x, y: y, width: CARD_W, height: CARD_H, "class": "card-box" }));
      g.appendChild(el("rect", { x: x, y: y, width: CARD_W, height: 20, "class": "card-bar" }));
      g.appendChild(el("text", { x: x + 8, y: y + 14, "class": "card-title" }, r.role));
      var tag = (r.open_needs > 0 ? r.open_needs + " open need" + (r.open_needs > 1 ? "s" : "") + " · " : "") + (active ? "active" : "idle");
      g.appendChild(el("text", { x: x + CARD_W - 8, y: y + 14, "class": "card-title", "text-anchor": "end" }, tag));
      g.appendChild(el("text", { x: x + 8, y: y + 39, "class": "card-line" }, line.length > 33 ? line.slice(0, 32) + "…" : line));
      if (active) g.appendChild(el("rect", { x: x + 8 + Math.min(line.length, 33) * 6.6 + 3, y: y + 30, width: 7, height: 11, "class": "cursor" }));
      g.appendChild(el("text", { x: x + 8, y: y + 62, "class": "card-line dim" }, r.requests + " asks · " + r.decisions + " decisions · " + r.edits + " edits"));
      layers.nodes.appendChild(g);
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

  function travel(from, to, lane, then) {
    var a = positions[from], b = positions[to];
    if (!a || !b || MC.reduced) { then(); return; }
    var path = el("path", { d: curve(a, b, lane), fill: "none" });
    var dot = el("rect", { width: "9", height: "9", fill: MC.css("--ink") });
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
      travel(r.from, r.to, lane, function () { pulse(r.to); floatLabel(r.to, ev.kind); });
    } else {
      pulse(ev.role); floatLabel(ev.role, ev.kind);
    }
  }

  function update(state, fresh) {
    var mine = state.events.map(function (e) { return e.key; }).slice(-60);
    var sig = JSON.stringify([state.roles.map(function (r) { return [r.role, r.requests, r.decisions, r.edits, r.open_needs]; }), state.flows, Math.floor(state.now / 30000), mine]);
    if (sig !== signature) { signature = sig; place(state.roles); drawEdges(state.flows); drawNodes(state); }
    fresh.forEach(function (ev, i) { setTimeout(function () { play(ev); }, i * 350); });
  }

  MC.views.orchestration = { update: update, play: play };
})();
