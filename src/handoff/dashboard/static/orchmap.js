// The orchestration drawing: a card per session and one arrow per direction between two sessions,
// carrying a pill that says what travels (message ━━, read ╌╌, need ···) and how many.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var CARD_W = 250, CARD_H = 116, LINE_H = 14, MIN_PILL = 150, WIDTH = 960;
  var GLYPH = { message: "━━", nudge: "━━", digest: "━━", read: "╌╌", need: "···", question: "?", standin_answer: "↩" };
  var KINDS = ["message", "nudge", "digest", "question", "standin_answer", "read", "need"];

  function label(kind) { return kind.replace("_", " "); }
  function dir(a, b) { return a.source === b.source ? KINDS.indexOf(a.kind) - KINDS.indexOf(b.kind) : 0; }

  // Where each session sits: alone in the middle, side by side, or round an ellipse starting at the top.
  function place(roles) {
    var names = roles.map(function (r) { return r.role; }).sort(), pos = Object.create(null), n = names.length;
    names.forEach(function (name, i) {
      if (n === 1) pos[name] = { x: WIDTH / 2, y: 90 };
      else if (n === 2) pos[name] = { x: 155 + i * 650, y: 90 };
      else {
        var angle = (-90 + (360 / n) * i) * Math.PI / 180;
        pos[name] = { x: WIDTH / 2 + 375 * Math.cos(angle), y: 263 + 189 * Math.sin(angle) };
      }
    });
    return pos;
  }

  // Where a line starting at `p` (inside the card centred on `c`) in direction `d` leaves the card.
  function leave(c, p, d) {
    var hw = CARD_W / 2 + 5, hh = CARD_H / 2 + 5;
    var tx = d.x ? (Math.sign(d.x) * hw - (p.x - c.x)) / d.x : Infinity, ty = d.y ? (Math.sign(d.y) * hh - (p.y - c.y)) / d.y : Infinity;
    var t = Math.min(tx > 0 ? tx : Infinity, ty > 0 ? ty : Infinity);
    return { x: p.x + d.x * t, y: p.y + d.y * t };
  }

  // The line between two cards. With one in each direction the two run side by side, `o` apart
  // (their pills then never meet); alone, a line bows a little. Returns the path and the pill's centre.
  function curve(a, b, o, bow) {
    var dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1, nx = -dy / len, ny = dx / len;
    var a2 = { x: a.x + nx * o, y: a.y + ny * o }, b2 = { x: b.x + nx * o, y: b.y + ny * o };
    var s = leave(a, a2, { x: dx, y: dy }), e = leave(b, b2, { x: -dx, y: -dy });
    var cx = (s.x + e.x) / 2 + nx * bow, cy = (s.y + e.y) / 2 + ny * bow;
    return { d: "M" + s.x + "," + s.y + " Q" + cx + "," + cy + " " + e.x + "," + e.y, mx: (s.x + 2 * cx + e.x) / 4, my: (s.y + 2 * cy + e.y) / 4 };
  }

  function size(p, latest) {
    var rows = p.kinds.map(function (f) { return GLYPH[f.kind] + " " + label(f.kind) + " ×" + f.count; });
    var route = p.source + " → " + p.target, tag = latest ? "● latest " + MC.clock(p.at) : "";
    var longest = Math.max(route.length, tag.length, Math.max.apply(null, rows.map(function (r) { return r.length; })));
    return { rows: rows, route: route, tag: tag, w: Math.max(MIN_PILL, longest * 6.6 + 18), h: (1 + rows.length + (latest ? 1 : 0)) * LINE_H + 10 };
  }

  function pill(group, p, c, z) {
    var x = c.mx - z.w / 2, y = c.my - z.h / 2, yy = y + 15;
    group.appendChild(el("rect", { "class": "pill-box", x: x, y: y, width: z.w, height: z.h, rx: 8 }));
    group.appendChild(el("text", { "class": "pill-route", x: x + 9, y: yy }, z.route));
    if (z.tag) group.appendChild(el("text", { "class": "pill-tag", x: x + 9, y: (yy += LINE_H) }, z.tag));
    p.kinds.forEach(function (f, i) { group.appendChild(el("text", { "class": "pill-line k-" + f.kind, x: x + 9, y: yy + LINE_H * (i + 1) }, z.rows[i])); });
  }

  // How far apart two opposite lines run: enough that their pills do not overlap along the normal.
  function apart(a, b, z) {
    var dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1;
    return Math.min(78, (Math.abs(dy) / len * z.w + Math.abs(dx) / len * z.h) / 2 + 8);
  }

  // One arrow per direction. Returns {key: path} so a travelling square can ride the same line.
  function drawEdges(layer, flows, pos) {
    MC.clear(layer);
    var by = Object.create(null), newest = flows.reduce(function (m, f) { return Math.max(m, f.last_at); }, 0), paths = Object.create(null);
    flows.forEach(function (f) {
      if (!pos[f.source] || !pos[f.target] || f.source === f.target) return;
      var key = f.source + ">" + f.target, p = by[key] || (by[key] = { source: f.source, target: f.target, kinds: [], total: 0, at: 0 });
      p.kinds.push(f); p.total += f.count; p.at = Math.max(p.at, f.last_at);
    });
    Object.keys(by).forEach(function (key) {
      var p = by[key], latest = p.at === newest && newest > 0, both = !!by[p.target + ">" + p.source];
      p.kinds.sort(dir);
      var z = size(p, latest), a = pos[p.source], b = pos[p.target], c = both ? curve(a, b, apart(a, b, z), 0) : curve(a, b, 0, 36);
      var g = el("g", { "class": "orch-edge" + (latest ? " latest" : ""), role: "img", "aria-label": p.source + " to " + p.target + ": " + p.kinds.map(function (f) { return label(f.kind) + " " + f.count; }).join(", ") });
      g.appendChild(el("path", { d: c.d, "class": "edge flow", "stroke-width": String(Math.min(5, 1.5 + p.total * 0.3)), "marker-end": "url(#oa)" }));
      pill(g, p, c, z); layer.appendChild(g); paths[key] = c.d;
    });
    return paths;
  }

  window.MC.orchMap = { CARD_W: CARD_W, CARD_H: CARD_H, WIDTH: WIDTH, place: place, drawEdges: drawEdges, curve: curve };
})();
