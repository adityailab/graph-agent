// The tracks view: how handoff answers each competition track, with live numbers as evidence.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var root = document.getElementById("tracks"), signature = "";

  function macs(roles) {
    var box = el("span", { "class": "macs", "aria-hidden": "true" });
    roles.forEach(function (r) {
      var svg = el("svg", { viewBox: "0 0 44 36", width: "30", height: "25" });
      svg.appendChild(MC.critter.draw(-2, -1, MC.color(r), false)); box.appendChild(svg);
    });
    return box;
  }

  function track(t, roles, n) {
    var box = el("article", { "class": "mod" }), head = el("div", { "class": "mod-head" });
    head.appendChild(el("span", { "class": "mod-tag" }, "track " + n));
    head.appendChild(el("h3", {}, t.title)); head.appendChild(macs(roles));
    box.appendChild(head); box.appendChild(el("p", { "class": "ask" }, t.asks));
    var chain = el("ol", { "class": "chain" });
    t.how.forEach(function (line, i) {
      var li = el("li"); li.appendChild(el("span", { "class": "nd" }, String(i + 1)));
      li.appendChild(el("span", {}, line)); chain.appendChild(li);
    });
    box.appendChild(chain);
    var grid = el("div", { "class": "ev" });
    t.evidence.forEach(function (e) {
      var cell = el("div", /open/.test(e.label) && e.value > 0 ? { "class": "warn" } : {}), v = el("b", {}, "0");
      cell.appendChild(v); cell.appendChild(el("span", {}, e.label));
      MC.countTo(v, e.value, t.id + ":" + e.label); grid.appendChild(cell);
    });
    box.appendChild(grid);
    return box;
  }

  function update(state) {
    var sig = JSON.stringify(state.tracks);
    if (sig === signature) return;
    signature = sig; MC.clear(root);
    var roles = state.roles.map(function (r) { return r.role; });
    state.tracks.forEach(function (t, i) { root.appendChild(track(t, roles, i + 1)); });
  }

  MC.views.tracks = { update: update };
})();
