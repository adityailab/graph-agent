// Shared helpers for every view. All text from the graph goes in with textContent, never innerHTML.
(function () {
  "use strict";
  var PALETTE = { frontend: "#38bdf8", backend: "#a78bfa", deploy: "#fbbf24", person: "#4ade80", shared: "#f87171" };
  var EXTRA = ["#f472b6", "#2dd4bf", "#fb923c", "#a3e635", "#e879f9"];
  var assigned = {};
  var SVG_TAGS = ["svg", "g", "circle", "line", "path", "text", "rect", "defs"];
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function color(role) {
    if (!role) return "#64748b";
    if (PALETTE[role]) return PALETTE[role];
    if (!assigned[role]) assigned[role] = EXTRA[Object.keys(assigned).length % EXTRA.length];
    return assigned[role];
  }

  function el(tag, attrs, text) {
    var node = SVG_TAGS.indexOf(tag) >= 0
      ? document.createElementNS("http://www.w3.org/2000/svg", tag)
      : document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

  // Who an event is aimed at, read from the feed text: {from, to} or null for events about one role.
  function route(ev) {
    var m;
    if ((m = /^to ([\w-]+):/.exec(ev.text)) && ev.kind !== "READ") return { from: ev.role, to: m[1] };
    if ((m = /^from ([\w-]+):/.exec(ev.text)) && ev.kind === "NEEDS") return { from: ev.role, to: m[1] };
    if ((m = /^([\w-]+) work:/.exec(ev.text)) && ev.kind === "READ") return { from: m[1], to: ev.role };
    return null;
  }

  // Count a number up (or down) to its new value so changes are noticeable.
  function countTo(node, value) {
    var from = Number(node.getAttribute("data-v") || 0);
    node.setAttribute("data-v", String(value));
    if (reduced || from === value) { node.textContent = String(value); return; }
    var start = performance.now();
    (function tick(now) {
      var t = Math.min(1, (now - start) / 600);
      node.textContent = String(Math.round(from + (value - from) * t));
      if (t < 1) requestAnimationFrame(tick);
    })(start);
  }

  window.MC = { color: color, el: el, clear: clear, route: route, countTo: countTo, reduced: reduced, views: {} };
})();
