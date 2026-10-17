// The context-graph view, drawn with the force-graph library (the one the FalkorDB browser uses):
// drag nodes (they stay where you put them), scroll to zoom, drag the background to pan. Circles
// are nodes, arrows are relationships, each named with its type. Hover or click a node to light
// up its own relationships; labels never come from the library, so graph text is never markup.
(function () {
  "use strict";
  var MC = window.MC;
  var holder = document.getElementById("graph"), tip = document.getElementById("tip");
  var count = document.getElementById("graph-count"), legend = document.getElementById("legend");
  var SIZE = { Session: 6.5, Request: 3.6, Decision: 4, Need: 4, Edit: 2.6, File: 4, Message: 3 };
  var EDGE = ["#e11d48", "#0ea5e9", "#22c55e", "#a855f7", "#f59e0b", "#14b8a6", "#ec4899", "#84cc16", "#6366f1", "#f97316"], edgeSlots = {};
  var mode = "work", visible = false, last = { work: null, concepts: null, sig: "" };
  var nodes = {}, plain = [], hover = null, hoverLink = null, selected = null, pal = {}, typeSlots = {}, degree = {};
  var fg = ForceGraph()(holder).backgroundColor("rgba(0,0,0,0)").nodeId("id").cooldownTicks(220).onEngineStop(function () { if (visible && !selected) fg.zoomToFit(300, 60); })
    .linkDirectionalArrowLength(5).linkDirectionalArrowRelPos(1).linkWidth(function (l) { return lit(l) ? 2.2 : 1; })
    .linkColor(function (l) { return hexAlpha(edgeColour(l.kind), focus() && !lit(l) ? 0.12 : 0.85); })
    .linkCurvature("curve").nodeRelSize(1).nodeLabel(function () { return ""; });
  fg.d3Force("charge").strength(-45).distanceMax(260);
  fg.d3Force("link").distance(26);

  function focus() { return selected || hover; }
  function lit(l) {
    var f = focus(), s = l.source.id || l.source, t = l.target.id || l.target;
    return l === hoverLink || (!!f && (s === f.id || t === f.id));
  }
  function edgeColour(kind) {
    if (!(kind in edgeSlots)) edgeSlots[kind] = Object.keys(edgeSlots).length % EDGE.length;
    return EDGE[edgeSlots[kind]];
  }
  function hexAlpha(hex, a) {
    var n = parseInt(hex.slice(1), 16);
    return "rgba(" + (n >> 16) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + a + ")";
  }

  function fill(n) {
    if (n.role) return MC.color(n.role);
    if (!(n.kind in typeSlots)) typeSlots[n.kind] = Object.keys(typeSlots).length % 5;
    return MC.css("--role-" + typeSlots[n.kind]);
  }

  function shape(ctx, n, r) {
    ctx.beginPath();
    if (n.kind === "Decision") { ctx.moveTo(n.x, n.y - r * 1.3); ctx.lineTo(n.x + r * 1.3, n.y); ctx.lineTo(n.x, n.y + r * 1.3); ctx.lineTo(n.x - r * 1.3, n.y); ctx.closePath(); }
    else if (n.kind === "File" || n.kind === "Need") ctx.rect(n.x - r, n.y - r, r * 2, r * 2);
    else ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
  }

  function caption(ctx, lines, x, y, scale, colour) {
    ctx.font = (11 / scale) + "px ui-monospace, Menlo, monospace"; ctx.textAlign = "center"; ctx.lineJoin = "round";
    lines.forEach(function (l, i) {
      ctx.strokeStyle = pal.bg; ctx.lineWidth = 4 / scale; ctx.strokeText(l, x, y + i * 13 / scale);
      ctx.fillStyle = colour; ctx.fillText(l, x, y + i * 13 / scale);
    });
  }

  fg.onRenderFramePre(function () { pal = { ink: MC.css("--ink"), line: MC.css("--line"), bg: MC.css("--bg"), dim: MC.css("--dim"), red: MC.css("--red") }; });
  fg.nodeCanvasObject(function (n, ctx, scale) {
    var r = SIZE[n.kind] || 5, f = focus(), near = f && (f === n || neighbours(f, n));
    ctx.globalAlpha = (f || hoverLink) && !near && !(hoverLink && touchesLink(n)) ? 0.15 : 1;
    shape(ctx, n, r); ctx.fillStyle = fill(n); ctx.fill();
    ctx.strokeStyle = n === f ? pal.ink : n.kind === "Need" ? pal.red : pal.bg; ctx.lineWidth = (n === f ? 2.5 : 1.5) / scale; ctx.stroke();
    if (n.kind === "Session" || n === f || near || scale > 3.4)
      caption(ctx, MC.wrap(n.text, 28, n === f ? 5 : 2), n.x, n.y + r + 11 / scale, scale, pal.ink);
    ctx.globalAlpha = 1;
  }).nodePointerAreaPaint(function (n, colour, ctx) { shape(ctx, n, (SIZE[n.kind] || 5) + 3); ctx.fillStyle = colour; ctx.fill(); });

  fg.linkCanvasObjectMode(function () { return "after"; }).linkCanvasObject(function (l, ctx, scale) {
    if (!(focus() ? lit(l) : scale > 1.6) || !l.source.x) return;
    var mx = (l.source.x + l.target.x) / 2, my = (l.source.y + l.target.y) / 2;
    caption(ctx, [l.kind.toLowerCase().replace("_", " ")], mx, my, scale, edgeColour(l.kind));
  });

  var links = [];
  function touchesLink(n) { return !!hoverLink && [hoverLink.source.id, hoverLink.target.id].indexOf(n.id) >= 0; }
  function neighbours(a, b) { return links.some(function (l) { var s = l.source.id || l.source, t = l.target.id || l.target; return (s === a.id && t === b.id) || (t === a.id && s === b.id); }); }

  function sync(next) {
    var fresh = {};
    next.nodes.forEach(function (n) {
      var old = nodes[n.id];
      fresh[n.id] = old ? Object.assign(old, { role: n.role, text: n.text }) : { id: n.id, kind: n.kind, text: n.text, role: n.role };
    });
    var pair = {}, seen = {};
    plain = next.edges.filter(function (e) { return fresh[e.source] && fresh[e.target]; });
    degree = {};
    links = plain.map(function (e) {
      var key = [e.source, e.target].sort().join("|"), i = seen[key] = (seen[key] || 0) + 1;
      degree[e.source] = (degree[e.source] || 0) + 1; degree[e.target] = (degree[e.target] || 0) + 1;
      return { source: e.source, target: e.target, kind: e.kind, curve: i === 1 ? 0 : 0.22 * (i % 2 ? i : -i) / 1.5 };
    });
    nodes = fresh;
    fg.graphData({ nodes: Object.keys(fresh).map(function (k) { return fresh[k]; }), links: links });
    count.textContent = Object.keys(nodes).length + " nodes · " + plain.length + " relationships";
    MC.graphDetail.refresh(nodes, plain); drawLegend();
  }

  function drawLegend() {
    MC.clear(legend); var seen = {};
    Object.keys(nodes).forEach(function (k) { var n = nodes[k]; seen[n.role || n.kind] = fill(n); });
    Object.keys(seen).forEach(function (label) {
      var s = MC.el("span", {}, label === "shared" ? "shared by two roles" : label); s.style.setProperty("--c", seen[label]); legend.appendChild(s);
    });
    var kinds = {}; plain.forEach(function (e) { kinds[e.kind] = true; });
    Object.keys(kinds).forEach(function (k) { var t = MC.el("span", { "class": "line" }, k.toLowerCase().replace("_", " ")); t.style.setProperty("--c", edgeColour(k)); legend.appendChild(t); });
    if (mode === "work") legend.appendChild(MC.el("span", { "class": "plain" }, "◆ decision · ■ file or need (red outline = need) · ● session, request, message · arrows read source → target"));
  }

  function resize() { var box = holder.parentNode.getBoundingClientRect(); fg.width(Math.max(300, box.width)).height(box.height); }

  function show() {
    var v = last[mode]; nodes = {}; plain = []; links = []; selected = null; MC.graphDetail.clear();
    fg.graphData({ nodes: [], links: [] });
    if (v && v.nodes.length) sync(v); else { count.textContent = mode === "concepts" ? "no concepts yet: run handoff knowledge" : ""; MC.clear(legend); }
  }

  fg.onLinkHover(function (l) { hoverLink = l || null; holder.style.cursor = l ? "pointer" : "default"; });
  fg.onNodeHover(function (n) {
    hover = n || null; holder.style.cursor = n ? "pointer" : "default"; tip.hidden = !n;
    if (n) tip.textContent = n.kind + (n.role ? " (" + n.role + ")" : "") + ": " + n.text;
  });
  holder.addEventListener("mousemove", function (ev) { var b = holder.getBoundingClientRect(); tip.style.left = Math.min(ev.clientX - b.left + 14, b.width - 340) + "px"; tip.style.top = (ev.clientY - b.top + 14) + "px"; });
  fg.onNodeClick(function (n) { selected = n; MC.graphDetail.show(n); });
  // Anything that is not a node puts the graph back to normal: no selection, nothing faded.
  function clearFocus() { selected = null; hover = null; hoverLink = null; tip.hidden = true; MC.graphDetail.clear(); }
  fg.onBackgroundClick(clearFocus).onLinkClick(clearFocus);
  holder.addEventListener("mouseleave", function () { hover = null; hoverLink = null; tip.hidden = true; });
  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") clearFocus(); });
  fg.onNodeDragEnd(function (n) { n.fx = n.x; n.fy = n.y; });  // a dragged node stays where it is put
  document.getElementById("graph-fit").addEventListener("click", function () { fg.zoomToFit(400, 40); });
  document.getElementById("graph-unpin").addEventListener("click", function () { Object.keys(nodes).forEach(function (k) { nodes[k].fx = nodes[k].fy = undefined; }); fg.d3ReheatSimulation(); });
  document.querySelectorAll("[data-mode]").forEach(function (b) {
    b.addEventListener("click", function () {
      mode = b.getAttribute("data-mode");
      document.querySelectorAll("[data-mode]").forEach(function (o) { o.setAttribute("aria-pressed", String(o === b)); });
      show(); setTimeout(function () { fg.zoomToFit(400, 40); }, 900);
    });
  });
  window.addEventListener("resize", resize);

  function update(state) {
    var sig = JSON.stringify([state.work, state.concepts]);
    if (sig === last.sig) return;
    last = { work: state.work, concepts: state.concepts, sig: sig };
    var v = last[mode], first = !Object.keys(nodes).length;
    if (v && (v.nodes.length || mode === "work")) sync(v); else show();
    if (first && visible) setTimeout(function () { fg.zoomToFit(400, 40); }, 900);
  }

  MC.views.graph = { update: update, setVisible: function (v) { visible = v; if (v) { resize(); setTimeout(function () { fg.zoomToFit(400, 40); }, 900); } else fg.pauseAnimation(); if (v) fg.resumeAnimation(); } };
  resize();
})();
