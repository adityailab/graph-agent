// Opening a memory: what is inside one kind (click a card) and which memories are relevant to
// what a session is doing. Text from the graph goes in with textContent only.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el, open = "";

  function fetchItems(path, then) {
    fetch(path, { cache: "no-store" }).then(function (r) { return r.json(); })
      .then(function (data) { then(data.items || []); })
      .catch(function () { then(null); });
  }

  function itemRow(item) {
    var li = el("li"), tag = el("span", { "class": "t-role" }, item.title);
    if (item.role) tag.style.color = MC.color(item.role);
    li.appendChild(tag); li.appendChild(document.createTextNode("  "));
    MC.rich(li, item.text);
    return li;
  }

  function fill(list, items, empty) {
    MC.clear(list);
    if (items === null) { list.appendChild(el("li", { "class": "dim" }, "could not load")); return; }
    if (!items.length) { list.appendChild(el("li", { "class": "dim" }, empty)); return; }
    items.forEach(function (item) { list.appendChild(itemRow(item)); });
  }

  // The panel under the cards: the open kind's items, newest first.
  function showKind(panel, kind) {
    MC.clear(panel);
    if (!kind) return;
    panel.appendChild(el("h3", {}, "inside " + kind + " memory"));
    var list = el("ul", { "class": "mem-items" });
    panel.appendChild(list);
    fetchItems("/api/memory/" + kind, function (items) { fill(list, items, "nothing here yet"); });
  }

  // A session's list of memories whose words match its current task.
  function relevantFor(role, box) {
    box.appendChild(el("h3", {}, "relevant memories"));
    var list = el("ul", { "class": "mem-items" });
    box.appendChild(list);
    fetchItems("/api/memory/relevant/" + encodeURIComponent(role), function (items) {
      fill(list, items, "nothing in the graph matches this task yet");
    });
  }

  MC.memoryDetail = {
    toggle: function (kind) { open = open === kind ? "" : kind; return open; },
    current: function () { return open; },
    showKind: showKind,
    relevantFor: relevantFor
  };
})();
