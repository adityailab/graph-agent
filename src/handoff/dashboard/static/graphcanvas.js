// The canvas itself, drawn with the force-graph library (the one the FalkorDB browser uses): drag a
// node, scroll to zoom (no cap), drag the background to pan. Hulls and pills are painted by
// graphhulls.js, each node by graphpaint.js; graph text never goes through the library as markup.
(function () {
  "use strict";
  var MC = window.MC, st = MC.graphState, P = MC.graphPaint, H = MC.graphHulls;
  var holder = document.getElementById("graph"), FIT_MAX = 2.2, pal = {}, visible = false, onStop = function () {};
  var topicSlots = {};

  function colourOf(g) {
    if (st.s.by === "topic") { if (!(g in topicSlots)) topicSlots[g] = Object.keys(topicSlots).length % 5; return MC.css("--role-" + topicSlots[g]); }
    return g === "shared" ? MC.css("--dim") : MC.color(g);
  }

  function label(n, scale, f) {
    var m = st.model, many = Object.keys(st.vis.ids).length > 45;
    var key = n.kind === "Decision" || n.kind === "Need" || n.kind === "Session";
    var show = n === f || (f && st.near(n.id)) || scale > 3.4 || (st.plain() ? Object.keys(m.nodes).length < 12 || n.kind === "Session" : key && (!many || scale > 1.8));
    return show ? MC.wrap(n.text, n === f ? 28 : 22, n === f ? 5 : 2) : null;
  }

  function paintNode(n, ctx, scale) {
    var m = st.model, f = st.focus() ? { id: st.focus() } : null, near = !f || st.near(n.id);
    P.node(ctx, n, scale, { pal: pal, readers: m.readers[n.id], replaced: !!m.replacedBy[n.id], open: n.status === "open", selected: n.id === st.s.selected,
      faded: !near && !(st.hoverLink && [st.hoverLink.source.id, st.hoverLink.target.id].indexOf(n.id) >= 0), label: label(n, scale, f && n.id === f.id ? n : null) });
  }

  var fg = ForceGraph()(holder).backgroundColor("rgba(0,0,0,0)").nodeId("id").cooldownTicks(220).nodeRelSize(1).nodeLabel(function () { return ""; })
    .linkDirectionalArrowLength(5).linkDirectionalArrowRelPos(1).linkCurvature("curve").minZoom(0.05).maxZoom(40)
    .onEngineStop(function () { onStop(); });
  fg.linkWidth(function (l) { return lit(l) ? 2.4 : 1.2; }).linkLineDash(function (l) { return P.link(l.kind).dash; });
  fg.linkColor(function (l) { var k = P.link(l.kind); return P.alpha(k.colour, st.focus() && !lit(l) ? 0.12 : k.plain ? 0.45 : 0.85); });
  function lit(l) { var f = st.focus(), a = l.source.id || l.source, b = l.target.id || l.target; return l === st.hoverLink || (!!f && (a === f || b === f)); }
  fg.d3Force("charge").strength(-90).distanceMax(400);

  fg.onRenderFramePre(function (ctx, scale) {
    pal = { ink: MC.css("--ink"), line: MC.css("--line"), bg: MC.css("--bg"), dim: MC.css("--dim"), red: MC.css("--red") };
    if (st.hulls()) H.draw(ctx, scale, fg.graphData().nodes, function (n) { return n.g; }, { colour: colourOf, total: function (g) { return st.totals[g] || 0; }, hidden: function (g) { return st.vis.hidden[g] || 0; }, expanded: function (g) { return !!st.s.expanded[g]; } });
  });
  fg.onRenderFramePost(function (ctx, scale) { if (st.hulls() && st.s.by === "session") H.pills(ctx, scale, st.model.cross); });
  fg.nodeCanvasObject(paintNode).nodePointerAreaPaint(function (n, colour, ctx) { P.shape(ctx, n, P.radius(n, 0) + 3); ctx.fillStyle = colour; ctx.fill(); });
  fg.linkCanvasObjectMode(function () { return "after"; }).linkCanvasObject(function (l, ctx, scale) {
    if (!(st.focus() ? lit(l) : scale > 1.6) || !l.source.x) return;
    var k = P.link(l.kind);
    P.caption(ctx, [l.kind.toLowerCase().replace("_", " ")], (l.source.x + l.target.x) / 2, (l.source.y + l.target.y) / 2, scale, k.colour, pal.bg);
  });

  function fit(ms, pad) { fg.zoomToFit(ms, pad); setTimeout(function () { if (fg.zoom() > FIT_MAX) fg.zoom(FIT_MAX, 250); }, ms + 60); }
  function resize() { var box = holder.parentNode.getBoundingClientRect(); fg.width(Math.max(300, box.width)).height(box.height); }
  window.addEventListener("resize", resize);
  resize();

  window.MC.graphCanvas = {
    fg: fg, fit: fit, resize: resize, hit: function (ev) { var p = fg.screen2GraphCoords(ev.offsetX, ev.offsetY); return H.hit(p.x, p.y); },
    onStop: function (fn) { onStop = fn; }, setVisible: function (v) { visible = v; if (v) { resize(); fg.resumeAnimation(); } else fg.pauseAnimation(); }, isVisible: function () { return visible; },
    edgeColour: function (k) { return P.link(k).colour; }
  };
})();
