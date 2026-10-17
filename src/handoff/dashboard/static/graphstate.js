// What the graph page is showing and why: the choices made in the toolbar, the derived model, and
// the nodes now on the canvas. Shared by the canvas, the side panel and the toolbar.
(function () {
  "use strict";
  var st = {
    s: { mode: "work", by: "session", kinds: { Decision: true, Need: true, Message: false, Request: false, File: false }, only: null, expanded: {}, selected: null, pinning: false, memoryKind: null },
    model: { nodes: {}, edges: [], out: {}, inn: {}, readers: {}, replacedBy: {}, topic: {}, cross: [] }, vis: { ids: {}, hidden: {} }, totals: {}, hover: null, hoverLink: null,
    plain: function () { return st.s.mode !== "work"; },
    hulls: function () { return st.s.mode === "work" && st.s.by !== "none"; },
    // The node the canvas lights up: the selected one, else the one under the pointer.
    focus: function () { return st.s.selected || (st.hover && st.hover.id) || null; },
    near: function (id) {
      var f = st.focus(), m = st.model;
      if (!f || !m || !m.nodes[f]) return true;
      return id === f || m.out[f].concat(m.inn[f]).some(function (e) { return e.source === id || e.target === id; });
    }
  };
  window.MC.graphState = st;
})();
