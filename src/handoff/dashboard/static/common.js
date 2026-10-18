// Shared helpers for every view. All text from the graph goes in with textContent, never innerHTML.
(function () {
  "use strict";
  // Roles are told apart by shade (and by name), not hue: the page is black and white.
  var SLOT = Object.assign(Object.create(null), { frontend: 0, backend: 1, deploy: 2, person: 3 });
  var assigned = Object.create(null);
  var SVG_TAGS = ["svg", "g", "circle", "ellipse", "line", "path", "polygon", "text", "tspan", "rect", "defs", "marker"];
  var SENT = ["MESSAGE", "NUDGE", "DIGEST", "QUESTION", "STANDIN_ANSWER"];
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

  // A role's shade, read from the theme each call so light and dark both work.
  function color(role) {
    if (!role) return css("--dim");
    if (role === "shared") return css("--bg");  // hollow: told apart from every role's shade
    if (!(role in SLOT) && !(role in assigned)) assigned[role] = 4;
    return css("--role-" + (role in SLOT ? SLOT[role] : assigned[role]));
  }

  function clock(ms) {
    var d = new Date(ms), p2 = function (n) { return (n < 10 ? "0" : "") + n; };
    return p2(d.getHours()) + ":" + p2(d.getMinutes()) + ":" + p2(d.getSeconds());
  }

  function el(tag, attrs, text) {
    var node = SVG_TAGS.indexOf(tag) >= 0
      ? document.createElementNS("http://www.w3.org/2000/svg", tag)
      : document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    if (text !== undefined) node.textContent = text;
    return node;
  }

  // Text from the graph with its paths, constants and role names in colour. Spans only ever get
  // textContent, so nothing in the text can become markup.
  var ROLE_WORDS = [];
  function words(roles) { ROLE_WORDS = roles.slice(); }
  function rich(parent, text) {
    var roles = ROLE_WORDS.map(function (r) { return r.replace(/[^\w-]/g, ""); }).filter(Boolean).join("|");
    var re = new RegExp("(\\bwhy:|[\\w.\\-]*\\/[\\w.\\-\\/]+|\\b[A-Z][A-Z0-9_]{3,}\\b" + (roles ? "|\\b(?:" + roles + ")\\b" : "") + ")", "g");
    var last = 0, m;
    while ((m = re.exec(text))) {
      if (m.index > last) parent.appendChild(document.createTextNode(text.slice(last, m.index)));
      var w = m[0], cls = w === "why:" ? "t-why" : ROLE_WORDS.indexOf(w) >= 0 ? "t-role" : /^[A-Z0-9_]+$/.test(w) ? "t-const" : "t-path";
      var span = el("span", { "class": cls }, w);
      if (cls === "t-role") span.style.color = color(w);
      parent.appendChild(span); last = m.index + w.length;
    }
    if (last < text.length) parent.appendChild(document.createTextNode(text.slice(last)));
    return parent;
  }

  // Word-wrap to at most `lines` lines of `width` characters; the last line ends with … only if cut.
  function wrap(text, width, lines) {
    var out = [], line = "";
    text.split(/\s+/).forEach(function (w) {
      if (line && (line + " " + w).length > width) { out.push(line); line = w; } else line = line ? line + " " + w : w;
    });
    if (line) out.push(line);
    if (out.length > lines) { out = out.slice(0, lines); out[lines - 1] = out[lines - 1].slice(0, width - 1) + "…"; }
    return out;
  }

  // A small pill naming a thing, with a dot in `colour` (a CSS colour); `solid` fills it.
  function chip(label, colour, solid) {
    var c = el("span", { "class": "chip" + (solid ? " solid" : "") }, label);
    if (colour) c.style.setProperty("--c", colour);
    return c;
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

  // Long text shows three lines; a click opens all of it (and a click again folds it back).
  function clamp(node) {
    node.classList.add("clamp"); node.title = "click to read all of it";
    node.addEventListener("click", function (ev) {
      if (ev.target.closest && ev.target.closest("a")) return;
      node.classList.toggle("open");
    });
    return node;
  }

  window.MC = { chip: chip, clamp: clamp, wrap: wrap, rich: rich, words: words, css: css, clock: clock, color: color, el: el, clear: clear, route: route, countTo: countTo, reduced: reduced, views: {} };
})();
