// The little markdown Claude answers in (headings, bold, `code`, bullets), built as nodes and
// never as HTML, so text that came from the graph cannot inject markup.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el;

  function inline(parent, text) {
    text.split(/(\*\*[^*]+\*\*|`[^`]+`)/).forEach(function (part) {
      if (/^\*\*[^*]+\*\*$/.test(part)) parent.appendChild(el("strong", {}, part.slice(2, -2)));
      else if (/^`[^`]+`$/.test(part)) parent.appendChild(el("code", {}, part.slice(1, -1)));
      else if (part) MC.rich(parent, part);
    });
    return parent;
  }

  function render(box, text) {
    var list = null;
    text.split("\n").forEach(function (line) {
      var bullet = /^\s*(?:[-*]|\d+\.)\s+(.*)$/.exec(line), head = /^#{1,4}\s+(.*)$/.exec(line);
      if (bullet) {
        if (!list) { list = el("ul", { "class": "ask-list" }); box.appendChild(list); }
        list.appendChild(inline(el("li"), bullet[1]));
        return;
      }
      list = null;
      if (head) box.appendChild(inline(el("h4", { "class": "ask-head" }), head[1]));
      else if (line.trim()) box.appendChild(inline(el("p", { "class": "full" }), line));
    });
  }

  MC.markdown = render;
})();
