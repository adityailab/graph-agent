// The graph page: groups the work graph into one hull per session, shows decisions and needs first,
// and keeps the toolbar, the canvas and the side panel in step with one another.
(function () {
  "use strict";
  var MC = window.MC, M = MC.graphModel, st = MC.graphState, C = MC.graphCanvas, fg = C.fg, s = st.s;
  var bar = document.getElementById("graph-bar"), overview = document.getElementById("side-overview"), detail = document.getElementById("detail");
  var pathBar = document.getElementById("path-bar"), memList = document.getElementById("mem-list"), tip = document.getElementById("tip"), holder = document.getElementById("graph");
  var last = { work: null, concepts: null, memory: null, sig: "" }, cache = {}, sideOn = { select: select, only: setOnly };

  // Pulls every node toward its own cell, so the hulls stay apart and every caption has room.
  function cluster() {
    return function (alpha) { Object.keys(st.vis.ids).forEach(function (id) { var n = cache[id]; if (n.tx !== undefined && n.vx !== undefined) { n.vx += (n.tx - n.x) * 0.35 * alpha; n.vy += (n.ty - n.y) * 0.35 * alpha; } }); };
  }

  // Pushes nodes that sit closer than a label's width apart, so captions stay readable.
  function separate() {
    return function (alpha) {
      var list = Object.keys(st.vis.ids).map(function (id) { return cache[id]; });
      for (var i = 0; i < list.length; i++) for (var j = i + 1; j < list.length; j++) {
        var a = list[i], b = list[j], dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 0.01, min = 66;
        if (d < min) { var k = (min - d) / d * 0.5 * alpha * 2; a.vx -= dx * k; a.vy -= dy * k; b.vx += dx * k; b.vy += dy * k; }
      }
    };
  }

  function node(id, cell) {
    var d = st.model.nodes[id], g = st.hulls() ? M.group(st.model, d, s.by) : "", t = cell[id];
    var n = cache[id] || (cache[id] = t ? { x: t.x, y: t.y } : { x: Math.random() * 60 - 30, y: Math.random() * 60 - 30 });
    return Object.assign(n, { id: id, kind: d.kind, text: d.text, role: d.role, at: d.at, status: d.status, g: g, tx: t && t.x, ty: t && t.y });
  }

  // Works out what is on the canvas from the model and the choices, and hands it to the library.
  function apply() {
    var m = st.model;
    st.vis = M.visible(m, { kinds: s.kinds, group: st.hulls() ? s.by : "none", only: st.plain() ? null : s.only, expanded: s.expanded, focus: s.selected, all: st.plain() });
    var totals = {}, byGroup = {}, seen = {}, ids = Object.keys(st.vis.ids);
    Object.keys(m.nodes).forEach(function (id) { if (m.nodes[id].kind !== "Session") { var g = M.group(m, m.nodes[id], s.by); totals[g] = (totals[g] || 0) + 1; } });
    st.totals = totals;
    ids.forEach(function (id) { var g = M.group(m, m.nodes[id], s.by); (byGroup[g] = byGroup[g] || []).push(id); });
    var cell = st.hulls() ? MC.graphLayout.place(byGroup, m.nodes) : {};
    var links = m.edges.filter(function (e) { return st.vis.ids[e.source] && st.vis.ids[e.target]; }).map(function (e) {
      var key = [e.source, e.target].sort().join("|"), i = seen[key] = (seen[key] || 0) + 1;
      return { source: e.source, target: e.target, kind: e.kind, curve: i === 1 ? 0 : 0.22 * (i % 2 ? i : -i) / 1.5 };
    });
    var small = ids.length < 12, grouped = st.hulls();
    fg.d3Force("link").distance(small ? 130 : 60).strength(grouped ? 0.02 : 0.3); fg.d3Force("charge").strength(small ? -240 : grouped ? -10 : -160);
    fg.d3Force("cluster", grouped ? cluster() : null); fg.d3Force("separate", grouped ? null : separate());
    fg.graphData({ nodes: ids.map(function (id) { return node(id, cell); }), links: links });
  }

  function pathLine(n) {
    pathBar.hidden = !n; MC.clear(pathBar);
    if (!n) return;
    pathBar.appendChild(el("span", {}, "focus:"));
    MC.graphDetail.chain(st.model, n).forEach(function (c, i) { if (i) pathBar.appendChild(el("span", {}, "→")); pathBar.appendChild(c); });
    pathBar.appendChild(el("span", {}, "· everything else faded"));
  }
  function el(tag, a, t) { return MC.el(tag, a, t); }

  function renderSide() {
    var n = s.selected && st.model.nodes[s.selected];
    if (s.selected && !n) { s.selected = null; apply(); }
    detail.hidden = !n; overview.hidden = !!n; pathLine(n || null);
    if (n) MC.graphDetail.show(detail, st.model, n, { select: select, back: clearFocus });
    else MC.graphSide.render(overview, st.model, s, sideOn);
    var empty = !Object.keys(st.model.nodes).length;
    if (empty) { MC.clear(overview); overview.appendChild(el("p", { "class": "dim" }, s.mode === "concepts" ? "no concepts yet: run handoff knowledge" : "nothing in the graph yet")); }
  }

  var on = {
    mode: function (m) { s.mode = m; s.selected = null; s.only = null; s.expanded = {}; load(); setTimeout(function () { C.fit(400, 40); }, 900); },
    group: function (g) { s.by = g; s.only = null; s.expanded = {}; refresh(); },
    toggle: function (k) { s.kinds[k] = !s.kinds[k]; refresh(); },
    fit: function () { C.fit(400, 40); }, unpin: function () { Object.keys(cache).forEach(function (k) { cache[k].fx = cache[k].fy = undefined; }); fg.d3ReheatSimulation(); },
    pin: function () { s.pinning = !s.pinning; renderBar(); }
  };

  function renderBar() { MC.graphBar.render(bar, s, M.counts(st.model, s.only, s.by), on); }
  function refresh() { apply(); renderBar(); renderSide(); fg.d3ReheatSimulation(); }
  function setOnly(g) { s.only = s.only === g ? null : g; refresh(); setTimeout(function () { C.fit(400, 60); }, 700); }
  function clearFocus() { s.selected = null; st.hover = null; st.hoverLink = null; tip.hidden = true; refresh(); }

  // Open one node: its neighbourhood joins the canvas and everything else fades. A jump from a
  // connection card also centres and zooms on it.
  function select(id, jump) {
    s.selected = id; refresh();
    if (jump !== false) setTimeout(function () { var n = cache[id]; if (n && n.x !== undefined) { fg.centerAt(n.x, n.y, 500); fg.zoom(Math.max(fg.zoom(), 2.4), 500); } }, 300);
  }

  function load() {
    var v = last[s.mode] || { nodes: [], edges: [] };
    st.model = M.build(v); cache = {}; st.hover = null; st.hoverLink = null; memList.hidden = s.mode !== "memory";
    fg.graphData({ nodes: [], links: [] }); refresh();
  }

  fg.onNodeClick(function (n) { select(n.id, false); });
  fg.onBackgroundClick(function (ev) { var g = C.hit(ev); if (g) { s.expanded[g] = !s.expanded[g]; refresh(); } else clearFocus(); });
  fg.onLinkClick(clearFocus);
  fg.onNodeHover(function (n) { st.hover = n || null; holder.style.cursor = n ? "pointer" : "default"; tip.hidden = !n; if (n) tip.textContent = n.kind + (n.role ? " (" + n.role + ")" : "") + ": " + (n.at ? MC.clock(n.at) + " " : "") + short(n.text); });
  fg.onLinkHover(function (l) { st.hoverLink = l || null; });
  fg.onNodeDragEnd(function (n) { if (s.pinning) { n.fx = n.x; n.fy = n.y; } });
  function short(t) { var one = t.replace(/\s+/g, " ").trim(); return one.length > 48 ? one.slice(0, 47).replace(/\s+\S*$/, "") + "…" : one; }
  holder.addEventListener("mousemove", function (ev) { var b = holder.getBoundingClientRect(); tip.style.left = Math.min(ev.clientX - b.left + 14, b.width - 340) + "px"; tip.style.top = (ev.clientY - b.top + 14) + "px"; });
  holder.addEventListener("mouseleave", function () { st.hover = null; st.hoverLink = null; tip.hidden = true; });
  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape" && s.selected) clearFocus(); });
  C.onStop(function () { if (C.isVisible() && !s.selected) C.fit(300, 60); });

  function update(state) {
    var sig = JSON.stringify([state.work, state.concepts]);
    if (sig === last.sig) return;
    var first = !st.model || !Object.keys(st.model.nodes).length;
    last = { work: state.work, concepts: state.concepts, memory: last.memory, sig: sig };
    var v = last[s.mode];
    if (!v) return;
    st.model = M.build(v); refresh();
    if (first && C.isVisible()) setTimeout(function () { C.fit(400, 40); }, 900);
  }

  // One kind of memory (from the memory page) drawn as its own small graph, in its own mode.
  function showMemory(kind, view) {
    last.memory = view; s.memoryKind = kind; on.mode("memory");
    MC.memoryDetail.listKind(kind, memList);
  }

  MC.views.graph = { update: update, select: select, showMemory: showMemory, setVisible: function (v) { C.setVisible(v); if (v) setTimeout(function () { C.fit(400, 40); }, 900); } };
  st.model = M.build({ nodes: [], edges: [] }); renderBar();
})();
