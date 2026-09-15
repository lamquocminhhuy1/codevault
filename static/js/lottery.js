/* Loaded on every lottery page. Deliberately tiny - page-specific behavior
   (the check flow, OCR, animations) lives in its own file loaded only
   where needed, mirroring app.js/dep-graph.js's split in the vault app. */
(function () {
  "use strict";

  // Auto-dismiss flash messages after a few seconds.
  var messages = document.querySelectorAll(".lt-messages li");
  if (messages.length) {
    window.setTimeout(function () {
      for (var i = 0; i < messages.length; i++) {
        messages[i].style.transition = "opacity 0.4s";
        messages[i].style.opacity = "0";
      }
    }, 4000);
  }
})();
