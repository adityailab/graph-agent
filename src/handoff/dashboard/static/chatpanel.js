// The answer panel on the right: opens when a question is asked, closes with ×, and its left edge
// drags (or takes the arrow keys) to make it wider or narrower. The width is remembered in this browser.
(function () {
  "use strict";
  var MC = window.MC, panel = document.getElementById("dock-chat"), grip = document.getElementById("chat-grip");
  var KEY = "handoff-chat-width", MIN = 300;

  function limit(w) { return Math.max(MIN, Math.min(Math.round(window.innerWidth * 0.6), w)); }
  function set(w) { document.documentElement.style.setProperty("--chat-w", limit(w) + "px"); }
  function width() { return panel.getBoundingClientRect().width; }
  try { var saved = Number(localStorage.getItem(KEY)); if (saved) set(saved); } catch (e) { /* the default width stays */ }
  function remember() { try { localStorage.setItem(KEY, String(Math.round(width()))); } catch (e) { /* not kept */ } }

  grip.addEventListener("pointerdown", function (ev) {
    grip.setPointerCapture(ev.pointerId);
    function move(e) { set(window.innerWidth - e.clientX - 16); }
    function up() { grip.removeEventListener("pointermove", move); grip.removeEventListener("pointerup", up); remember(); relayout(); }
    grip.addEventListener("pointermove", move); grip.addEventListener("pointerup", up);
  });
  grip.addEventListener("keydown", function (ev) {
    if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;
    ev.preventDefault(); set(width() + (ev.key === "ArrowLeft" ? 24 : -24)); remember();
  });

  // The page changes width when the panel opens, closes or is resized: tell drawings that fit their box.
  function relayout() { setTimeout(function () { window.dispatchEvent(new Event("handoff-layout")); }, 60); }
  function show(on) {
    panel.hidden = !on; document.body.classList.toggle("chat-open", on);
    if (on) document.getElementById("dock-input").focus();
    relayout();
  }
  document.getElementById("dock-chat-close").addEventListener("click", function () { show(false); });
  var icon = document.getElementById("bot-icon");
  if (icon && MC.critter) icon.appendChild(MC.critter.draw(-2, -1, MC.css("--green"), true));
  document.getElementById("bot-button").addEventListener("click", function () { show(true); });
  new MutationObserver(function () { panel.classList.toggle("has-turns", document.getElementById("dock-chat-log").children.length > 0); }).observe(document.getElementById("dock-chat-log"), { childList: true });
  MC.chatPanel = { open: function () { show(true); }, close: function () { show(false); }, isOpen: function () { return !panel.hidden; } };
})();
