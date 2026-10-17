// The context-graph view: the shared graph (or its concept map) as a live, force-directed drawing,
// in the style of the FalkorDB browser: circles for nodes, arrows for relationships, each arrow
// named with its relationship type. Hover or click a node to light up its own relationships.
(function () {
  "use strict";
  var MC = window.MC;
  var canvas = document.getElementById("graph"), ctx = canvas.getContext("2d");
  var tip = document.getElementById("tip"), count = document.getElementById("graph-count");
  var legend = document.getElementById("legend");
  var mode = "work", nodes = {}, edges = [], visible = false, alpha = 1, hover = null, selected = null;
  var width = 600, height = 620, view = { s: 1, tx: 0, ty: 0 }, last = { work: null, concepts: null };
  var SIZE = { Session: 22, Request: 11, Decision: 13, Need: 12, Edit: 7, File: 12, Message: 9 };
  var typeSlots = {}, WIDE = 1.8;  // the layout is stretched sideways to use the width of the canvas

  function resize() {
    var box = canvas.parentNode.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    width = Math.max(300, box.width); height = box.height;
    canvas.width = width * dpr; canvas.height = height * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  // Work-graph nodes take their role's colour; concepts take one colour per concept type.
  function fill(n) {
    if (n.role) return MC.color(n.role);
    if (!(n.kind in typeSlots)) typeSlots[n.kind] = Object.keys(typeSlots).length % 5;
    return MC.css("--role-" + typeSlots[n.kind]);
  }

  function sync(next) {
    var fresh = {}, byId = {};
    next.nodes.forEach(function (n) {
      var old = nodes[n.id];
      fresh[n.id] = old ? Object.assign(old, { role: n.role, text: n.text }) :
        { id: n.id, kind: n.kind, text: n.text, role: n.role, born: performance.now(), vx: 0, vy: 0,
          x: width * (0.1 + Math.random() * 0.8), y: height * (0.1 + Math.random() * 0.8) };
      byId[n.id] = fresh[n.id];
    });
    next.edges.forEach(function (e) {
      var a = byId[e.source], b = byId[e.target];
      if (a && b && !nodes[b.id] && nodes[a.id]) { b.x = a.x + (Math.random() - 0.5) * 30; b.y = a.y + (Math.random() - 0.5) * 30; }
    });
    if (Object.keys(fresh).length !== Object.keys(nodes).length) alpha = Math.max(alpha, 0.8);
    nodes = fresh; edges = next.edges.filter(function (e) { return fresh[e.source] && fresh[e.target]; });
    var degree = {};
    edges.forEach(function (e) { degree[e.source] = (degree[e.source] || 0) + 1; degree[e.target] = (degree[e.target] || 0) + 1; });
    Object.keys(nodes).sort(function (a, b) { return (degree[b] || 0) - (degree[a] || 0); }).forEach(function (k, i) { nodes[k].hub = i < 6; });
    count.textContent = Object.keys(nodes).length + " nodes · " + edges.length + " relationships";
    MC.graphDetail.refresh(nodes, edges); drawLegend();
  }

  function step() {
    var list = Object.keys(nodes).map(function (k) { return nodes[k]; }), i, j, a, b, dx, dy, d2, f;
    for (i = 0; i < list.length; i++) {
      a = list[i];
      for (j = i + 1; j < list.length; j++) {
        b = list[j]; dx = a.x - b.x; dy = a.y - b.y; d2 = (dx / WIDE) * (dx / WIDE) + dy * dy + 0.01;
        if (d2 > 250000) continue;
        f = 1500 / (d2 + 300); a.vx += dx * f; a.vy += dy * f; b.vx -= dx * f; b.vy -= dy * f;
      }
      a.vx += (width / 2 - a.x) * 0.0006; a.vy += (height / 2 - a.y) * 0.003;
    }
    edges.forEach(function (e) {
      a = nodes[e.source]; b = nodes[e.target]; dx = b.x - a.x; dy = b.y - a.y;
      f = (Math.hypot(dx / WIDE, dy) - 150) * 0.008; a.vx += dx * f; a.vy += dy * f; b.vx -= dx * f; b.vy -= dy * f;
    });
    list.forEach(function (n) {
      n.vx = Math.max(-6, Math.min(6, n.vx * 0.8)); n.vy = Math.max(-6, Math.min(6, n.vy * 0.8)); n.x += n.vx * alpha; n.y += n.vy * alpha;
      n.x = Math.min(width - 14, Math.max(14, n.x)); n.y = Math.min(height - 14, Math.max(14, n.y));
    });
    alpha = Math.max(0.05, alpha * 0.985);
  }

  function fit() {
    var ids = Object.keys(nodes); if (!ids.length) return;
    var x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
    ids.forEach(function (k) { var n = nodes[k]; x0 = Math.min(x0, n.x); x1 = Math.max(x1, n.x); y0 = Math.min(y0, n.y); y1 = Math.max(y1, n.y); });
    var s = Math.max(0.5, Math.min(2.2, Math.min((width - 160) / Math.max(1, x1 - x0), (height - 140) / Math.max(1, y1 - y0))));
    view.s += (s - view.s) * 0.08; view.tx += (width / 2 - s * (x0 + x1) / 2 - view.tx) * 0.08; view.ty += (height / 2 - s * (y0 + y1) / 2 - view.ty) * 0.08;
  }

  function shape(n, r) {
    ctx.beginPath();
    if (n.kind === "Decision") { ctx.moveTo(n.x, n.y - r); ctx.lineTo(n.x + r, n.y); ctx.lineTo(n.x, n.y + r); ctx.lineTo(n.x - r, n.y); ctx.closePath(); }
    else if (n.kind === "File" || n.kind === "Need") ctx.rect(n.x - r, n.y - r, r * 2, r * 2);
    else ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
  }

  function arrow(a, b, rb, pal, lit) {
    var dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 1, ux = dx / d, uy = dy / d;
    var tx = b.x - ux * (rb + 2), ty = b.y - uy * (rb + 2), s = 7 / view.s;
    ctx.strokeStyle = ctx.fillStyle = lit ? pal.ink : pal.line; ctx.lineWidth = (lit ? 1.8 : 1.1) / view.s;
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(tx, ty); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(tx - ux * s - uy * s * 0.5, ty - uy * s + ux * s * 0.5);
    ctx.lineTo(tx - ux * s + uy * s * 0.5, ty - uy * s - ux * s * 0.5); ctx.closePath(); ctx.fill();
  }

  function text(lines, x, y, size, pal, colour) {
    ctx.font = (size / view.s) + "px ui-monospace, Menlo, monospace"; ctx.textAlign = "center"; ctx.lineJoin = "round";
    lines.forEach(function (l, i) {
      ctx.strokeStyle = pal.bg; ctx.lineWidth = 4 / view.s; ctx.strokeText(l, x, y + i * 12 / view.s);
      ctx.fillStyle = colour; ctx.fillText(l, x, y + i * 12 / view.s);
    });
  }

  function draw(now) {
    var pal = { ink: MC.css("--ink"), line: MC.css("--line"), bg: MC.css("--bg"), dim: MC.css("--dim") }, focus = selected || hover;
    ctx.clearRect(0, 0, width, height); fit(); ctx.save(); ctx.translate(view.tx, view.ty); ctx.scale(view.s, view.s);
    var touching = function (e) { return focus && (e.source === focus.id || e.target === focus.id); };
    edges.forEach(function (e) { if (!touching(e)) arrow(nodes[e.source], nodes[e.target], SIZE[nodes[e.target].kind] || 9, pal, false); });
    edges.forEach(function (e) { if (touching(e)) arrow(nodes[e.source], nodes[e.target], SIZE[nodes[e.target].kind] || 9, pal, true); });
    edges.forEach(function (e) {
      var a = nodes[e.source], b = nodes[e.target], lit = touching(e);
      if (focus ? !lit : Math.hypot(a.x - b.x, a.y - b.y) * view.s < 90) return;  // short lines have no room for a name
      text([e.kind.toLowerCase().replace("_", " ")], (a.x + b.x) / 2, (a.y + b.y) / 2 + 3 / view.s, 9, pal, lit ? pal.ink : pal.dim);
    });
    Object.keys(nodes).forEach(function (k) {
      var n = nodes[k], age = now - n.born, r = (SIZE[n.kind] || 9) * Math.min(1, age / 500), c = fill(n);
      if (age < 1800) { ctx.strokeStyle = c; ctx.globalAlpha = 1 - age / 1800; ctx.lineWidth = 2 / view.s; ctx.beginPath(); ctx.arc(n.x, n.y, r + 5 + age / 80, 0, Math.PI * 2); ctx.stroke(); ctx.globalAlpha = 1; }
      shape(n, r); ctx.fillStyle = c; ctx.fill(); ctx.strokeStyle = n === focus ? pal.ink : pal.bg; ctx.lineWidth = (n === focus ? 3 : 1.5) / view.s; ctx.stroke();
      if (n.kind === "Need") { ctx.strokeStyle = MC.css("--red"); ctx.lineWidth = 2.5 / view.s; ctx.stroke(); }
      if (n.kind === "Session" || n.hub || n === focus) text(MC.wrap(n.text, 26, n === focus ? 4 : 2), n.x, n.y + r + 13 / view.s, 11, pal, pal.ink);
    });
    ctx.restore();
  }

  function loop(now) { if (visible && !document.hidden) { step(); draw(now); } requestAnimationFrame(loop); }

  function drawLegend() {
    MC.clear(legend);
    var seen = {};
    Object.keys(nodes).forEach(function (k) { var n = nodes[k]; seen[n.role || n.kind] = fill(n); });
    Object.keys(seen).forEach(function (label) {
      var s = MC.el("span", {}, label === "shared" ? "shared by two roles" : label); s.style.setProperty("--c", seen[label]); legend.appendChild(s);
    });
    if (mode === "work") legend.appendChild(MC.el("span", { "class": "plain" }, "◆ decision · ■ file or need (red outline = need) · ● session, request, message · arrows read source → target"));
  }

  function recentre() {
    Object.keys(nodes).forEach(function (k) { var n = nodes[k]; n.x = width * (0.1 + Math.random() * 0.8); n.y = height * (0.1 + Math.random() * 0.8); n.vx = 0; n.vy = 0; });
  }

  function show() {
    var v = last[mode]; nodes = {}; edges = []; selected = null; MC.graphDetail.clear();
    if (v && v.nodes.length) sync(v); else { count.textContent = mode === "concepts" ? "no concepts yet: run handoff knowledge" : ""; MC.clear(legend); }
    alpha = 1;
  }

  function pick(ev) {
    var box = canvas.getBoundingClientRect(), x = ev.clientX - box.left, y = ev.clientY - box.top, best = null, bd = 20;
    var wx = (x - view.tx) / view.s, wy = (y - view.ty) / view.s;
    Object.keys(nodes).forEach(function (k) { var n = nodes[k], d = Math.hypot(n.x - wx, n.y - wy) * view.s; if (d < bd) { bd = d; best = n; } });
    return { node: best, x: x, y: y };
  }

  canvas.addEventListener("mousemove", function (ev) {
    var p = pick(ev); hover = p.node; tip.hidden = !p.node; canvas.style.cursor = p.node ? "pointer" : "default";
    if (p.node) { tip.textContent = p.node.kind + (p.node.role ? " (" + p.node.role + ")" : "") + ": " + p.node.text; tip.style.left = Math.min(p.x + 14, width - 340) + "px"; tip.style.top = (p.y + 14) + "px"; }
  });
  canvas.addEventListener("click", function (ev) { selected = pick(ev).node; if (selected) MC.graphDetail.show(selected); else MC.graphDetail.clear(); });
  canvas.addEventListener("mouseleave", function () { hover = null; tip.hidden = true; });
  document.querySelectorAll("[data-mode]").forEach(function (b) {
    b.addEventListener("click", function () {
      mode = b.getAttribute("data-mode");
      document.querySelectorAll("[data-mode]").forEach(function (o) { o.setAttribute("aria-pressed", String(o === b)); });
      show();
    });
  });
  window.addEventListener("resize", resize);

  function update(state) {
    var sig = JSON.stringify([state.work, state.concepts]);
    if (sig === last.sig) return;
    last = { work: state.work, concepts: state.concepts, sig: sig };
    var v = last[mode];
    if (v && (v.nodes.length || mode === "work")) sync(v); else show();
  }

  MC.views.graph = { update: update, setVisible: function (v) { visible = v; if (v) { resize(); recentre(); alpha = 0.9; } } };
  resize(); requestAnimationFrame(loop);
})();
