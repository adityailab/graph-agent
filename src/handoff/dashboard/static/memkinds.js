// How the six kinds of memory feed each other, drawn as a small workflow: events are distilled into
// decisions, decisions harden into rules, rules and matching decisions load into each live session;
// social spreads decisions between sessions and temporal orders everything. Click a kind to open it.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var COLOUR = { working: "--blue", episodic: "--teal", semantic: "--purple", procedural: "--amber", temporal: "--red", social: "--green" };
  // The short line on each card; the longer explanation lives in the docs and the opened graph.
  var GLOSS = { working: "what sessions hold", episodic: "what happened, in order", semantic: "what things mean", procedural: "standing rules", temporal: "when things happened, and what replaced what", social: "who knows what" };
  // x, y, width, height of each card; the temporal card is the wide one underneath.
  var BOX = { social: [270, 14, 170, 70], episodic: [20, 134, 170, 78], semantic: [270, 134, 170, 78], procedural: [520, 134, 170, 78], working: [770, 134, 170, 78], temporal: [20, 262, 920, 52] };
  var ARROWS = [["M190,173 L268,173", "distilled", 229, 173, 64], ["M440,173 L518,173", "hardens", 479, 173, 64], ["M690,173 L768,173", "loaded", 729, 173, 56],
    ["M355,84 L355,132", "spreads", 355, 108, 62], ["M355,262 L355,214", "ordered", 355, 238, 60], ["M105,262 L105,214", "ordered", 105, 238, 60],
    ["M440,148 Q605,70 770,150", "relevant decisions loaded", 605, 92, 168]];

  function arrow(g, a) {
    g.appendChild(el("path", { "class": "karrow", d: a[0], "marker-end": "url(#ka)" }));
    g.appendChild(el("rect", { "class": "pill-box", x: a[2] - a[4] / 2, y: a[3] - 9, width: a[4], height: 18, rx: 6 }));
    g.appendChild(el("text", { "class": "kpill", x: a[2], y: a[3] + 4, "text-anchor": "middle" }, a[1]));
  }

  function card(g, t) {
    var b = BOX[t.key]; if (!b) return;
    var x = b[0], y = b[1], w = b[2], h = b[3], wide = w > 400, c = MC.css(COLOUR[t.key] || "--dim");
    var k = el("g", { "class": "kcard", role: "button", tabindex: "0", "aria-label": t.name + ", " + t.count + ": " + t.what + ". Open as a graph" });
    k.appendChild(el("rect", { "class": "kbox", x: x, y: y, width: w, height: h, rx: 8 }));
    k.appendChild(el("rect", { x: x, y: y, width: w, height: 4, fill: c }));
    k.appendChild(el("text", { "class": "kname", x: x + 12, y: y + 24 }, t.name));
    var n = el("text", { "class": "kcount", x: x + w - 12, y: y + (wide ? 34 : 28), "text-anchor": "end", fill: c }, "0"); k.appendChild(n); MC.countTo(n, t.count, "memory:" + t.key);
    k.appendChild(el("text", { "class": "kwhat", x: wide ? x + 110 : x + 12, y: wide ? y + 24 : y + 45 }, GLOSS[t.key] || t.what));
    k.appendChild(el("text", { "class": "kdet", x: x + 12, y: wide ? y + 42 : y + 62 }, MC.wrap(t.detail, wide ? 150 : 29, 1)[0]));
    var open = function () { MC.memoryDetail.openGraph(t.key); };
    k.addEventListener("click", open);
    k.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
    g.appendChild(k);
  }

  function draw(box, types) {
    var svg = el("svg", { id: "kinds", viewBox: "0 0 960 330", role: "group", "aria-label": "How the six kinds of memory feed each other" }), g = el("g");
    var defs = el("defs"), m = el("marker", { id: "ka", viewBox: "0 0 10 10", refX: "9", refY: "5", markerUnits: "userSpaceOnUse", markerWidth: "10", markerHeight: "10", orient: "auto" });
    m.appendChild(el("path", { d: "M0,0 L10,5 L0,10 z", "class": "ah" })); defs.appendChild(m); svg.appendChild(defs); svg.appendChild(g);
    ARROWS.forEach(function (a) { arrow(g, a); });
    types.forEach(function (t) { card(g, t); });
    var wrap = el("div", { "class": "svg-scroll" }); wrap.appendChild(svg); box.appendChild(wrap);
  }

  window.MC.memKinds = { draw: draw };
})();
