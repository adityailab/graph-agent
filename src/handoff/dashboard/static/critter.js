// Each session is a tiny compact Macintosh: a rounded body in the session's colour, a cream
// screen with two tall oval eyes (a blob's face), a floppy slot and an LED. While the session
// works the eyes glance about and blink, a mouse cursor roams the screen and the LED blinks, like
// an agent using a computer. When idle the screen dims and everything holds still. The header
// logo is three of them passing work along. (Original drawing, inspired by the first Macintosh.)
(function () {
  "use strict";
  var MC = window.MC, el = MC.el, NS = "http://www.w3.org/2000/svg";
  var WIDTH = 44, HEIGHT = 32;
  var INK = "#121826";

  function shape(tag, attrs, cls) {
    var n = document.createElementNS(NS, tag);
    Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (cls) n.setAttribute("class", cls);
    return n;
  }

  // One Mac in a box `w` wide and `h` tall whose top-left is (x, y), appended to `into`.
  function mac(into, x, y, w, h, colour) {
    var g = shape("g", { transform: "translate(" + x + "," + y + ") scale(" + (w / 30) + "," + (h / 30) + ")" });
    g.appendChild(shape("rect", { x: 0, y: 0, width: 30, height: 30, rx: 5, fill: colour }));
    g.appendChild(shape("rect", { x: 0, y: 0, width: 30, height: 8, rx: 5, fill: "#fff", opacity: 0.16 }));
    g.appendChild(shape("rect", { x: 4, y: 4, width: 22, height: 15, rx: 3, fill: INK, opacity: 0.22 }));
    g.appendChild(shape("rect", { x: 4.8, y: 4.8, width: 20.4, height: 13.4, rx: 2.4 }, "screen"));
    var eyes = shape("g", {}, "eyes");
    [11, 19].forEach(function (cx) { eyes.appendChild(shape("ellipse", { cx: cx, cy: 11.5, rx: 1.7, ry: 3.3, fill: INK }, "eye")); });
    g.appendChild(eyes);
    g.appendChild(shape("rect", { x: 7, y: 23, width: 13, height: 1.8, rx: 0.9, fill: INK, opacity: 0.35 }));
    g.appendChild(shape("circle", { cx: 23.5, cy: 23.9, r: 1.1 }, "led"));
    return g;
  }

  // Returns a <g> at (x, y); `active` picks the working or the resting pose.
  function draw(x, y, colour, active) {
    var g = el("g", { transform: "translate(" + x + "," + y + ")" }), bot = el("g", { "class": "bot " + (active ? "work" : "idle") });
    var m = mac(bot, 7, 1, 30, 30, colour);
    var cur = shape("g", {}, "cur");
    cur.appendChild(shape("polygon", { points: "0,0 0,7 1.9,5.4 3.2,8.4 4.4,7.9 3.1,5 5.6,5", fill: INK, stroke: "#fff", "stroke-width": 0.6, transform: "scale(0.9)" }));
    m.appendChild(cur);
    bot.appendChild(m); g.appendChild(bot);
    return g;
  }

  // The header mark: three Macs passing work along.
  function drawLogo(svg) {
    [["d0", 1], ["d1", 23], ["d2", 45]].forEach(function (d) {
      var m = mac(svg, d[1], 6, 18, 18, "currentColor");
      m.setAttribute("class", d[0]); svg.appendChild(m);
    });
    [19.5, 41.5].forEach(function (x) { svg.appendChild(shape("path", { d: "M" + x + " 15h3m-1.2-1.4 1.2 1.4-1.2 1.4", fill: "none", "stroke-width": 1.3, "stroke-linecap": "round" }, "hand")); });
  }

  var logo = document.getElementById("logo");
  if (logo) drawLogo(logo);

  MC.critter = { draw: draw, width: WIDTH, height: HEIGHT };
})();
