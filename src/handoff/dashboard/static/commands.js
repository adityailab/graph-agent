// The command field's grammar: `ask <question>`, `msg <session> <text>`, `need <session> <text>`,
// `go <page>`. Pure: text in, a plain object out, so the dock only has to carry it out.
(function () {
  "use strict";
  var PAGES = ["orchestration", "handoff", "memory", "graph", "log", "ask", "tracks"];
  var HELP = "try: ask <question> · msg <session> <text> · need <session> <text> · go <page>";
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

  function parse(input, roles) {
    var m = /^\s*(\S+)(?:\s+([\s\S]*))?$/.exec(input || "");
    if (!m) return null;
    var verb = m[1].toLowerCase(), rest = (m[2] || "").trim();
    if (verb === "go") {
      var p = page(rest);
      return p ? { kind: "go", page: p } : fail("go where? " + PAGES.join(", "));
    }
    if (verb === "ask") {
      if (!rest) return fail("ask what? ask <question>");
      return rest.length > MAX_ASK ? fail("questions are kept to " + MAX_ASK + " characters") : { kind: "ask", text: rest };
    }
    if (verb === "msg" || verb === "need") {
      var parts = /^(\S+)(?:\s+([\s\S]+))?$/.exec(rest);
      if (!parts || !parts[2]) return fail(verb + " <session> <text>");
      var who = session(parts[1], roles);
      if (!who) return fail("no session called " + parts[1] + (roles.length ? " (sessions: " + roles.join(", ") + ")" : " yet"));
      var text = parts[2].trim();
      return text.length > MAX_TEXT ? fail("that is longer than " + MAX_TEXT + " characters") : { kind: verb, to: who, text: text };
    }
    return fail(HELP);
  }

  window.MC.parseCommand = parse;
  window.MC.PAGES = PAGES;
})();
