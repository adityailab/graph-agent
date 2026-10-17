// The detail beside the handoff workflow: for the chosen arrow or session, one card per hand-off
// (who read whose work, how many decisions travelled), the full text one click away.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;

  function chip(role) {
    var c = el("span", { "class": "chip" }, role); c.style.setProperty("--c", MC.color(role)); return c;
  }

  function card(h, open) {
    var c = el("details", { "class": "card hcard" }), head = el("summary");
    if (open) c.open = true;
    head.appendChild(chip(h.reader)); head.appendChild(el("span", { "class": "arrow" }, " ← "));
    head.appendChild(chip(h.author));
    head.appendChild(el("span", { "class": "when" }, MC.clock(h.at)));
    head.appendChild(el("span", { "class": "nb" }, h.decisions.length + (h.decisions.length === 1 ? " decision" : " decisions")));
    head.appendChild(el("span", { "class": "peek" }, h.request.length > 90 ? h.request.slice(0, 89) + "…" : h.request));
    c.appendChild(head);
    c.appendChild(MC.clamp(MC.rich(el("p", { "class": "full asked" }), "their request: " + h.request)));
    if (!h.decisions.length) { c.appendChild(el("p", { "class": "none" }, "no decision was recorded for that work.")); return c; }
    var list = el("ul");
    h.decisions.forEach(function (d) {
      var li = MC.rich(el("li"), d.text);
      var why = el("details", { "class": "fold why-fold" });
      why.appendChild(el("summary", {}, "why")); why.appendChild(MC.rich(el("p", { "class": "why" }), d.reason)); li.appendChild(why);
      list.appendChild(li);
    });
    c.appendChild(list);
    return c;
  }

  // `title` says what is selected; `list` are its hand-offs, newest first.
  function render(box, title, list) {
    MC.clear(box);
    var sel = el("div", { "class": "sel" }), n = list.reduce(function (t, h) { return t + h.decisions.length; }, 0);
    sel.appendChild(el("h3", {}, title)); sel.appendChild(el("span", { "class": "dim" }, list.length + " reads · " + n + " decisions")); box.appendChild(sel);
    if (!list.length) { box.appendChild(el("p", { "class": "dim" }, "no session has read another's work here yet")); return; }
    list.forEach(function (h, i) { box.appendChild(card(h, i === 0)); });
  }

  MC.handoffCards = { render: render };
})();
