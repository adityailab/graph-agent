// The graph's toolbar: which graph, how to group it, which kinds of node to show, and the view controls.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el, M = MC.graphModel;
  var GLYPH = { Decision: "◆ decisions", Need: "■ needs", Message: "● messages", Request: "● requests", File: "▪ files" };
  var MODES = [["work", "work graph"], ["concepts", "concept graph"]];

  function button(text, pressed, id) {
    var b = el("button", { type: "button", "aria-pressed": String(pressed) }, text);
    if (id) b.id = id;
    return b;
  }
  function group(label, cls) {
    var g = el("span", { "class": "grp " + (cls || ""), role: "group", "aria-label": label });
    if (cls === "seg" && label !== "Graph") g.appendChild(el("span", { "class": "lbl" }, label.toLowerCase()));
    return g;
  }

  // `s` is the view's state, `on` its handlers. Built again whenever a count or a choice changes.
  function render(box, s, counts, on) {
    MC.clear(box);
    var modes = group("Graph", "seg");
    MODES.forEach(function (m) { var b = button(m[1], s.mode === m[0]); b.setAttribute("data-mode", m[0]); b.addEventListener("click", function () { on.mode(m[0]); }); modes.appendChild(b); });
    var mem = button("memory · " + (s.memoryKind || ""), s.mode === "memory", "graph-memory");
    mem.setAttribute("data-mode", "memory"); mem.hidden = !s.memoryKind; mem.addEventListener("click", function () { on.mode("memory"); }); modes.appendChild(mem);
    box.appendChild(modes);
    if (s.mode === "work") {
      var show = group("Show"); show.appendChild(el("span", { "class": "lbl" }, "show"));
      M.TOGGLES.forEach(function (k) {
        var b = button(GLYPH[k] + " ", s.kinds[k]); b.className = "toggle"; b.appendChild(el("i", {}, String(counts[k] || 0)));
        b.addEventListener("click", function () { on.toggle(k); }); show.appendChild(b);
      });
      box.appendChild(show);
    }
    var right = el("span", { "class": "right" }), fit = button("fit", false, "graph-fit"), pin = button("pin on drag: " + (s.pinning ? "on" : "off"), s.pinning, "graph-pin"), un = button("unpin all", false, "graph-unpin");
    fit.addEventListener("click", on.fit); pin.addEventListener("click", on.pin); un.addEventListener("click", on.unpin);
    [fit, pin, un].forEach(function (b) { b.removeAttribute("aria-pressed"); right.appendChild(b); });
    pin.setAttribute("aria-pressed", String(!!s.pinning));
    box.appendChild(right);
  }

  window.MC.graphBar = { render: render };
})();
