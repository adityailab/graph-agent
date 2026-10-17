// The selected node, in full: its whole text and every relationship it has, readable without hover.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var box = document.getElementById("detail"), nodes = {}, edges = [], shown = null;

  function line(label, other) {
    var li = el("li");
    li.appendChild(el("span", { "class": "rel" }, label));
    li.appendChild(el("span", { "class": "kind" }, " " + other.kind + (other.role ? " (" + other.role + ")" : "") + ": "));
    li.appendChild(MC.rich(el("span"), other.text));
    return li;
  }

  function show(n) {
    shown = n.id; MC.clear(box); box.hidden = false;
    var head = el("h3", {}, n.kind + (n.role ? " · " + n.role : "") + (n.at ? " · " + MC.clock(n.at) : ""));
    box.appendChild(head);
    box.appendChild(MC.rich(el("p", { "class": "full" }), n.text));
    var list = el("ul");
    edges.forEach(function (e) {
      if (e.source === n.id && nodes[e.target]) list.appendChild(line("──" + e.kind.toLowerCase() + "──▶", nodes[e.target]));
      if (e.target === n.id && nodes[e.source]) list.appendChild(line("◀──" + e.kind.toLowerCase() + "──", nodes[e.source]));
    });
    box.appendChild(list.children.length ? list : el("p", { "class": "dim" }, "no relationships in this view"));
  }

  function clear() { shown = null; MC.clear(box); box.hidden = true; }

  // New data arrives every few seconds: keep the panel in step with it.
  function refresh(newNodes, newEdges) {
    nodes = newNodes; edges = newEdges;
    if (shown && nodes[shown]) show(nodes[shown]); else if (shown) clear();
  }

  MC.graphDetail = { show: show, clear: clear, refresh: refresh };
})();
