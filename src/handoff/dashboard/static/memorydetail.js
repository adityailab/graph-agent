// Opening a memory: a kind of memory drawn as a graph (click a card) and which memories are
// relevant to what a session is doing. Text from the graph goes in with textContent only.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;

  function fetchItems(path, then) {
    fetch(path, { cache: "no-store" }).then(function (r) { return r.json(); })
      .then(function (data) { then(data.items || []); })
      .catch(function () { then(null); });
  }

  // One memory as a small card: a header (kind, who, when) and the text in three lines, click for all.
  function itemRow(item) {
    var li = el("li", { "class": "item-card" }), head = el("div", { "class": "link-head" });
    var tag = el("span", { "class": "chip" }, item.title);
    if (item.role) tag.style.setProperty("--c", MC.color(item.role));
    head.appendChild(tag);
    if (item.at) head.appendChild(el("span", { "class": "when" }, MC.clock(item.at)));
    li.appendChild(head); li.appendChild(MC.clamp(MC.rich(el("p", { "class": "full" }), item.text)));
    return li;
  }

  function fill(list, items, empty) {
    MC.clear(list);
    if (items === null) { list.appendChild(el("li", { "class": "dim" }, "could not load")); return; }
    if (!items.length) { list.appendChild(el("li", { "class": "dim" }, empty)); return; }
    items.forEach(function (item) { list.appendChild(itemRow(item)); });
  }

  // Opening a card draws that kind of memory as a graph on the graph page.
  function openGraph(kind) {
    fetch("/api/memory/" + kind + "/graph", { cache: "no-store" }).then(function (r) { return r.json(); })
      .then(function (view) { MC.views.graph.showMemory(kind, view); MC.setView("graph"); })
      .catch(function () { /* the card stays as it is; the next poll tries again on click */ });
  }

  // Every item of one kind with its whole text, beside the graph so nothing has to be hovered.
  function listKind(kind, box) {
    MC.clear(box); box.hidden = false;
    box.appendChild(el("h3", {}, "everything in " + kind + " memory"));
    var list = el("ul", { "class": "mem-full" });
    box.appendChild(list);
    fetchItems("/api/memory/" + kind, function (items) { fill(list, items, "nothing here yet"); });
  }

  // A session's list of memories whose words match its current task.
  function relevantFor(role, box) {
    var fold = el("details", { "class": "fold" }), list = el("ul", { "class": "mem-items" });
    fold.appendChild(el("summary", {}, "relevant memories (decisions that match this task)"));
    fold.appendChild(list); box.appendChild(fold);
    fetchItems("/api/memory/relevant/" + encodeURIComponent(role), function (items) {
      fill(list, items, "nothing in the graph matches this task yet");
    });
  }

  MC.memoryDetail = { openGraph: openGraph, listKind: listKind, relevantFor: relevantFor };
})();
