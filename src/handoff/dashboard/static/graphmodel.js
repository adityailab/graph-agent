// What the drawn graph needs, worked out from the raw nodes and relationships: who read which
// decision, which decision replaced which, what moved between sessions, and which nodes to show.
(function () {
  "use strict";
  var TOGGLES = ["Decision", "Need", "Message", "Request", "File"];  // File stands for files and edits
  var NONE = "no topic";

  function toggleOf(kind) { return kind === "Edit" ? "File" : kind; }
  function each(list, fn) { (list || []).forEach(fn); }

  function topics(m) {
    Object.keys(m.nodes).forEach(function (id) { if (m.nodes[id].kind === "Decision") m.topic[id] = m.nodes[id].topic || NONE; });
    Object.keys(m.nodes).forEach(function (id) {
      if (m.nodes[id].kind !== "Request") return;
      var led = m.out[id].filter(function (e) { return e.kind === "LED_TO"; })[0];
      m.topic[id] = led ? m.topic[led.target] : NONE;
    });
    Object.keys(m.nodes).forEach(function (id) {
      if (m.nodes[id].kind !== "Edit") return;
      var by = m.inn[id].filter(function (e) { return e.kind === "CAUSED"; })[0];
      m.topic[id] = by ? m.topic[by.source] : NONE;
    });
  }

  // A decision is read by every session whose request consulted the request that led to it.
  function reading(m) {
    each(m.edges, function (e) {
      var reader = m.nodes[e.source], author = m.nodes[e.target];
      if (e.kind !== "CONSULTED" || !reader || !author || reader.role === author.role) return;
      each(m.out[author.id], function (led) {
        if (led.kind !== "LED_TO") return;
        var seen = (m.readers[led.target] = m.readers[led.target] || {});
        if (!(reader.role in seen) || reader.at < seen[reader.role]) seen[reader.role] = reader.at;
      });
    });
  }

  function crossing(m) {
    var tally = {};
    function add(from, to, kind) { if (from && to && from !== to) { var k = from + ">" + to + ">" + kind; tally[k] = (tally[k] || 0) + 1; } }
    each(m.edges, function (e) {
      var a = m.nodes[e.source], b = m.nodes[e.target];
      if (e.kind === "CONSULTED") add(a.role, b.role, "read");
      if (e.kind === "DELIVERED_TO") each(m.inn[a.id], function (s) { if (s.kind === "SENT") add(m.nodes[s.source].role, b.role, "message"); });
    });
    Object.keys(m.nodes).forEach(function (id) { var n = m.nodes[id]; if (n.kind === "Need") add(n.role, n.for_role, "need"); });
    m.cross = Object.keys(tally).map(function (k) { var p = k.split(">"); return { from: p[0], to: p[1], kind: p[2], count: tally[k] }; });
  }

  function build(view) {
    var m = { nodes: {}, edges: view.edges, out: {}, inn: {}, readers: {}, replacedBy: {}, topic: {}, cross: [] };
    each(view.nodes, function (n) { m.nodes[n.id] = n; m.out[n.id] = []; m.inn[n.id] = []; });
    m.edges = view.edges.filter(function (e) { return m.nodes[e.source] && m.nodes[e.target]; });
    each(m.edges, function (e) {
      m.out[e.source].push(e); m.inn[e.target].push(e);
      if (e.kind === "SUPERSEDES") m.replacedBy[e.target] = e.source;
    });
    topics(m); reading(m); crossing(m);
    return m;
  }

  function group(m, n, by) {
    if (by === "topic") return m.topic[n.id] || NONE;
    return n.role || "shared";
  }

  // The nodes to draw. Decisions and needs by default; the other kinds when toggled on or when the
  // node's group is opened, and the whole neighbourhood of the selected node.
  function visible(m, o) {
    var ids = {}, hidden = {}, near = {};
    if (o.focus && m.nodes[o.focus]) {
      near[o.focus] = true;
      each(m.out[o.focus].concat(m.inn[o.focus]), function (e) { near[e.source] = near[e.target] = true; });
    }
    Object.keys(m.nodes).forEach(function (id) {
      var n = m.nodes[id], g = group(m, n, o.group);
      if (o.only && g !== o.only) return;
      if (n.kind === "Session" && o.group === "session") return;  // the hull is the session
      var show = o.all || near[id] || o.kinds[toggleOf(n.kind)] || (o.expanded[g] && n.kind !== "Session") || (n.kind === "Session" && o.group === "none");
      if (show) ids[id] = true; else hidden[g] = (hidden[g] || 0) + 1;
    });
    return { ids: ids, hidden: hidden };
  }

  function counts(m, only, by) {
    var c = {};
    TOGGLES.forEach(function (t) { c[t] = 0; });
    Object.keys(m.nodes).forEach(function (id) {
      var n = m.nodes[id], t = toggleOf(n.kind);
      if (t in c && (!only || group(m, n, by) === only)) c[t]++;
    });
    return c;
  }

  window.MC.graphModel = { TOGGLES: TOGGLES, build: build, group: group, visible: visible, counts: counts };
})();
