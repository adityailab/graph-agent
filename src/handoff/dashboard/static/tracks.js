// The tracks view: how handoff answers each competition track, with live numbers as evidence.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var root = document.getElementById("tracks"), signature = "";

  function track(t) {
    var box = el("div", { "class": "track" });
    box.appendChild(el("h3", {}, t.title));
    box.appendChild(el("p", { "class": "asks" }, t.asks));
    var how = el("ul");
    t.how.forEach(function (line) { how.appendChild(el("li", {}, line)); });
    box.appendChild(how);
    var grid = el("div", { "class": "evidence" });
    t.evidence.forEach(function (e) {
      var cell = el("div"), n = el("b", {}, "0");
      cell.appendChild(n); cell.appendChild(el("span", {}, e.label));
      MC.countTo(n, e.value, t.id + ":" + e.label); grid.appendChild(cell);
    });
    box.appendChild(grid);
    return box;
  }

  function update(state) {
    var sig = JSON.stringify(state.tracks);
    if (sig === signature) return;
    signature = sig; MC.clear(root);
    state.tracks.forEach(function (t) { root.appendChild(track(t)); });
  }

  MC.views.tracks = { update: update };
})();
