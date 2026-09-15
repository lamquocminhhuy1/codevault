/* Checking / win / lose reveal for the ticket-check result panel.
   Exposes window.LotteryAnimations, used by lottery-check.js. */
window.LotteryAnimations = (function () {
  "use strict";

  var CONSOLATION_CAPTIONS = [
    "Vẫn là kênh đầu tư nhiều rủi ro 😄 Hẹn mai dò tiếp.",
    "Thị trường xổ số hôm nay... chưa thuận lợi lắm 📉",
    "Không sao, coi như góp vui cho đài hôm nay 🙏",
    "Vốn vẫn còn, cơ hội vẫn còn. Mai lại quay số! 🍀",
    "Đầu tư mà, đâu phải lúc nào cũng lãi 😅",
    "Chưa trúng không có nghĩa là hết duyên - thử ván khác nhé!"
  ];

  function qs(root, sel) {
    return root.querySelector(sel);
  }

  function resetStates(panel) {
    var states = panel.querySelectorAll(".lt-result-state");
    for (var i = 0; i < states.length; i++) {
      states[i].hidden = true;
    }
  }

  var reelTimer = null;

  function runReel(reel) {
    if (!reel) {
      return;
    }
    var digits = reel.querySelectorAll(".lt-reel-digit");
    window.clearInterval(reelTimer);
    reelTimer = window.setInterval(function () {
      for (var i = 0; i < digits.length; i++) {
        digits[i].textContent = String(Math.floor(Math.random() * 10));
      }
    }, 80);
  }

  function stopReel() {
    window.clearInterval(reelTimer);
  }

  function showChecking(panel) {
    panel.hidden = false;
    resetStates(panel);
    qs(panel, "#state-checking").hidden = false;
    runReel(qs(panel, "#reel"));
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function formatVnd(n) {
    return Number(n || 0).toLocaleString("vi-VN") + "đ";
  }

  function showResult(panel, data) {
    stopReel();
    resetStates(panel);
    if (!data.checked) {
      qs(panel, "#state-pending").hidden = false;
      return;
    }
    if (data.is_winner) {
      qs(panel, "#win-tier").textContent = data.tier_label + " (khớp số " + data.matched_number + ")";
      qs(panel, "#win-amount").textContent = "+" + formatVnd(data.payout_amount);
      qs(panel, "#state-win").hidden = false;
      burstConfetti(qs(panel, "#confetti-canvas"));
    } else {
      var caption = CONSOLATION_CAPTIONS[Math.floor(Math.random() * CONSOLATION_CAPTIONS.length)];
      qs(panel, "#lose-caption").textContent = caption;
      qs(panel, "#state-lose").hidden = false;
    }
  }

  function showErrors(panel) {
    stopReel();
    resetStates(panel);
    var el = qs(panel, "#state-pending");
    el.hidden = false;
    var msg = el.querySelector("p");
    if (msg) {
      msg.textContent = "Có lỗi khi lưu vé - kiểm tra lại thông tin đã nhập.";
    }
  }

  function showNetworkError(panel) {
    stopReel();
    resetStates(panel);
    var el = qs(panel, "#state-pending");
    el.hidden = false;
    var msg = el.querySelector("p");
    if (msg) {
      msg.textContent = "Không kết nối được tới máy chủ - thử lại nhé.";
    }
  }

  function burstConfetti(canvas) {
    if (!canvas || !canvas.getContext) {
      return;
    }
    var ctx = canvas.getContext("2d");
    var w = (canvas.width = canvas.clientWidth);
    var h = (canvas.height = canvas.clientHeight);
    var colors = ["#ffd23f", "#ee4266", "#3bceac", "#0ead69", "#8a4fff"];
    var particles = [];
    var count = 90;
    var i;
    for (i = 0; i < count; i++) {
      particles.push({
        x: w / 2 + (Math.random() - 0.5) * 40,
        y: h * 0.35,
        vx: (Math.random() - 0.5) * 9,
        vy: Math.random() * -7 - 2,
        size: Math.random() * 6 + 4,
        color: colors[Math.floor(Math.random() * colors.length)],
        rot: Math.random() * 360,
        vrot: (Math.random() - 0.5) * 12
      });
    }
    var start = Date.now();
    function frame() {
      var elapsed = Date.now() - start;
      ctx.clearRect(0, 0, w, h);
      var alive = false;
      for (i = 0; i < particles.length; i++) {
        var p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.25;
        p.rot += p.vrot;
        if (p.y < h + 20) {
          alive = true;
        }
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate((p.rot * Math.PI) / 180);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
        ctx.restore();
      }
      if (alive && elapsed < 2800) {
        window.requestAnimationFrame(frame);
      } else {
        ctx.clearRect(0, 0, w, h);
      }
    }
    window.requestAnimationFrame(frame);
  }

  return {
    showChecking: showChecking,
    showResult: showResult,
    showErrors: showErrors,
    showNetworkError: showNetworkError
  };
})();
