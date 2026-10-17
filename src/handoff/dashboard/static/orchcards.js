// The session cards of the orchestration drawing: name band, Mac, what it did last, its counts.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el, W = MC.orchMap.CARD_W, H = MC.orchMap.CARD_H;

  function lastEvent(role, events) {
    for (var i = events.length - 1; i >= 0; i--) if (events[i].role === role) return events[i];
    return null;
  }

  function body(g, x, y, r, last, active, colour) {
    var mac = el("g", { transform: "translate(" + (x + 4) + "," + (y + 19) + ")" });
    mac.appendChild(MC.critter.draw(0, 0, colour, active)); g.appendChild(mac);
    var kind = last ? last.kind.toLowerCase() : "", text = MC.wrap(last ? last.text : "", 19, 1)[0] || "";
    var head = el("text", { x: x + 50, y: y + 35, "class": "card-line" });
    head.appendChild(el("tspan", { "class": "k-" + kind }, kind)); g.appendChild(head);
    g.appendChild(el("text", { x: x + 50, y: y + 47, "class": "card-line" }, text));
    g.appendChild(el("text", { x: x + 8, y: y + 67, "class": "card-line dim" }, r.requests + " asks · " + r.decisions + " decisions · " + r.edits + " edits"));
  }

  // One card. `pick` is called with the role on a click or Enter; returns the ring to pulse.
  function card(layer, state, r, p, chosen, pick) {
    var x = p.x - W / 2, y = p.y - H / 2, colour = MC.color(r.role), active = state.now - r.last_seen_at <= 120000;
    var g = el("g", { "class": "orch-node" + (chosen ? " on" : ""), role: "button", tabindex: "0", "aria-label": r.role + " session, open details", "aria-pressed": String(chosen) });
    var ring = el("rect", { x: x, y: y, width: W, height: H, rx: 6, "class": "node-ring", stroke: colour });
    g.appendChild(ring);
    g.appendChild(el("rect", { x: x, y: y, width: W, height: H, rx: 6, "class": "card-box" }));
    g.appendChild(el("rect", { x: x, y: y, width: W, height: 19, rx: 6, fill: colour }));
    g.appendChild(el("rect", { x: x, y: y + 12, width: W, height: 7, fill: colour }));
    g.appendChild(el("text", { x: x + 8, y: y + 13, "class": "card-title" }, (chosen ? "▾ " : "") + r.role));
    var tag = (r.open_needs > 0 ? r.open_needs + " open need" + (r.open_needs > 1 ? "s" : "") + " · " : "") + (active ? "active" : "idle");
    g.appendChild(el("text", { x: x + W - 8, y: y + 13, "class": "card-state" }, tag));
    body(g, x, y, r, lastEvent(r.role, state.events), active, colour);
    g.addEventListener("click", function () { pick(r.role); });
    g.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); pick(r.role); } });
    layer.appendChild(g);
    return ring;
  }

  window.MC.orchCards = { card: card };
})();
