// The context-graph view, drawn with the force-graph library (the one the FalkorDB browser uses):
// drag nodes (they stay where you put them), scroll to zoom, drag the background to pan. Circles
// are nodes, arrows are relationships, each named with its type. Hover or click a node to light
// up its own relationships; labels never come from the library, so graph text is never markup.
(function () {
  "use strict";
  var MC = window.MC;
  var M = MC.graphModel;
  var holder = document.getElementById("graph"), tip = document.getElementById("tip");
  var bar = document.getElementById("graph-bar"), overview = document.getElementById("side-overview"), detail = document.getElementById("detail"), pathBar = document.getElementById("path-bar");
  // Choices made in the toolbar and panel: which kinds of node to draw, and an optional single session.
  var opts = { kinds: { Decision: true, Need: true, Message: true, Request: true, File: true }, only: null, memoryKind: null, model: null, full: null };
  var SIZE = { Session: 6.5, Request: 3.6, Decision: 4, Need: 4, Edit: 2.6, File: 4, Message: 3, Convention: 4.5, Topic: 4 };
  var EDGE = ["#e11d48", "#0ea5e9", "#22c55e", "#a855f7", "#f59e0b", "#14b8a6", "#ec4899", "#84cc16", "#6366f1", "#f97316"], edgeSlots = {};
  var mode = "work", visible = false, last = { work: null, concepts: null, memory: null, sig: "" };
  var nodes = {}, plain = [], hover = null, hoverLink = null, selected = null, pal = {}, typeSlots = {}, degree = {};
  var fg = ForceGraph()(holder).backgroundColor("rgba(0,0,0,0)").nodeId("id").cooldownTicks(220).onEngineStop(function () { if (visible && !selected) fit(300, 60); })
    .linkDirectionalArrowLength(5).linkDirectionalArrowRelPos(1).linkWidth(function (l) { return lit(l) ? 2.2 : 1; })
    .linkColor(function (l) { return hexAlpha(edgeColour(l.kind), focus() && !lit(l) ? 0.12 : 0.85); })
    .linkCurvature("curve").nodeRelSize(1).nodeLabel(function () { return ""; });
  // Zooming is free (a person reads crowded labels by zooming in); only the automatic fit is
  // limited, so a graph of two nodes is not blown up until it fills the canvas.
  fg.minZoom(0.05).maxZoom(40);
  var FIT_MAX = 2.2;
  function fit(ms, pad) {
    fg.zoomToFit(ms, pad);
    setTimeout(function () { if (fg.zoom() > FIT_MAX) fg.zoom(FIT_MAX, 250); }, ms + 60);
  }
  fg.d3Force("charge").strength(-90).distanceMax(400);
  fg.d3Force("link").distance(40);

  // The short name shown on hover: the first words only. The whole text opens in the side panel on click.
  function stamp(n) { return n.at ? MC.clock(n.at) + " " : ""; }
  function name(n) {
    var one = n.text.replace(/\s+/g, " ").trim();
    return one.length > 48 ? one.slice(0, 47).replace(/\s+\S*$/, "") + "…" : one;
  }

  // A graph of a handful of nodes (one kind of memory) has room: space it out and label everything.
  function small() { return Object.keys(nodes).length < 12; }

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
    else if (n.kind === "File" || n.kind === "Need" || n.kind === "Convention") ctx.rect(n.x - r, n.y - r, r * 2, r * 2);
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
    if (n.kind === "Session" || n === f || near || scale > 3.4 || small())
      caption(ctx, MC.wrap((mode === "memory" ? stamp(n) : "") + n.text, 28, n === f ? 5 : 2), n.x, n.y + r + 11 / scale, scale, pal.ink);
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

  function sync(raw) {
    opts.full = raw; opts.model = M.build(raw);
    var next = narrowed(raw), fresh = {};
    next.nodes.forEach(function (n) {
      var old = nodes[n.id];
      fresh[n.id] = old ? Object.assign(old, { role: n.role, text: n.text, at: n.at }) : { id: n.id, kind: n.kind, text: n.text, role: n.role, at: n.at };
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
    fg.d3Force("link").distance(small() ? 130 : 40);
    fg.d3Force("charge").strength(small() ? -240 : -90);
    fg.graphData({ nodes: Object.keys(fresh).map(function (k) { return fresh[k]; }), links: links });
    panel();
  }

  // The toolbar's choices applied to the data: which kinds of node, and one session if chosen.
  function narrowed(raw) {
    var keep = {};
    raw.nodes.forEach(function (n) {
      var t = n.kind === "Edit" ? "File" : n.kind, off = mode === "work" && t in opts.kinds && !opts.kinds[t];
      var other = mode === "work" && opts.only && n.role !== opts.only && n.kind !== "Session";
      if (!off && !other) keep[n.id] = true;
    });
    return { nodes: raw.nodes.filter(function (n) { return keep[n.id]; }), edges: raw.edges.filter(function (e) { return keep[e.source] && keep[e.target]; }) };
  }

  // Toolbar, side panel (overview or the selected node) and the focus bar, all from the same data.
  function panel() {
    var m = opts.model;
    if (!m) return;
    MC.graphBar.render(bar, { mode: mode, kinds: opts.kinds, pinning: pinning, memoryKind: opts.memoryKind }, M.counts(m, null, "session"), on);
    var n = selected && m.nodes[selected.id];
    detail.hidden = !n; overview.hidden = !!n; pathBar.hidden = !n; MC.clear(pathBar);
    if (n) {
      MC.graphDetail.show(detail, m, n, { select: select, back: clearFocus });
      pathBar.appendChild(MC.el("span", {}, "focus:"));
      MC.graphDetail.chain(m, n).forEach(function (c, i) { if (i) pathBar.appendChild(MC.el("span", {}, "→")); pathBar.appendChild(c); });
      pathBar.appendChild(MC.el("span", {}, "· everything else faded"));
    } else if (!Object.keys(m.nodes).length) {
      MC.clear(overview); overview.appendChild(MC.el("p", { "class": "dim" }, mode === "concepts" ? "no concepts yet: run handoff knowledge" : "nothing in the graph yet"));
    } else MC.graphSide.render(overview, m, { by: "session", only: opts.only }, { select: select, only: setOnly, edgeColour: edgeColour });
  }

  var pinning = false;
  var on = {
    mode: function (m) { mode = m; show(); setTimeout(function () { fit(400, 40); }, 900); },
    toggle: function (k) { opts.kinds[k] = !opts.kinds[k]; sync(opts.full); },
    fit: function () { fit(400, 40); },
    pin: function () { pinning = !pinning; panel(); },
    unpin: function () { Object.keys(nodes).forEach(function (k) { nodes[k].fx = nodes[k].fy = undefined; }); fg.d3ReheatSimulation(); }
  };
  function setOnly(g) { opts.only = opts.only === g ? null : g; sync(opts.full); setTimeout(function () { fit(400, 60); }, 700); }

  function resize() { var box = holder.parentNode.getBoundingClientRect(); fg.width(Math.max(300, box.width)).height(box.height); }

  function show() {
    document.getElementById("mem-list").hidden = mode !== "memory";
    var v = last[mode]; nodes = {}; plain = []; links = []; selected = null; opts.only = null;
    fg.graphData({ nodes: [], links: [] });
    if (v && v.nodes.length) sync(v); else { opts.model = M.build({ nodes: [], edges: [] }); panel(); }
  }

  fg.onLinkHover(function (l) { hoverLink = l || null; holder.style.cursor = l ? "pointer" : "default"; });
  fg.onNodeHover(function (n) {
    hover = n || null; holder.style.cursor = n ? "pointer" : "default"; tip.hidden = !n;
    if (n) tip.textContent = n.kind + (n.role ? " (" + n.role + ")" : "") + ": " + stamp(n) + name(n);
  });
  holder.addEventListener("mousemove", function (ev) { var b = holder.getBoundingClientRect(); tip.style.left = Math.min(ev.clientX - b.left + 14, b.width - 340) + "px"; tip.style.top = (ev.clientY - b.top + 14) + "px"; });
  fg.onNodeClick(function (n) { selected = n; panel(); });
  // Anything that is not a node puts the graph back to normal: no selection, nothing faded.
  function clearFocus() { selected = null; hover = null; hoverLink = null; tip.hidden = true; panel(); }
  fg.onBackgroundClick(clearFocus).onLinkClick(clearFocus);
  holder.addEventListener("mouseleave", function () { hover = null; hoverLink = null; tip.hidden = true; });
  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") clearFocus(); });
  // Nodes float free by default; "pin on drag" makes a dragged node stay where it is put.
  fg.onNodeDragEnd(function (n) { if (pinning) { n.fx = n.x; n.fy = n.y; } });
  window.addEventListener("resize", resize);

  function update(state) {
    var sig = JSON.stringify([state.work, state.concepts]);
    if (sig === last.sig) return;
    last = { work: state.work, concepts: state.concepts, memory: last.memory, sig: sig };
    var v = last[mode], first = !Object.keys(nodes).length;
    if (v && (v.nodes.length || mode === "work")) sync(v); else show();
    if (first && visible) setTimeout(function () { fit(400, 40); }, 900);
  }

  // Draw one kind of memory (from the memory page) as its own small graph, in its own mode.
  function showMemory(kind, view) {
    last.memory = view; mode = "memory"; opts.memoryKind = kind;
    show(); MC.memoryDetail.listKind(kind, document.getElementById("mem-list"));
    setTimeout(function () { fit(400, 40); }, 900);
  }

  // Jump to one node (from a connection card): select it, centre on it and zoom to read it.
  function select(id) {
    var n = nodes[id]; if (!n) return;
    selected = n; panel();
    fg.centerAt(n.x, n.y, 500); fg.zoom(Math.max(fg.zoom(), 2.4), 500);
  }

  MC.views.graph = { context: function () { return selected ? "the " + selected.kind + " \"" + selected.text.slice(0, 200) + "\" (" + selected.role + ") is selected in the " + mode + " graph" : "the " + mode + " graph, nothing selected"; }, update: update, select: select, showMemory: showMemory, setVisible: function (v) { visible = v; if (v) { resize(); setTimeout(function () { fit(400, 40); }, 900); } else fg.pauseAnimation(); if (v) fg.resumeAnimation(); } };
  resize();
})();
