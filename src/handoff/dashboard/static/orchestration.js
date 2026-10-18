// The orchestration view: sessions as cards, what moves between them as labelled arrows, and a
// square that travels along an arrow each time an event happens now.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el, map = MC.orchMap;
  var svg = document.getElementById("orch"), detailBox = document.getElementById("orch-detail");
  var layers = { edges: el("g"), live: el("g"), nodes: el("g") };
  svg.appendChild(layers.edges); svg.appendChild(layers.live); svg.appendChild(layers.nodes);
  var KIND_VAR = { MESSAGE: "--teal", NUDGE: "--teal", DIGEST: "--teal", QUESTION: "--purple", STANDIN_ANSWER: "--purple", NEEDS: "--red", READ: "--amber", DECIDED: "--green", edited: "--blue", asked: "--ink" };
  var pos = {}, paths = {}, rings = {}, signature = "", current = null, chosen = null;

  function fitHeight() {
    var bottom = Object.keys(pos).reduce(function (m, k) { return Math.max(m, pos[k].y); }, 0) + map.CARD_H / 2 + 24;
    svg.setAttribute("viewBox", "0 0 " + map.WIDTH + " " + Math.max(200, bottom));
  }

  function pick(role) { chosen = role; render(); }

  function render() {
    MC.clear(layers.nodes); MC.clear(detailBox); rings = {};
    if (!current.roles.length) { layers.nodes.appendChild(el("text", { x: map.WIDTH / 2, y: 100, "class": "empty" }, "waiting for the first session…")); return; }
    current.roles.forEach(function (r) { rings[r.role] = MC.orchCards.card(layers.nodes, current, r, pos[r.role], r.role === chosen, pick); });
    MC.orchDetail.show(detailBox, current, chosen, pick);
  }

  function floatLabel(role, text) {
    var p = pos[role]; if (!p) return;
    var t = el("text", { x: p.x, y: p.y - map.CARD_H / 2 - 6, "class": "float" }, text);
    layers.live.appendChild(t);
    setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 1700);
  }

  function pulse(role) {
    var ring = rings[role]; if (!ring) return;
    ring.classList.remove("pulse"); void ring.getBoundingClientRect(); ring.classList.add("pulse");
  }

  function travel(from, to, colour, then) {
    var d = paths[from + ">" + to] || map.curve(pos[from], pos[to], 0, 0).d;
    if (MC.reduced) { then(); return; }
    var path = el("path", { d: d, fill: "none" }), dot = el("rect", { width: "9", height: "9", fill: colour });
    layers.live.appendChild(dot);
    var len = path.getTotalLength(), start = performance.now(), ms = 1100;
    (function frame(now) {
      var t = Math.min(1, (now - start) / ms), pt = path.getPointAtLength(len * t);
      dot.setAttribute("x", pt.x - 4.5); dot.setAttribute("y", pt.y - 4.5);
      if (t < 1) requestAnimationFrame(frame); else { dot.remove(); then(); }
    })(start);
  }

  // One event happening now: a square travels between roles, or the role itself pulses.
  function play(ev) {
    var r = MC.route(ev);
    if (r && pos[r.from] && pos[r.to]) {
      floatLabel(r.from, ev.kind);
      travel(r.from, r.to, MC.css(KIND_VAR[ev.kind] || "--dim"), function () { pulse(r.to); floatLabel(r.to, ev.kind); });
    } else { pulse(ev.role); floatLabel(ev.role, ev.kind); }
  }

  function update(state, fresh) {
    current = state;
    var sig = JSON.stringify([state.roles.map(function (r) { return [r.role, r.requests, r.decisions, r.edits, r.open_needs]; }), state.flows, Math.floor(state.now / 30000), state.events.map(function (e) { return e.key; }).slice(-60)]);
    if (sig !== signature) {
      signature = sig;
      if (!chosen || !state.roles.some(function (r) { return r.role === chosen; })) chosen = state.roles.length ? state.roles[0].role : null;
      pos = map.place(state.roles); fitHeight(); paths = map.drawEdges(layers.edges, state.flows, pos); render();
      MC.orchDetail.status(document.getElementById("orch-status"), state);
      MC.orchDetail.table(document.getElementById("flows"), document.getElementById("lines-summary"), state.flows);
    }
    fresh.forEach(function (ev, i) { setTimeout(function () { play(ev); }, i * 350); });
  }

  MC.views.orchestration = { update: update, play: play, context: function () { return chosen ? "the " + chosen + " session is open" : ""; } };
})();
