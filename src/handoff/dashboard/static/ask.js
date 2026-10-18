// The ask page: a chat with the graphs. Claude Code writes read-only Cypher, and the page shows
// what it is doing as it happens (steps, notes, the answer being written), then the answer and
// the Cypher so it can be checked. Earlier turns are sent along, so follow-ups keep their subject.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var askLog = document.getElementById("ask-log"), log = askLog, working = false;  // `log` is where the current question is drawn
  var empty = document.getElementById("ask-empty"), chips = document.getElementById("ask-chips");
  var STARTERS = [
    "What is each session working on right now?",
    "Which decisions were replaced, and by what?",
    "Which standing rules are in force?",
    "Who has read whose work?"
  ];
  var history = [];  // earlier {q, a} turns
  var KEEP = "handoff.chat", MAX_TURNS = 40, saved = [];  // saved: {q, a, queries, page}; survives reloads

  // Browser storage can be missing or refuse writes (private windows): the chat then just lasts the visit.
  function load() { try { var v = JSON.parse(localStorage.getItem(KEEP) || "[]"); return Array.isArray(v) ? v : []; } catch (e) { return []; } }
  function store() { try { localStorage.setItem(KEEP, JSON.stringify(saved.slice(-MAX_TURNS))); } catch (e) { /* not kept */ } }

  function toBottom() { log.scrollTop = log.scrollHeight; }

  function avatar(working) {
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 44 32"); svg.setAttribute("class", "ask-bot"); svg.setAttribute("aria-hidden", "true");
    svg.appendChild(MC.critter.draw(0, 0, MC.css("--green"), working));
    return svg;
  }

  function userTurn(text) {
    var row = el("div", { "class": "ask-row me" });
    row.appendChild(el("div", { "class": "ask-me" }, text));
    log.appendChild(row); toBottom();
  }

  // The finished answer: its words, the Cypher it ran, and a copy button. Used live and when mirrored.
  function finish(body, answer, queries) {
    var text = el("div", { "class": "ask-answer" }); MC.markdown(text, answer); body.appendChild(text);
    if (queries.length) {
      var d = el("details", { "class": "ask-cypher" });
      d.appendChild(el("summary", {}, "Cypher it ran (" + queries.length + ")"));
      queries.forEach(function (q) { d.appendChild(el("pre", {}, q)); });
      body.appendChild(d);
    }
    var copy = el("button", { type: "button", "class": "ask-copy" }, "copy answer");
    copy.addEventListener("click", function () {
      var ok = function () { copy.textContent = "copied"; setTimeout(function () { copy.textContent = "copy answer"; }, 1200); };
      if (navigator.clipboard) navigator.clipboard.writeText(answer).then(ok, function () {});
    });
    body.appendChild(copy);
  }

  // One conversation, two places: a question asked in the panel is also written into the Ask page,
  // and one asked on the Ask page is also written into the panel, so each shows the whole thread.
  function mirror(question, answer, queries, page, into) {
    var me = el("div", { "class": "ask-row me" }), bubble = el("div", { "class": "ask-me" }, question);
    if ((into === askLog) !== (page === "ask")) bubble.appendChild(el("span", { "class": "from-page" }, "asked on the " + page + " page"));
    me.appendChild(bubble); into.appendChild(me);
    var row = el("div", { "class": "ask-row bot" }), body = el("div", { "class": "ask-body" });
    row.appendChild(avatar(false)); row.appendChild(body); finish(body, answer, queries); into.appendChild(row);
    into.scrollTop = into.scrollHeight;
  }

  // One assistant turn: avatar, live steps, a notes line for the words as they arrive, the answer.
  function claudeTurn() {
    var row = el("div", { "class": "ask-row bot" }), body = el("div", { "class": "ask-body" });
    var bot = avatar(true), steps = el("ol", { "class": "ask-steps" }), live = el("p", { "class": "ask-live" });
    var clock = el("span", { "class": "ask-clock" }, "0s"), current = null, started = Date.now();
    row.appendChild(bot); row.appendChild(body); body.appendChild(steps); body.appendChild(live); body.appendChild(clock);
    log.appendChild(row); toBottom();
    var timer = setInterval(function () { clock.textContent = Math.round((Date.now() - started) / 1000) + "s"; }, 1000);

    function tick() { if (current) { current.classList.remove("now"); current.firstChild.textContent = "✓ "; } }
    function settle() {  // words written before a tool call were Claude's notes to itself: keep them as a step
      if (!live.textContent.trim()) return;
      var note = el("li", { "class": "note" }, live.textContent.trim()); steps.appendChild(note); live.textContent = "";
    }
    return {
      step: function (text) {
        if (text !== "writing the answer") settle();  // those words are the answer itself, not a note
        tick();
        current = el("li", { "class": "now" });
        current.appendChild(el("span", { "class": "tick" }, "▸ ")); current.appendChild(document.createTextNode(text));
        steps.appendChild(current); toBottom();
      },
      text: function (words) { live.textContent += words; toBottom(); },
      thought: function (words) { live.classList.add("thinking"); live.textContent += words; toBottom(); },
      done: function (answer, queries) {
        clearInterval(timer); tick(); live.remove(); clock.remove();
        var count = steps.children.length, secs = ((Date.now() - started) / 1000).toFixed(1);
        var how = el("details", { "class": "ask-how" });
        how.appendChild(el("summary", {}, "how it got there · " + count + " steps · " + secs + "s"));
        body.replaceChild(how, steps); how.appendChild(steps);
        finish(body, answer, queries); bot.setAttribute("class", "ask-bot idle"); bot.replaceChild(avatar(false).firstChild, bot.firstChild); toBottom();
      },
      fail: function (message) {
        clearInterval(timer); tick(); live.remove(); clock.remove();
        body.appendChild(el("p", { "class": "ask-error" }, message)); bot.replaceChild(avatar(false).firstChild, bot.firstChild); toBottom();
      }
    };
  }

  function lines(response, onLine) {
    var reader = response.body.getReader(), decoder = new TextDecoder(), rest = "";
    function pump() {
      return reader.read().then(function (chunk) {
        rest += decoder.decode(chunk.value || new Uint8Array(), { stream: !chunk.done });
        var parts = rest.split("\n"); rest = parts.pop();
        parts.forEach(function (p) { if (p.trim()) onLine(JSON.parse(p)); });
        if (chunk.done) { if (rest.trim()) onLine(JSON.parse(rest)); return; }
        return pump();
      });
    }
    return pump();
  }

  function busy(on) { working = on; }

  // `target` is a container to draw into (the dock's answer panel); `context` says what the person is looking at.
  function ask(question, target, context) {
    log = target || askLog; if (!target) empty.hidden = true;
    var page = MC.view();
    userTurn(question);
    var turn = claudeTurn(), finished = false;
    turn.step("sending the question"); busy(true);
    function end(fn) { if (!finished) { finished = true; fn(); } }
    fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question, history: history.slice(-6), stream: true, context: context || "" }) })
      .then(function (r) {
        if ((r.headers.get("Content-Type") || "").indexOf("application/x-ndjson") !== 0) {
          // Rejected before streaming (JSON), or an older dashboard server (an HTML error page).
          return r.text().then(function (text) {
            var message; try { message = JSON.parse(text).error; } catch (e) { message = "this dashboard server is older than this page: restart `handoff dashboard`"; }
            end(function () { turn.fail(message || "no answer"); });
          });
        }
        return lines(r, function (line) {
          if (line.step) turn.step(line.step);
          else if (line.text) turn.text(line.text);
          else if (line.thought) turn.thought(line.thought);
          else if (line.error) end(function () { turn.fail(line.error); });
          else if (line.answer) end(function () { turn.done(line.answer, line.queries || []); history.push({ q: question, a: line.answer }); saved.push({ q: question, a: line.answer, queries: line.queries || [], page: page }); store(); var other = target ? askLog : document.getElementById("dock-chat-log"); if (target) empty.hidden = true; mirror(question, line.answer, line.queries || [], page, other); });
        });
      })
      .catch(function (e) { end(function () { turn.fail("could not ask: " + e.message); }); })
      .then(function () { busy(false); });
  }

  document.getElementById("ask-new").addEventListener("click", function () {
    if (working) return;
    history = []; saved = []; store(); MC.clear(askLog); MC.clear(document.getElementById("dock-chat-log")); empty.hidden = false;
  });
  STARTERS.forEach(function (s) {
    var b = el("button", { type: "button" }, s);
    b.addEventListener("click", function () { if (!working) ask(s); });
    chips.appendChild(b);
  });
  var botHolder = document.getElementById("ask-empty-bot");
  if (botHolder) botHolder.appendChild(avatar(true));  // waiting for a question: alive, not asleep

  // Bring back the conversation from the last visit, into the Ask page and the panel alike.
  saved = load().filter(function (t) { return t && typeof t.q === "string" && typeof t.a === "string"; });
  saved.forEach(function (t) {
    var queries = Array.isArray(t.queries) ? t.queries.filter(function (q) { return typeof q === "string"; }) : [], page = typeof t.page === "string" ? t.page : "ask";
    history.push({ q: t.q, a: t.a }); empty.hidden = true;
    mirror(t.q, t.a, queries, page, askLog); mirror(t.q, t.a, queries, page, document.getElementById("dock-chat-log"));
  });

  // The command field (dock.js) asks through here: false when the last question is still being answered.
  MC.ask = { start: function (q, target, context) { if (working) return false; ask(q, target, context); return true; } };
  MC.views.ask = { update: function () {} };
})();
