// Puts events on a shared time axis: events that landed together share a row across the columns,
// so an empty cell in a column means that session did nothing then. Pure; no DOM.
(function () {
  "use strict";
  var SAME_MOMENT_MS = 2000, GAP_MS = 60000;

  // events: newest first. Returns rows newest first: {at, cells: {role: event}, gap: ms before the next (older) row}.
  function pack(events) {
    var rows = [];
    events.forEach(function (e) {
      var row = rows[rows.length - 1];
      if (!row || row.cells[e.role] || row.at - e.at > SAME_MOMENT_MS) {
        row = { at: e.at, cells: {}, gap: 0 }; rows.push(row);
      }
      row.cells[e.role] = e;
    });
    rows.forEach(function (r, i) {
      var older = rows[i + 1];
      r.gap = older && r.at - older.at >= GAP_MS ? r.at - older.at : 0;
    });
    return rows;
  }

  function span(ms) {
    var m = Math.round(ms / 60000);
    if (m < 60) return m + " min";
    var h = Math.floor(m / 60), rest = m % 60;
    return h + " h" + (rest ? " " + rest + " min" : "");
  }

  window.MC.logrows = { pack: pack, span: span };
})();
