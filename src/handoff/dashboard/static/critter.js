// A small pixel bot for each session: an antenna and a visor with a scanner light. While the
// session is active the antenna blinks and the scanner sweeps; when it is idle both go still and dim.
(function () {
  "use strict";
  var MC = window.MC, el = MC.el, PX = 4;
  var BODY = ["....XXX....", ".....X.....", ".XXXXXXXXX.", ".XXXXXXXXX.", "XXX.....XXX", "XXX.....XXX", ".XXXXXXXXX.", "...XXXXX..."];
  var WIDTH = 11 * PX, HEIGHT = 8 * PX;

  // Returns a <g> at (x, y); `active` picks the working or the resting pose.
  function draw(x, y, colour, active) {
    var g = el("g", { transform: "translate(" + x + "," + y + ")" }), bot = el("g", { "class": "bot " + (active ? "work" : "idle") });
    BODY.forEach(function (row, j) {
      for (var i = 0; i < row.length; i++)
        if (row[i] === "X") bot.appendChild(el("rect", { x: i * PX, y: j * PX, width: PX, height: PX, fill: colour, "class": j === 0 ? "ball" : "" }));
    });
    bot.appendChild(el("rect", { x: 3 * PX, y: 4 * PX, width: PX * 2, height: PX * 2, "class": "scan", fill: colour }));
    g.appendChild(bot);
    return g;
  }

  MC.critter = { draw: draw, width: WIDTH, height: HEIGHT };
})();
