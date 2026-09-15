/* Wiring for the /xoso/check/ page: entry-mode toggle (manual vs scan) and
   the AJAX ticket-check submission that drives LotteryAnimations. */
(function () {
  "use strict";

  var form = document.getElementById("ticket-form");
  var resultPanel = document.getElementById("result-panel");
  if (!form || !resultPanel || !window.LotteryAnimations) {
    return;
  }

  var submitBtn = document.getElementById("check-submit-btn");
  var MIN_CHECKING_MS = 1200;

  form.addEventListener("submit", function (evt) {
    evt.preventDefault();
    if (submitBtn) {
      submitBtn.disabled = true;
    }
    window.LotteryAnimations.showChecking(resultPanel);

    var startedAt = Date.now();
    var formData = new FormData(form);

    fetch(form.getAttribute("action") || window.location.href, {
      method: "POST",
      body: formData
    })
      .then(function (resp) {
        return resp
          .json()
          .catch(function () {
            return { ok: false };
          })
          .then(function (json) {
            return { status: resp.status, json: json };
          });
      })
      .then(function (res) {
        var elapsed = Date.now() - startedAt;
        var wait = Math.max(0, MIN_CHECKING_MS - elapsed);
        window.setTimeout(function () {
          if (submitBtn) {
            submitBtn.disabled = false;
          }
          if (res.status !== 200 || !res.json.ok) {
            window.LotteryAnimations.showErrors(resultPanel);
            return;
          }
          window.LotteryAnimations.showResult(resultPanel, res.json);
        }, wait);
      })
      .catch(function () {
        if (submitBtn) {
          submitBtn.disabled = false;
        }
        window.LotteryAnimations.showNetworkError(resultPanel);
      });
  });

  var againBtn = document.getElementById("check-again-btn");
  if (againBtn) {
    againBtn.addEventListener("click", function () {
      resultPanel.hidden = true;
      form.reset();
      var numberField = document.getElementById("id_number");
      if (numberField) {
        numberField.focus();
      }
    });
  }

  /* ---- Entry mode: manual vs scan ---------------------------------- */

  var modeButtons = document.querySelectorAll("#entry-mode button");
  var scanPanel = document.getElementById("scan-panel");
  for (var i = 0; i < modeButtons.length; i++) {
    (function (btn) {
      btn.addEventListener("click", function () {
        for (var j = 0; j < modeButtons.length; j++) {
          modeButtons[j].classList.remove("active");
        }
        btn.classList.add("active");
        if (scanPanel) {
          scanPanel.hidden = btn.getAttribute("data-mode") !== "scan";
        }
      });
    })(modeButtons[i]);
  }
})();
