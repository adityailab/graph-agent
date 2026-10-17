// The selected node as a card, and each of its connections as a card of its own with a "connect"
// button that jumps the graph to that node, so the graph can be walked one link at a time.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var box = document.getElementById("detail"), nodes = {}, edges = [], shown = null, SHOWN = 5, showAll = false;

  function chip(n) {
    var c = el("span", { "class": "chip" }, n.kind.toLowerCase() + (n.role ? " · " + n.role : ""));
    if (n.role) c.style.setProperty("--c", MC.color(n.role));
    return c;
  }

  function when(n) { return n.at ? el("span", { "class": "when" }, MC.clock(n.at)) : null; }

  // A neighbour: how it is linked, who it belongs to, its text (three lines; click for all) and a connect button.
  function connection(label, other) {
    var card = el("div", { "class": "link-card" }), head = el("div", { "class": "link-head" });
    head.appendChild(el("span", { "class": "rel" }, label)); head.appendChild(chip(other));
    var w = when(other); if (w) head.appendChild(w);
    var go = el("button", { type: "button", "class": "connect" }, "connect →");
    go.addEventListener("click", function () { MC.views.graph.select(other.id); });
    head.appendChild(go); card.appendChild(head);
    card.appendChild(MC.clamp(MC.rich(el("p", { "class": "full" }), other.text)));
    return card;
  }

  function show(n) {
    shown = n.id; MC.clear(box); box.hidden = false;
    var head = el("div", { "class": "node-card" }), top = el("div", { "class": "link-head" });
    top.appendChild(chip(n)); var w = when(n); if (w) top.appendChild(w);
    head.appendChild(top); head.appendChild(MC.rich(el("p", { "class": "full" }), n.text));
    box.appendChild(head);
    var links = [];
    edges.forEach(function (e) {
      if (e.source === n.id && nodes[e.target]) links.push(["──" + e.kind.toLowerCase().replace("_", " ") + "──▶", nodes[e.target]]);
      if (e.target === n.id && nodes[e.source]) links.push(["◀──" + e.kind.toLowerCase().replace("_", " ") + "──", nodes[e.source]]);
    });
    box.appendChild(el("h3", {}, "connections (" + links.length + ")"));
    if (!links.length) box.appendChild(el("p", { "class": "dim" }, "no relationships in this view"));
    links.slice(0, showAll ? links.length : SHOWN).forEach(function (l) { box.appendChild(connection(l[0], l[1])); });
    if (links.length > SHOWN && !showAll) {
      var more = el("button", { type: "button", "class": "more" }, "show all " + links.length);
      more.addEventListener("click", function () { showAll = true; show(n); });
      box.appendChild(more);
    }
  }

  function clear() { shown = null; showAll = false; MC.clear(box); box.hidden = true; }

  // New data arrives every few seconds: keep the panel in step with it.
  function refresh(newNodes, newEdges) {
    nodes = newNodes; edges = newEdges;
    if (shown && nodes[shown]) show(nodes[shown]); else if (shown) clear();
  }

  MC.graphDetail = { show: show, clear: clear, refresh: refresh };
})();
