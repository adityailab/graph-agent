// Shared helpers for every view. All text from the graph goes in with textContent, never innerHTML.
(function () {
  "use strict";
  var PALETTE = Object.assign(Object.create(null), { frontend: "#38bdf8", backend: "#a78bfa", deploy: "#fbbf24", person: "#4ade80", shared: "#f87171" });
  var EXTRA = ["#f472b6", "#2dd4bf", "#fb923c", "#a3e635", "#e879f9"];
  var assigned = Object.create(null);
  var SVG_TAGS = ["svg", "g", "circle", "line", "path", "text", "rect", "defs"];
  var SENT = ["MESSAGE", "NUDGE", "DIGEST", "QUESTION", "STANDIN_ANSWER"];
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
    // Only these kinds are addressed; a prompt that merely starts with "to x:" must not fake a message.
    if (SENT.indexOf(ev.kind) >= 0 && (m = /^to ([\w-]+):/.exec(ev.text))) return { from: ev.role, to: m[1] };
    if (ev.kind === "NEEDS" && (m = /^from ([\w-]+):/.exec(ev.text))) return { from: ev.role, to: m[1] };
    if ((m = /^([\w-]+) work:/.exec(ev.text)) && ev.kind === "READ") return { from: m[1], to: ev.role };
    return null;
  }

  // Count a number up (or down) to its new value so changes are noticeable.
  var shown = Object.create(null);
  function countTo(node, value, key) {
    var from = key !== undefined && key in shown ? shown[key] : Number(node.getAttribute("data-v") || 0);
    if (key !== undefined) shown[key] = value;
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
