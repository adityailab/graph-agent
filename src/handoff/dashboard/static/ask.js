// The ask page: a chat with the graphs. Claude Code writes read-only Cypher, and the page shows
// what it is doing as it happens (steps, notes, the answer being written), then the answer and
// the Cypher so it can be checked. Earlier turns are sent along, so follow-ups keep their subject.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;
  var form = document.getElementById("ask-form"), input = document.getElementById("ask-input");
  var send = document.getElementById("ask-send"), log = document.getElementById("ask-log");
  var empty = document.getElementById("ask-empty"), chips = document.getElementById("ask-chips");
  var STARTERS = [
    "What is each session working on right now?",
    "Which decisions were replaced, and by what?",
    "Which standing rules are in force?",
    "Who has read whose work?"
  ];
  var history = [];  // earlier {q, a} turns

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
      done: function (answer, queries, quick) {
        clearInterval(timer); tick(); live.remove(); clock.remove();
        var count = steps.children.length, secs = ((Date.now() - started) / 1000).toFixed(1);
        var how = el("details", { "class": "ask-how" });
        how.appendChild(el("summary", {}, "how it got there · " + count + " steps · " + secs + "s"));
        body.replaceChild(how, steps); how.appendChild(steps);
        var text = el("div", { "class": "ask-answer" }); MC.markdown(text, answer); body.appendChild(text);
        if (quick) body.appendChild(el("p", { "class": "dim" }, "answered straight from the graph, no model used · source: " + quick));
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
        body.appendChild(copy); bot.setAttribute("class", "ask-bot idle"); bot.replaceChild(avatar(false).firstChild, bot.firstChild); toBottom();
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

  function busy(on) { send.disabled = on; input.disabled = on; if (!on) input.focus(); }

  function ask(question) {
    empty.hidden = true; userTurn(question);
    var turn = claudeTurn(), finished = false;
    turn.step("sending the question"); busy(true);
    function end(fn) { if (!finished) { finished = true; fn(); } }
    fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question, history: history.slice(-6), stream: true }) })
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
          else if (line.answer) end(function () { turn.done(line.answer, line.queries || [], line.quick); history.push({ q: question, a: line.answer }); });
        });
      })
      .catch(function (e) { end(function () { turn.fail("could not ask: " + e.message); }); })
      .then(function () { busy(false); });
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var q = input.value.trim();
    if (!q || send.disabled) return;
    input.value = ""; ask(q);
  });
  document.getElementById("ask-new").addEventListener("click", function () {
    if (send.disabled) return;
    history = []; MC.clear(log); empty.hidden = false; input.focus();
  });
  STARTERS.forEach(function (s) {
    var b = el("button", { type: "button" }, s);
    b.addEventListener("click", function () { if (!send.disabled) ask(s); });
    chips.appendChild(b);
  });
  var botHolder = document.getElementById("ask-empty-bot");
  if (botHolder) botHolder.appendChild(avatar(true));  // waiting for a question: alive, not asleep

  MC.views.ask = { update: function () {} };
})();
