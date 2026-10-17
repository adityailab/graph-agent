// A small pixel critter for each session: hops and shuffles its legs while the session is active,
// squints and sleeps when it is idle. Drawn from a character map so it stays crisp at any size.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el, PX = 4;
  var BODY = ["..XXXXXXX..", ".XXXXXXXXX.", "XXXXXXXXXXX", ".XXXXXXXXX.", ".XXXXXXXXX.", "..XXXXXXX.."];
  var EYES = [[3, 2], [7, 2]];
  var LEGS_A = [[2, 6], [4, 6], [6, 6], [8, 6]], LEGS_B = [[3, 6], [5, 6], [7, 6], [9, 6]];
  var WIDTH = 11 * PX, HEIGHT = 7 * PX;

  function pixels(group, cells, colour) {
    cells.forEach(function (c) { group.appendChild(el("rect", { x: c[0] * PX, y: c[1] * PX, width: PX, height: PX, fill: colour })); });
  }

  // Returns a <g> at (x, y); `active` picks the working or the sleeping pose.
  function draw(x, y, colour, active) {
    var g = el("g", { transform: "translate(" + x + "," + y + ")" }), body = el("g", { "class": "critter " + (active ? "work" : "idle") });
    var cells = [];
    BODY.forEach(function (row, j) { for (var i = 0; i < row.length; i++) if (row[i] === "X") cells.push([i, j]); });
    pixels(body, cells, colour);
    var a = el("g", { "class": "legs-a" }), b = el("g", { "class": "legs-b" });
    pixels(a, LEGS_A, colour); pixels(b, LEGS_B, colour);
    body.appendChild(a); body.appendChild(b);
    EYES.forEach(function (e) { body.appendChild(el("rect", { x: e[0] * PX, y: e[1] * PX, width: PX, height: PX * 1.4, "class": "eye" })); });
    g.appendChild(body);
    if (!active) g.appendChild(el("text", { x: WIDTH + 2, y: -2, "class": "zzz" }, "z"));
    return g;
  }

  MC.critter = { draw: draw, width: WIDTH, height: HEIGHT };
})();
