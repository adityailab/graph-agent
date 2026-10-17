// Light, dark or the system's choice. The choice is remembered in this browser only; when storage
// is unavailable the page simply follows the system. Loaded in <head> so the page never flashes.
(function () {
  "use strict";
  var KEY = "handoff-theme", root = document.documentElement;

  function stored() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function remember(value) { try { localStorage.setItem(KEY, value); } catch (e) { /* the choice just is not kept */ } }
  function effective() {
    var set = root.getAttribute("data-theme");
    return set || (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  }

  var saved = stored();
  if (saved === "dark" || saved === "light") root.setAttribute("data-theme", saved);

  document.addEventListener("DOMContentLoaded", function () {
    var button = document.getElementById("theme");
    if (!button) return;
    function label() { button.textContent = effective() === "dark" ? "light mode" : "dark mode"; }
    button.addEventListener("click", function () {
      var next = effective() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next); remember(next); label();
    });
    label();
  });
})();
