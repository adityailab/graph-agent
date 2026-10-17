// The memory view: the six kinds of memory the graph holds, then what each session holds right now
// and how context moves between sessions. All text from the graph goes in with textContent.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var root = document.getElementById("memory"), signature = "";
  // One session's card: what it is on (three lines, click for all), its counts, then what it learned
  // and what is relevant to it, each folded until asked for.
  function context(c) {
    var box = el("article", { "class": "ctx" }), bar = el("div", { "class": "ctx-bar" }), colour = MC.color(c.role);
    box.style.setProperty("--c", colour);
    var svg = el("svg", { viewBox: "0 0 44 36", width: "26", height: "22", "aria-hidden": "true" }); svg.appendChild(MC.critter.draw(-2, -1, colour, false));
    bar.appendChild(svg); bar.appendChild(el("b", {}, c.role)); bar.appendChild(el("span", { "class": "inbox" }, "inbox " + c.inbox)); box.appendChild(bar);
    var body = el("div", { "class": "ctx-body" });
    body.appendChild(el("h3", {}, "working on")); body.appendChild(MC.clamp(MC.rich(el("p", { "class": "full" }), c.working_on)));
    var facts = el("div", { "class": "facts" });
    [[c.inbox, "delivered", ""], [c.open_needs, "open needs", c.open_needs ? "need" : ""], [c.rules, "rules", ""]].forEach(function (f) {
      var s = el("span", { "class": f[2] }); s.appendChild(el("b", {}, String(f[0]))); s.appendChild(document.createTextNode(" " + f[1])); facts.appendChild(s);
    });
    body.appendChild(facts);
    var fold = el("details", { "class": "fold" });
    fold.appendChild(el("summary", {}, "learned from other sessions (" + c.learned.length + ")"));
    var list = el("ul", { "class": "plain" });
    if (!c.learned.length) list.appendChild(el("li", { "class": "dim" }, "nothing yet: no decision has travelled to this role"));
    c.learned.slice(0, 8).forEach(function (pair) {
      var li = el("li"), who = el("span", { "class": "t-role" }, pair[0]); who.style.color = MC.color(pair[0]);
      li.appendChild(who); li.appendChild(document.createTextNode(": ")); MC.rich(li, pair[1]); list.appendChild(li);
    });
    if (c.learned.length > 8) list.appendChild(el("li", { "class": "dim" }, "… and " + (c.learned.length - 8) + " more"));
    fold.appendChild(list); body.appendChild(fold);
    MC.memoryDetail.relevantFor(c.role, body);
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
    var head = el("div", { "class": "page-head" }); head.appendChild(el("h2", {}, "memory"));
    head.appendChild(el("span", { "class": "dim" }, "six kinds, and how they feed each other · click a kind to see it as a graph")); root.appendChild(head);
    MC.memKinds.draw(root, memory.types);
    root.appendChild(el("p", { "class": "mem-key" }, "read left to right: events are distilled into decisions, decisions harden into rules, and rules plus the decisions that match a task are loaded into each live session. Temporal orders everything; social spreads decisions between sessions."));
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
