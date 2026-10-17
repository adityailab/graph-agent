// The dashed hull round each session's (or topic's) nodes, its name and size, a "hidden: N · show"
// link, and between hulls the pill that says what travelled: read ╌╌, message ━━, need ···.
(function () {
  "use strict";
  var MC = window.MC, SIDE = 78, TOP = 54, BOTTOM = 82;
  var DASH = { read: [6, 4], need: [2, 4], message: [] }, VAR = { read: "--amber", need: "--red", message: "--teal" };
  var boxes = {}, more = [];

  function measure(nodes, groupOf) {
    boxes = {};
    nodes.forEach(function (n) {
      if (n.x === undefined) return;
      var g = groupOf(n), b = boxes[g] || (boxes[g] = { x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity, n: 0 });
      b.x0 = Math.min(b.x0, n.x - SIDE); b.y0 = Math.min(b.y0, n.y - TOP); b.x1 = Math.max(b.x1, n.x + SIDE); b.y1 = Math.max(b.y1, n.y + BOTTOM); b.n++;
    });
  }

  // `o`: colour(group), total(group), hidden(group), expanded(group).
  function draw(ctx, scale, nodes, groupOf, o) {
    measure(nodes, groupOf); more = [];
    Object.keys(boxes).forEach(function (g) {
      var b = boxes[g], c = o.colour(g), w = b.x1 - b.x0, h = b.y1 - b.y0, r = 14 / scale * Math.min(1, scale);
      ctx.beginPath(); ctx.roundRect(b.x0, b.y0, w, h, 14); ctx.fillStyle = MC.graphPaint.alpha(c, 0.06); ctx.fill();
      ctx.setLineDash([5 / scale, 4 / scale]); ctx.strokeStyle = c; ctx.lineWidth = 1.2 / scale; ctx.stroke(); ctx.setLineDash([]);
      ctx.textAlign = "right"; ctx.font = "500 " + (11.5 / scale) + "px " + MC.graphPaint.FONT; ctx.fillStyle = MC.css("--dim");
      var count = o.total(g) + " nodes", x = b.x1 - 10 / scale;
      ctx.fillText(count, x, b.y0 + 17 / scale);
      ctx.font = "700 " + (13 / scale) + "px " + MC.graphPaint.FONT; ctx.fillStyle = c;
      ctx.fillText(g, x - ctx.measureText(count).width - 18 / scale, b.y0 + 17 / scale);
      hiddenLink(ctx, scale, b, g, o);
    });
  }

  // "hidden: N · show" at the hull's bottom edge; a click on "show" opens the group's other nodes.
  function hiddenLink(ctx, scale, b, g, o) {
    var hidden = o.hidden(g), opened = o.expanded(g);
    if (!hidden && !opened) return;
    var lead = opened ? "" : "hidden: " + hidden + " · ", word = opened ? "hide extras" : "show", x = b.x0 + 10 / scale, y = b.y1 - 8 / scale;
    ctx.textAlign = "left"; ctx.font = "500 " + (11.5 / scale) + "px " + MC.graphPaint.FONT; ctx.fillStyle = MC.css("--dim"); ctx.fillText(lead, x, y);
    var lw = ctx.measureText(lead).width; ctx.fillStyle = MC.css("--blue"); ctx.fillText(word, x + lw, y);
    more.push({ g: g, x0: x + lw, x1: x + lw + ctx.measureText(word).width, y0: y - 14 / scale, y1: y + 4 / scale });
  }

  // Which "show" link, if any, a point on the canvas is on.
  function hit(x, y) {
    var found = more.filter(function (m) { return x >= m.x0 && x <= m.x1 && y >= m.y0 && y <= m.y1; })[0];
    return found ? found.g : null;
  }

  function edge(box, p, d) {
    var cx = (box.x0 + box.x1) / 2, cy = (box.y0 + box.y1) / 2, hw = (box.x1 - box.x0) / 2, hh = (box.y1 - box.y0) / 2;
    var tx = d.x ? (Math.sign(d.x) * hw - (p.x - cx)) / d.x : Infinity, ty = d.y ? (Math.sign(d.y) * hh - (p.y - cy)) / d.y : Infinity;
    var t = Math.min(tx > 0 ? tx : Infinity, ty > 0 ? ty : Infinity);
    return { x: p.x + d.x * t, y: p.y + d.y * t };
  }

  function arrow(ctx, from, to, scale) {
    var a = Math.atan2(to.y - from.y, to.x - from.x), s = 9 / scale;
    ctx.beginPath(); ctx.moveTo(to.x, to.y); ctx.lineTo(to.x - s * Math.cos(a - 0.4), to.y - s * Math.sin(a - 0.4)); ctx.lineTo(to.x - s * Math.cos(a + 0.4), to.y - s * Math.sin(a + 0.4)); ctx.closePath(); ctx.fill();
  }

  function pill(ctx, text, x, y, scale, colour) {
    ctx.font = "700 " + (11.5 / scale) + "px " + MC.graphPaint.FONT; ctx.textAlign = "center";
    var w = ctx.measureText(text).width + 14 / scale, h = 17 / scale;
    ctx.beginPath(); ctx.roundRect(x - w / 2, y - h / 2, w, h, h / 2); ctx.fillStyle = MC.css("--bg"); ctx.fill();
    ctx.strokeStyle = MC.css("--line"); ctx.lineWidth = 1 / scale; ctx.setLineDash([]); ctx.stroke();
    ctx.fillStyle = colour; ctx.fillText(text, x, y + 4 / scale);
  }

  // One line between two hulls per kind of traffic, each with its pill ("read ×5 → backend").
  function pills(ctx, scale, cross) {
    var slot = {};
    cross.forEach(function (c) {
      var a = boxes[c.from], b = boxes[c.to];
      if (!a || !b) return;
      var pair = c.from + ">" + c.to, i = slot[pair] = (slot[pair] || 0) + 1, colour = MC.css(VAR[c.kind]);
      var ca = { x: (a.x0 + a.x1) / 2, y: (a.y0 + a.y1) / 2 }, cb = { x: (b.x0 + b.x1) / 2, y: (b.y0 + b.y1) / 2 };
      var dx = cb.x - ca.x, dy = cb.y - ca.y, len = Math.hypot(dx, dy) || 1, off = (c.from < c.to ? 1 : -1) * 18 + (i - 1) * 8;
      var p = { x: ca.x - dy / len * off, y: ca.y + dx / len * off }, q = { x: cb.x - dy / len * off, y: cb.y + dx / len * off };
      var s = edge(a, p, { x: dx, y: dy }), e = edge(b, q, { x: -dx, y: -dy });
      ctx.strokeStyle = colour; ctx.fillStyle = colour; ctx.lineWidth = (1.6 + Math.min(3, c.count * 0.25)) / scale; ctx.setLineDash(DASH[c.kind].map(function (v) { return v / scale; }));
      ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(e.x, e.y); ctx.stroke(); ctx.setLineDash([]); arrow(ctx, s, e, scale);
      pill(ctx, c.kind + " ×" + c.count + " → " + c.to, (s.x + e.x) / 2 - dy / len * (i - 1) * 20 / scale, (s.y + e.y) / 2 + dx / len * (i - 1) * 20 / scale, scale, colour);
    });
  }

  window.MC.graphHulls = { draw: draw, pills: pills, hit: hit };
})();
