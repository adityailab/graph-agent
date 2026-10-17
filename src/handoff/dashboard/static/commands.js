// The command field's grammar: type a question in plain words, or `msg <session> <text>`,
// `need <session> <text>`, `go <page>`. Pure: text in, a plain object out, so the dock only has to carry it out.
(function () {
  "use strict";
  var PAGES = ["orchestration", "handoff", "memory", "graph", "log", "ask", "tracks"];
    var MAX_ASK = 500, MAX_TEXT = 2000;

  function fail(message) { return { kind: "error", message: message }; }

  // A session name the person typed, matched to a known role exactly or by a single prefix.
  function session(word, roles) {
    var w = word.toLowerCase();
    var exact = roles.filter(function (r) { return r.toLowerCase() === w; });
    if (exact.length) return exact[0];
    var starts = roles.filter(function (r) { return r.toLowerCase().indexOf(w) === 0; });
    return starts.length === 1 ? starts[0] : null;
  }

  function page(word) {
    var w = word.toLowerCase(), n = Number(w);
    if (n >= 1 && n <= PAGES.length) return PAGES[n - 1];
    var starts = PAGES.filter(function (p) { return p.indexOf(w) === 0; });
    return w && starts.length === 1 ? starts[0] : null;
  }

  // Anything that is not one of the four commands is a question: the model reads it and writes the Cypher.
  function question(text) {
    return text.length > MAX_ASK ? fail("questions are kept to " + MAX_ASK + " characters") : { kind: "ask", text: text };
  }

  function parse(input, roles) {
    var text = (input || "").trim(), m = /^(\S+)(?:\s+([\s\S]*))?$/.exec(text);
    if (!m) return null;
    var verb = m[1].toLowerCase(), rest = (m[2] || "").trim();
    if (verb === "go" && page(rest)) return { kind: "go", page: page(rest) };
    if (verb === "ask" && rest) return question(rest);
    if (verb === "msg" || verb === "need") {
      var parts = /^(\S+)(?:\s+([\s\S]+))?$/.exec(rest), who = parts && session(parts[1], roles);
      if (who && parts[2]) {
        var body = parts[2].trim();
        return body.length > MAX_TEXT ? fail("that is longer than " + MAX_TEXT + " characters") : { kind: verb, to: who, text: body };
      }
      if (verb === "msg") return fail("msg <session> <text>" + (roles.length ? " (sessions: " + roles.join(", ") + ")" : ""));
    }
    return question(text);  // "need to know…" and "go through…" are questions too
  }

  window.MC.parseCommand = parse;
  window.MC.PAGES = PAGES;
})();
