// Where each node sits when the graph is grouped: every group gets a block of cells (decisions
// first, then needs, then the rest), blocks are laid out in rows, so hulls never overlap and
// every caption has room.
(function () {
  "use strict";
  var CELL_W = 170, CELL_H = 130, GAP = 56, ROW = 1240, SIDE = 78, TOP = 54, BOTTOM = 82;  // the last three are the hull's padding round its nodes
  var ORDER = { Decision: 0, Need: 1, Request: 2, Message: 3, Edit: 4, File: 5, Session: 6 };

  function arrange(ids, nodes) {
    return ids.slice().sort(function (a, b) {
      var x = nodes[a], y = nodes[b];
      return (ORDER[x.kind] || 9) - (ORDER[y.kind] || 9) || (x.at || 0) - (y.at || 0);
    });
  }

  // `groups` maps a group name to its node ids; returns {id: {x, y}} centred on the origin.
  function place(groups, nodes) {
    var out = {}, x = 0, y = 0, rowH = 0, right = 0, names = Object.keys(groups).sort();
    names.forEach(function (g) {
      var ids = arrange(groups[g], nodes), cols = Math.max(1, Math.ceil(Math.sqrt(ids.length * 1.1))), rows = Math.ceil(ids.length / cols);
      var w = (cols - 1) * CELL_W + 2 * SIDE, h = (rows - 1) * CELL_H + TOP + BOTTOM;
      if (x > 0 && x + w > ROW) { x = 0; y += rowH + GAP; rowH = 0; }
      ids.forEach(function (id, i) { out[id] = { x: x + SIDE + (i % cols) * CELL_W, y: y + TOP + Math.floor(i / cols) * CELL_H }; });
      x += w + GAP; rowH = Math.max(rowH, h); right = Math.max(right, x - GAP);
    });
    var dx = right / 2, dy = (y + rowH) / 2;
    Object.keys(out).forEach(function (id) { out[id].x -= dx; out[id].y -= dy; });
    return out;
  }

  window.MC.graphLayout = { place: place };
})();
