// Each session is a small round "dot" character: a soft blob body, big eyes, a cheek each and an
// antenna dot. While the session works its pupils look around and the antenna pings; when it is
// idle the eyes close, it dims, and a small "z" floats up. The header logo is three of them
// handing work along. (Original drawing; colours come from the session's role.)
(function () {
  "use strict";
  var MC = window.MC, el = MC.el, NS = "http://www.w3.org/2000/svg";
  var WIDTH = 44, HEIGHT = 32;
  var BODY = "M3 29C1 29 1 24 2 19C3 9 11 6 22 6C33 6 41 9 42 19C43 24 43 29 41 29Z";

  function shape(tag, attrs, cls) {
    var n = document.createElementNS(NS, tag);
    Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (cls) n.setAttribute("class", cls);
    return n;
  }

  function eye(g, cx) {
    var wrap = shape("g", {}, "eye");
    wrap.appendChild(shape("ellipse", { cx: cx, cy: 19, rx: 4.6, ry: 5.2, fill: "#fff" }));
    wrap.appendChild(shape("circle", { cx: cx + 0.6, cy: 19.6, r: 2.4, fill: "#121826" }, "pupil"));
    g.appendChild(wrap);
  }

  // Returns a <g> at (x, y); `active` picks the working or the resting pose.
  function draw(x, y, colour, active) {
    var g = el("g", { transform: "translate(" + x + "," + y + ")" }), bot = el("g", { "class": "bot " + (active ? "work" : "idle") });
    bot.appendChild(shape("path", { d: "M22 6V2.5", stroke: colour, "stroke-width": 1.8, "stroke-linecap": "round", fill: "none" }));
    bot.appendChild(shape("circle", { cx: 22, cy: 2.4, r: 2.3, fill: colour }, "ping"));
    bot.appendChild(shape("path", { d: BODY, fill: colour }));
    bot.appendChild(shape("ellipse", { cx: 14, cy: 12, rx: 7, ry: 3, fill: "#fff", opacity: 0.18 }));
    eye(bot, 15); eye(bot, 29);
    bot.appendChild(shape("circle", { cx: 8.5, cy: 25, r: 2, fill: "#fff", opacity: 0.3 }));
    bot.appendChild(shape("circle", { cx: 35.5, cy: 25, r: 2, fill: "#fff", opacity: 0.3 }));
    bot.appendChild(shape("path", { d: "M19 26Q22 28.6 25 26", stroke: "#121826", "stroke-width": 1.3, "stroke-linecap": "round", fill: "none" }, "mouth"));
    var z = shape("text", { x: 38, y: 8, "font-size": 8, "font-weight": 700, fill: colour }, "zz"); z.textContent = "z";
    bot.appendChild(z);
    g.appendChild(bot);
    return g;
  }

  // The header mark: three dots handing work along.
  function drawLogo(svg) {
    [[10, "d0"], [32, "d1"], [54, "d2"]].forEach(function (d) {
      svg.appendChild(shape("path", { d: "M" + d[0] + " 8V4", "stroke-width": 1.6, "stroke-linecap": "round", fill: "none" }, "stem " + d[1]));
      svg.appendChild(shape("circle", { cx: d[0], cy: 3, r: 1.8 }, "dot " + d[1]));
      svg.appendChild(shape("ellipse", { cx: d[0], cy: 16, rx: 9, ry: 8 }, "dot " + d[1]));
      [-3, 3].forEach(function (dx) {
        svg.appendChild(shape("circle", { cx: d[0] + dx, cy: 15, r: 2.4, fill: "#fff" }));
        svg.appendChild(shape("circle", { cx: d[0] + dx + 0.6, cy: 15.3, r: 1.2, fill: "#121826" }));
      });
    });
    [19, 41].forEach(function (x) { svg.appendChild(shape("path", { d: "M" + x + " 15h6m-2-2 2 2-2 2", fill: "none", "stroke-width": 1.6, "stroke-linecap": "round" }, "hand")); });
  }

  var logo = document.getElementById("logo");
  if (logo) drawLogo(logo);

  MC.critter = { draw: draw, width: WIDTH, height: HEIGHT };
})();
