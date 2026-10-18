// The handoff page, drawn like orchestration (the same cards, arrows and pills) but counting what
// learning looks like: an arrow runs from the session that made decisions to the one that read them.
// Click an arrow or a session and the hand-offs behind it open below as cards.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el, map = MC.orchMap;
  var svg = document.getElementById("hf-graph"), detail = document.getElementById("hf-detail"), stats = document.getElementById("hf-stats");
  var layers = { edges: el("g"), live: el("g"), nodes: el("g") }, selected = null, signature = "", pos = {}, paths = {}, rings = {};
  svg.appendChild(layers.edges); svg.appendChild(layers.live); svg.appendChild(layers.nodes);

  function pairs(handoffs) {
    var by = {};
    handoffs.forEach(function (h) {
      var k = h.author + ">" + h.reader, p = by[k] || (by[k] = { author: h.author, reader: h.reader, list: [], decisions: 0, at: 0 });
      p.list.push(h); p.decisions += h.decisions.length; p.at = Math.max(p.at, h.at);
    });
    return Object.keys(by).map(function (k) { return by[k]; });
  }

  // The orchestration drawing takes lines of (source, target, kind, count); here the kinds are decisions and reads.
  function flows(list) {
    var out = [];
    list.forEach(function (p) {
      out.push({ source: p.author, target: p.reader, kind: "decision", count: p.decisions, last_at: p.at });
      out.push({ source: p.author, target: p.reader, kind: "read", count: p.list.length, last_at: p.at });
    });
    return out;
  }

  function info(state, r) {
    var learned = state.handoffs.reduce(function (n, h) { return n + (h.reader === r.role ? h.decisions.length : 0); }, 0), own = r.requests + r.decisions + r.edits;
    return { kind: "", text: "", stats: own + " own · " + learned + " learned" };
  }

  function select(sel, state) {
    selected = sel;
    var mine = state.handoffs.filter(function (h) {
      return sel.pair ? (h.author === sel.pair.author && h.reader === sel.pair.reader) : (h.author === sel.role || h.reader === sel.role);
    });
    MC.handoffCards.render(detail, sel.pair ? sel.pair.reader + " read " + sel.pair.author + "'s work" : "everything " + sel.role + " gave or took", mine);
    draw(state);
  }

  function draw(state) {
    MC.clear(layers.nodes); rings = {};
    pos = map.place(state.roles);
    var bottom = Object.keys(pos).reduce(function (m, k) { return Math.max(m, pos[k].y); }, 0) + map.CARD_H / 2 + 44;
    svg.setAttribute("viewBox", "0 0 " + map.WIDTH + " " + Math.max(160, bottom));
    var on = selected && selected.pair ? selected.pair.author + ">" + selected.pair.reader : "";
    paths = map.drawEdges(layers.edges, flows(pairs(state.handoffs)), pos, { marker: "hfa", on: on || "none", pick: function (a, b) { select({ pair: { author: a, reader: b } }, state); } });
    state.roles.forEach(function (r) {
      rings[r.role] = MC.orchCards.card(layers.nodes, state, r, pos[r.role], !!selected && selected.role === r.role, function (role) { select({ role: role }, state); }, info(state, r));
    });
  }

  function floatLabel(role, text) {
    var p = pos[role]; if (!p) return;
    var t = el("text", { x: p.x, y: p.y - map.CARD_H / 2 - 6, "class": "float" }, text);
    layers.live.appendChild(t); setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 1700);
  }
  function pulse(role) { var ring = rings[role]; if (ring) { ring.classList.remove("pulse"); void ring.getBoundingClientRect(); ring.classList.add("pulse"); } }

  // A read happening now: a green square rides the arrow from the author to the reader.
  function travel(from, to, then) {
    var d = paths[from + ">" + to];
    if (!d || MC.reduced) { then(); return; }
    var path = el("path", { d: d, fill: "none" }), dot = el("rect", { width: "9", height: "9", fill: MC.css("--green") });
    layers.live.appendChild(dot);
    var len = path.getTotalLength(), start = performance.now();
    (function frame(now) {
      var t = Math.min(1, (now - start) / 1100), pt = path.getPointAtLength(len * t);
      dot.setAttribute("x", pt.x - 4.5); dot.setAttribute("y", pt.y - 4.5);
      if (t < 1) requestAnimationFrame(frame); else { dot.remove(); then(); }
    })(start);
  }

  function play(ev) {
    var r = MC.route(ev);
    if (ev.kind === "READ" && r && pos[r.from] && pos[r.to]) { floatLabel(r.from, "read"); travel(r.from, r.to, function () { pulse(r.to); floatLabel(r.to, "learned"); }); }
    else if (pos[ev.role]) { pulse(ev.role); floatLabel(ev.role, ev.kind.toLowerCase()); }
  }

  function counters(state) {
    MC.clear(stats);
    var carried = state.handoffs.reduce(function (n, h) { return n + h.decisions.length; }, 0);
    [[state.handoffs.length, "reads of another session's work"], [carried, "decisions that travelled"]].forEach(function (s) {
      var box = el("span"), n = el("b", {}, "0"); box.appendChild(n); box.appendChild(document.createTextNode(" " + s[1]));
      MC.countTo(n, s[0], "handoff:" + s[1]); stats.appendChild(box);
    });
  }

  function update(state, fresh) {
    (fresh || []).forEach(function (ev, i) { setTimeout(function () { play(ev); }, i * 350); });
    var sig = JSON.stringify([state.handoffs, state.roles.map(function (r) { return [r.role, r.requests, r.decisions, r.edits]; })]);
    if (sig === signature) return;
    signature = sig; counters(state);
    if (!state.roles.length) { MC.clear(layers.edges); MC.clear(layers.nodes); return; }
    var first = state.handoffs[0];
    var keep = selected && (selected.role || (selected.pair && state.handoffs.some(function (h) { return h.author === selected.pair.author && h.reader === selected.pair.reader; })));
    select(keep ? selected : (first ? { pair: { author: first.author, reader: first.reader } } : { role: state.roles[0].role }), state);
  }

  MC.views.handoff = { update: update, play: play, context: function () { return !selected ? "" : selected.pair ? selected.pair.reader + " reading " + selected.pair.author + "'s work is selected" : selected.role + " is selected"; } };
})();
