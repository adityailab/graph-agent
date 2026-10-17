// The orchestration view: sessions as nodes, what moves between them as animated lines and dots.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var W = 800, H = 460, CX = 400, CY = 225, R = 165, NODE_R = 46;
  var KIND_COLOUR = { message: "#2dd4bf", read: "#fbbf24", need: "#f87171", nudge: "#94a3b8", digest: "#94a3b8" };
  var EVENT_COLOUR = { asked: "#e6edf3", DECIDED: "#4ade80", edited: "#38bdf8", NEEDS: "#f87171", MESSAGE: "#2dd4bf", READ: "#fbbf24" };
  var svg = document.getElementById("orch");
  var layers = { edges: el("g"), nodes: el("g"), live: el("g") };
  svg.appendChild(layers.edges); svg.appendChild(layers.nodes); svg.appendChild(layers.live);
  var positions = {}, signature = "", rings = {};

  function place(roles) {
    positions = {};
    var order = roles.map(function (r) { return r.role; }).sort();
    order.forEach(function (role, i) {
      if (order.length === 1) { positions[role] = { x: CX, y: CY }; return; }
      var angle = (-90 + (360 / order.length) * i) * Math.PI / 180;
      positions[role] = { x: CX + R * 1.35 * Math.cos(angle), y: CY + R * Math.sin(angle) };
    });
  }

  // A curve between two nodes; `lane` separates lines of different kinds and directions.
  function curve(a, b, lane) {
    var mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    var dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1;
    var off = 24 + lane * 30, cx = mx - dy / len * off, cy = my + dx / len * off;
    var t = [0.5, 0.3, 0.7, 0.2, 0.8][lane % 5], u = 1 - t;  // labels sit at different points of the curve
    return { d: "M" + a.x + "," + a.y + " Q" + cx + "," + cy + " " + b.x + "," + b.y,
             lx: u * u * a.x + 2 * u * t * cx + t * t * b.x, ly: u * u * a.y + 2 * u * t * cy + t * t * b.y };
  }

  function drawEdges(flows) {
    MC.clear(layers.edges);
    var lanes = {};
    flows.forEach(function (f) {
      if (!positions[f.source] || !positions[f.target] || f.source === f.target) return;
      var key = f.source + ">" + f.target, lane = lanes[key] = (lanes[key] || 0) + 1;
      var c = curve(positions[f.source], positions[f.target], lane - 1);
      var colour = KIND_COLOUR[f.kind] || "#94a3b8";
      layers.edges.appendChild(el("path", { d: c.d, "class": "edge", stroke: colour,
        "stroke-width": String(1.5 + Math.log2(f.count + 1) * 1.4) }));
      layers.edges.appendChild(el("text", { x: c.lx, y: c.ly, "class": "edge-label" }, f.kind + " ×" + f.count));
    });
  }

  function drawNodes(roles, now) {
    MC.clear(layers.nodes); rings = {};
    if (!roles.length) {
      layers.nodes.appendChild(el("text", { x: CX, y: CY, "class": "empty" }, "Waiting for the first session…"));
      return;
    }
    roles.forEach(function (r) {
      var p = positions[r.role], colour = MC.color(r.role), g = el("g");
      rings[r.role] = el("circle", { cx: p.x, cy: p.y, r: NODE_R, "class": "node-ring", stroke: colour });
      g.appendChild(rings[r.role]);
      g.appendChild(el("circle", { cx: p.x, cy: p.y, r: NODE_R, fill: "#0b141b", stroke: colour, "stroke-width": "3" }));
      g.appendChild(el("text", { x: p.x, y: p.y - 2, "class": "node-name" }, r.role));
      var idle = now - r.last_seen_at > 120000;
      g.appendChild(el("text", { x: p.x, y: p.y + 14, "class": "node-sub" }, idle ? "idle" : "active"));
      var above = p.y < CY - 20;  // counters go on the side away from the other sessions' lines
      g.appendChild(el("text", { x: p.x, y: above ? p.y - NODE_R - 12 : p.y + NODE_R + 18, "class": "node-sub" },
        r.requests + " asks · " + r.decisions + " decisions · " + r.edits + " edits"));
      if (r.open_needs > 0) {
        g.appendChild(el("circle", { cx: p.x + 34, cy: p.y - 34, r: "11", fill: "#f87171" }));
        g.appendChild(el("text", { x: p.x + 34, y: p.y - 30, "class": "badge" }, String(r.open_needs)));
      }
      layers.nodes.appendChild(g);
    });
  }

  function floatLabel(role, text, colour) {
    var p = positions[role]; if (!p) return;
    var t = el("text", { x: p.x, y: p.y - NODE_R - 8, "class": "float", fill: colour }, text);
    layers.live.appendChild(t);
    setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 1700);
  }

  function pulse(role) {
    var ring = rings[role]; if (!ring) return;
    ring.classList.remove("pulse"); void ring.getBoundingClientRect(); ring.classList.add("pulse");
  }

  function travel(from, to, colour, then) {
    var a = positions[from], b = positions[to];
    if (!a || !b || MC.reduced) { then(); return; }
    var path = el("path", { d: curve(a, b, 0).d, fill: "none" });
    var dot = el("circle", { r: "6", fill: colour });
    layers.live.appendChild(dot);
    var len = path.getTotalLength(), start = performance.now(), ms = 1100;
    (function frame(now) {
      var t = Math.min(1, (now - start) / ms), pt = path.getPointAtLength(len * t);
      dot.setAttribute("cx", pt.x); dot.setAttribute("cy", pt.y);
      if (t < 1) requestAnimationFrame(frame); else { dot.remove(); then(); }
    })(start);
  }

  // One event happening now: a dot travels between roles, or the role itself pulses.
  function play(ev) {
    var colour = EVENT_COLOUR[ev.kind] || "#94a3b8", r = MC.route(ev);
    if (r && positions[r.from] && positions[r.to]) {
      floatLabel(r.from, ev.kind, colour);
      travel(r.from, r.to, colour, function () { pulse(r.to); floatLabel(r.to, ev.kind, colour); });
    } else {
      pulse(ev.role); floatLabel(ev.role, ev.kind, colour);
    }
  }

  function update(state, fresh) {
    var sig = JSON.stringify([state.roles, state.flows, Math.floor(state.now / 30000)]);
    if (sig !== signature) {
      signature = sig; place(state.roles); drawEdges(state.flows); drawNodes(state.roles, state.now);
    }
    fresh.forEach(function (ev, i) { setTimeout(function () { play(ev); }, i * 350); });
  }

  MC.views.orchestration = { update: update, play: play };
})();
