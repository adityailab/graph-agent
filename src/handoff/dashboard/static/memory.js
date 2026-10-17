// The memory view: the six kinds of memory the graph holds, then what each session holds right now
// and how context moves between sessions. All text from the graph goes in with textContent.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var root = document.getElementById("memory"), signature = "";
  var COLOUR = { working: "--blue", episodic: "--teal", semantic: "--purple", procedural: "--amber", temporal: "--red", social: "--green" };

  function kindCard(t) {
    var card = el("div", { "class": "mem-card" }), n = el("b", {}, "0");
    card.style.borderTopColor = MC.css(COLOUR[t.key] || "--dim");
    n.style.color = MC.css(COLOUR[t.key] || "--ink");
    var head = el("div", { "class": "mem-head" }); head.appendChild(el("span", { "class": "mem-name" }, t.name)); head.appendChild(n);
    card.appendChild(head); card.appendChild(el("p", { "class": "mem-what" }, t.what)); card.appendChild(el("p", { "class": "dim" }, t.detail));
    MC.countTo(n, t.count, "memory:" + t.key);
    card.setAttribute("role", "button"); card.tabIndex = 0;
    var choose = function () { MC.memoryDetail.openGraph(t.key); };
    card.addEventListener("click", choose);
    card.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choose(); } });
    return card;
  }

  // One session's card: what it is on (three lines, click for all), then what it learned and what
  // is relevant, each folded until asked for.
  function context(c) {
    var box = el("div", { "class": "ctx" }), bar = el("div", { "class": "ctx-bar" }, c.role);
    bar.style.background = MC.color(c.role); box.appendChild(bar);
    var body = el("div", { "class": "ctx-body" });
    body.appendChild(el("h3", {}, "working on")); body.appendChild(MC.clamp(MC.rich(el("p", { "class": "full" }), c.working_on)));
    var fold = el("details", { "class": "fold" });
    fold.appendChild(el("summary", {}, "learned from other sessions (" + c.learned.length + ")"));
    if (!c.learned.length) fold.appendChild(el("p", { "class": "dim" }, "nothing yet: no decision has travelled to this role"));
    var list = el("ul");
    c.learned.slice(0, 8).forEach(function (pair) {
      var li = el("li"), who = el("span", { "class": "t-role" }, pair[0]); who.style.color = MC.color(pair[0]);
      li.appendChild(who); li.appendChild(document.createTextNode(": ")); MC.rich(li, pair[1]); list.appendChild(li);
    });
    if (c.learned.length > 8) list.appendChild(el("li", { "class": "dim" }, "… and " + (c.learned.length - 8) + " more"));
    fold.appendChild(list); body.appendChild(fold);
    MC.memoryDetail.relevantFor(c.role, body);
    body.appendChild(el("p", { "class": "dim facts" }, "inbox " + c.inbox + " delivered · open needs " + c.open_needs + " · rules in force " + c.rules));
    box.appendChild(body);
    return box;
  }

  function flows(state) {
    var box = el("div", { "class": "ctx-flows" }), pairs = Object.create(null);
    state.flows.forEach(function (f) {
      var key = f.source + " → " + f.target; (pairs[key] = pairs[key] || []).push(f);
    });
    Object.keys(pairs).forEach(function (key) {
      var row = el("div", {}, key + "  ");
      pairs[key].forEach(function (f) { row.appendChild(el("b", { "class": "k-" + f.kind }, f.kind + " ×" + f.count + " ")); });
      box.appendChild(row);
    });
    return box;
  }

  function update(state) {
    var memory = state.memory || { types: [], contexts: [] };  // an older server sends no memory
    var sig = JSON.stringify([memory, state.flows]);
    if (sig === signature) return;
    signature = sig; MC.clear(root);
    if (!memory.types.length) { root.appendChild(el("p", { "class": "dim" }, "no memory yet: start a session in this folder (if sessions exist, restart `handoff dashboard`: this server may be older than the memory page)")); return; }
    root.appendChild(el("h3", {}, "six kinds of memory the graph holds · click one to see it as a graph"));
    var grid = el("div", { "class": "mem-grid" });
    memory.types.forEach(function (t) { grid.appendChild(kindCard(t)); });
    root.appendChild(grid);
    root.appendChild(el("h3", {}, "what each session holds right now"));
    var ctxs = el("div", { "class": "ctx-grid" });
    memory.contexts.forEach(function (c) { ctxs.appendChild(context(c)); });
    root.appendChild(ctxs);
    var moves = el("details", { "class": "fold" });
    moves.appendChild(el("summary", {}, "how context moves between sessions (" + state.flows.length + " lines)"));
    moves.appendChild(flows(state)); root.appendChild(moves);
  }

  MC.views.memory = { update: update };
})();
