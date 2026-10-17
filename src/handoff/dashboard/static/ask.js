// The ask page: type a question, Claude answers from the graphs, and the Cypher it ran is shown
// so the answer can be checked. All text goes in with textContent (MC.rich only links names).
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var form = document.getElementById("ask-form"), input = document.getElementById("ask-input");
  var send = document.getElementById("ask-send"), log = document.getElementById("ask-log");
  var chips = document.getElementById("ask-chips");
  var STARTERS = [
    "What is each session working on right now?",
    "Which decisions were replaced, and by what?",
    "Which standing rules are in force?",
    "Who has read whose work?"
  ];

  function bubble(kind, who) {
    var box = el("div", { "class": "ask-turn ask-" + kind });
    box.appendChild(el("div", { "class": "ask-who" }, who));
    log.appendChild(box); box.scrollIntoView({ block: "nearest" });
    return box;
  }

  function showQueries(box, queries) {
    if (!queries.length) return;
    var d = el("details", { "class": "ask-cypher" });
    d.appendChild(el("summary", {}, "Cypher it ran (" + queries.length + ")"));
    queries.forEach(function (q) { d.appendChild(el("pre", {}, q)); });
    box.appendChild(d);
  }

  function ask(question) {
    bubble("q", "you").appendChild(el("p", {}, question));
    var pending = bubble("a", "claude");
    pending.appendChild(el("p", { "class": "dim" }, "asking Claude Code on your plan; usually under a minute…"));
    send.disabled = true; input.disabled = true;
    fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: question }) })
      .then(function (r) {
        // An older dashboard server answers a POST with an HTML error page, not JSON.
        return r.text().then(function (text) {
          var body; try { body = JSON.parse(text); } catch (e) { body = { error: "this dashboard server is older than the ask box: restart `handoff dashboard`" }; }
          return { ok: r.ok, body: body };
        });
      })
      .then(function (res) {
        pending.removeChild(pending.lastChild);
        if (!res.ok) { pending.appendChild(el("p", { "class": "ask-error" }, res.body.error || "no answer")); return; }
        pending.appendChild(MC.rich(el("p", { "class": "full" }), res.body.answer));
        showQueries(pending, res.body.queries);
      })
      .catch(function (e) { pending.removeChild(pending.lastChild); pending.appendChild(el("p", { "class": "ask-error" }, "could not ask: " + e.message)); })
      .then(function () { send.disabled = false; input.disabled = false; input.focus(); });
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var q = input.value.trim();
    if (!q) return;
    input.value = ""; ask(q);
  });
  STARTERS.forEach(function (s) {
    var b = el("button", { type: "button" }, s);
    b.addEventListener("click", function () { ask(s); });
    chips.appendChild(b);
  });

  MC.views.ask = { update: function () {} };
})();
