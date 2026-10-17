// How one node is drawn on the canvas: a diamond for a decision (rings for the sessions that
// learned it, dashed and hollow once replaced), a square for a need, a dot for the rest.
(function () {
  "use strict";
  var MC = window.MC;
  var SIZE = { Session: 6.5, Request: 3.6, Decision: 5, Need: 5, Edit: 2.6, File: 4, Message: 3.4, Convention: 4.5, Topic: 4 };
  var FONT = "Saira, ui-sans-serif, system-ui, sans-serif";
  var slots = {};

  function radius(n, readers) { return (SIZE[n.kind] || 5) + (n.kind === "Decision" ? Math.min(5, (readers || 0) * 1.3) : 0); }

  function fill(n) {
    if (n.role) return MC.color(n.role);
    if (!(n.kind in slots)) slots[n.kind] = Object.keys(slots).length % 5;
    return MC.css("--role-" + slots[n.kind]);
  }

  function shape(ctx, n, r) {
    ctx.beginPath();
    if (n.kind === "Decision") { ctx.moveTo(n.x, n.y - r * 1.3); ctx.lineTo(n.x + r * 1.3, n.y); ctx.lineTo(n.x, n.y + r * 1.3); ctx.lineTo(n.x - r * 1.3, n.y); ctx.closePath(); }
    else if (n.kind === "File" || n.kind === "Need" || n.kind === "Convention") ctx.rect(n.x - r, n.y - r, r * 2, r * 2);
    else ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
  }

  function caption(ctx, lines, x, y, scale, colour, bg) {
    ctx.font = (11.5 / scale) + "px " + FONT; ctx.textAlign = "center"; ctx.lineJoin = "round";
    lines.forEach(function (l, i) {
      ctx.strokeStyle = bg; ctx.lineWidth = 4 / scale; ctx.strokeText(l, x, y + i * 13 / scale);
      ctx.fillStyle = colour; ctx.fillText(l, x, y + i * 13 / scale);
    });
  }

  // One ring per session that learned the decision, each in that session's colour.
  function rings(ctx, n, r, readers, scale) {
    Object.keys(readers || {}).forEach(function (role, i) {
      ctx.beginPath(); ctx.arc(n.x, n.y, r * 1.3 + 3 + i * 3.2, 0, Math.PI * 2);
      ctx.strokeStyle = MC.color(role); ctx.lineWidth = 2 / scale; ctx.stroke();
    });
  }

  // `o`: pal (colours), readers, replaced, open (a need), selected, faded, label (lines or null).
  function node(ctx, n, scale, o) {
    var r = radius(n, Object.keys(o.readers || {}).length), colour = fill(n);
    ctx.globalAlpha = o.faded ? 0.16 : 1;
    shape(ctx, n, r);
    if (o.replaced) { ctx.fillStyle = o.pal.bg; ctx.fill(); ctx.strokeStyle = colour; ctx.lineWidth = 2 / scale; ctx.setLineDash([3 / scale, 2 / scale]); ctx.stroke(); ctx.setLineDash([]); }
    else if (n.kind === "Need") { ctx.fillStyle = o.pal.bg; ctx.fill(); ctx.strokeStyle = o.open ? o.pal.red : o.pal.dim; ctx.lineWidth = 2.5 / scale; ctx.stroke(); }
    else { ctx.fillStyle = colour; ctx.fill(); ctx.strokeStyle = o.pal.bg; ctx.lineWidth = 1.5 / scale; ctx.stroke(); }
    if (n.kind === "Decision") rings(ctx, n, r, o.readers, scale);
    if (o.selected) { ctx.beginPath(); ctx.arc(n.x, n.y, r * 1.3 + 7, 0, Math.PI * 2); ctx.strokeStyle = o.pal.ink; ctx.lineWidth = 2.5 / scale; ctx.stroke(); }
    if (o.label) caption(ctx, o.label, n.x, n.y + r * 1.3 + 12 / scale, scale, o.faded ? o.pal.dim : o.pal.ink, o.pal.bg);
    ctx.globalAlpha = 1;
  }

  // How a relationship is drawn: the shared line language for messages, reads and needs, neutral otherwise.
  var LANG = { CONSULTED: ["--amber", [6, 4], "╌╌"], SENT: ["--teal", [], "━━"], DELIVERED_TO: ["--teal", [], "━━"], REPLY_TO: ["--teal", [], "━━"], RAISED: ["--red", [2, 4], "···"], RESOLVED_BY: ["--red", [2, 4], "···"] };
  function link(kind) { var l = LANG[kind] || ["--dim", [], "──"]; return { colour: MC.css(l[0]), dash: l[1], glyph: l[2], plain: !LANG[kind] }; }

  function alpha(hex, a) {
    var n = parseInt(hex.slice(1), 16);
    return /^#[0-9a-f]{6}$/i.test(hex) ? "rgba(" + (n >> 16) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + a + ")" : hex;
  }

  window.MC.graphPaint = { alpha: alpha, link: link, node: node, shape: shape, radius: radius, caption: caption, fill: fill, FONT: FONT };
})();
