/* Client-side ticket-number OCR for the /xoso/check/ "Quét ảnh" mode.
   Runs entirely in the browser via ocrad.js (vendored, self-hosted) - the
   photo never leaves the device. Only pre-fills the number field; the
   user always reviews/edits it before the ticket is saved. */
(function () {
  "use strict";

  var input = document.getElementById("id_scan_input");
  var dropzone = document.querySelector(".lt-scan-dropzone");
  var preview = document.getElementById("scan-preview");
  var placeholder = document.getElementById("scan-preview-placeholder");
  var status = document.getElementById("scan-status");
  var numberField = document.getElementById("id_number");

  if (!input || !dropzone || typeof OCRAD === "undefined") {
    return;
  }

  input.addEventListener("change", function () {
    var file = input.files && input.files[0];
    if (!file) {
      return;
    }
    var reader = new FileReader();
    reader.onload = function (evt) {
      preview.src = evt.target.result;
      preview.hidden = false;
      if (placeholder) {
        placeholder.hidden = true;
      }
      if (status) {
        status.textContent = "Đang nhận diện số...";
      }
      var img = new Image();
      img.onload = function () {
        runOcr(img);
      };
      img.onerror = function () {
        if (status) {
          status.textContent = "Không đọc được ảnh - vui lòng nhập tay.";
        }
      };
      img.src = evt.target.result;
    };
    reader.readAsDataURL(file);
  });

  function runOcr(img) {
    try {
      var canvas = document.createElement("canvas");
      // Downscale - ocrad doesn't need full camera resolution and stays
      // fast either way; keeps this snappy even on a big photo.
      var scale = Math.min(1, 900 / img.naturalWidth);
      canvas.width = Math.round(img.naturalWidth * scale);
      canvas.height = Math.round(img.naturalHeight * scale);
      var ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      var text = OCRAD(canvas, { numeric: true });
      var digitRuns = (text || "").match(/\d{2,}/g) || [];
      digitRuns.sort(function (a, b) {
        return b.length - a.length;
      });
      var best = digitRuns[0];

      if (best && numberField) {
        numberField.value = best.slice(0, 6);
        if (status) {
          status.textContent = "Đã nhận diện: " + numberField.value + " - kiểm tra lại trước khi dò nhé!";
        }
        numberField.focus();
      } else if (status) {
        status.textContent = "Không nhận diện được số rõ ràng - vui lòng nhập tay.";
      }
    } catch (err) {
      if (status) {
        status.textContent = "Không nhận diện được số - vui lòng nhập tay.";
      }
    }
  }
})();
