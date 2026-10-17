// The command field fixed at the bottom of every page: the one place a person writes into the graph.
(function () {
  "use strict";
  var MC = window.MC;
  var form = document.getElementById("dock"), input = document.getElementById("dock-input");
  var chat = document.getElementById("dock-chat"), chatLog = document.getElementById("dock-chat-log");
  document.getElementById("dock-chat-close").addEventListener("click", function () { chat.hidden = true; });
  var reply = document.getElementById("dock-reply"), roles = [], past = [], at = 0, hideTimer = null;

  function say(text, bad) {
    reply.textContent = text; reply.hidden = !text; reply.classList.toggle("bad", !!bad);
    clearTimeout(hideTimer);
    if (text) hideTimer = setTimeout(function () { reply.hidden = true; }, 7000);
  }

  function post(command) {
    return fetch("/api/command", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind: command.kind, to: command.to, text: command.text }) })
      .then(function (r) { return r.text().then(function (t) {
        var body; try { body = JSON.parse(t); } catch (e) { body = {}; }
        if (!r.ok) throw new Error(body.error || "this dashboard server is older than this page: restart `handoff dashboard`");
        return body.reply;
      }); });
  }

  // On the Ask page the answer goes into its chat. Anywhere else it opens here, over the page being
  // looked at, and the model is told what that page is showing.
  function answer(text) {
    if (MC.view() === "ask") return say(MC.ask.start(text) ? "" : "still answering the last question", true);
    chat.hidden = false;
    if (!MC.ask.start(text, chatLog, MC.pageContext())) { say("still answering the last question", true); return; }
    say("");
  }

  function run(command) {
    if (command.kind === "error") return say(command.message, true);
    if (command.kind === "go") { MC.setView(command.page); return say(""); }
    if (command.kind === "ask") return answer(command.text);
    post(command).then(function (text) { say(text); })
      .catch(function (e) { say(e.message, true); });
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var text = input.value.trim();
    if (!text) return;
    var command = MC.parseCommand(text, roles);
    if (command && command.kind !== "error") { past.push(text); at = past.length; input.value = ""; }
    run(command);
  });
  // Up and down walk through what was typed before, like a shell.
  input.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") { if (!chat.hidden && !input.value) chat.hidden = true; input.blur(); return; }
    if ((ev.key !== "ArrowUp" && ev.key !== "ArrowDown") || !past.length) return;
    ev.preventDefault();
    at = Math.max(0, Math.min(past.length, at + (ev.key === "ArrowUp" ? -1 : 1)));
    input.value = past[at] || "";
  });
  // "/" jumps to the field from anywhere, as in a terminal's search.
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "/" && !/^(INPUT|TEXTAREA)$/.test(ev.target.tagName) && !ev.metaKey && !ev.ctrlKey && !ev.altKey) {
      ev.preventDefault(); input.focus();
    }
  });

  MC.views.dock = { update: function (s) { roles = s.roles.map(function (r) { return r.role; }); } };
})();
