(function () {
  "use strict";

  var start = function () { requestAnimationFrame(function () { setTimeout(init, 0); }); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
  function init() {
  var reduceMQ = window.matchMedia("(prefers-reduced-motion: reduce)");
  var reduce = function () { return reduceMQ.matches; };
  var finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  var toggle = document.getElementById("menu-toggle");
  var panel = document.getElementById("mobile-nav");
  if (toggle && panel) {
    var setOpen = function (open) {
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.querySelector(".menu-toggle__label").textContent = open ? "Close" : "Menu";
      if (open) panel.removeAttribute("hidden"); else panel.setAttribute("hidden", "");
    };
    toggle.addEventListener("click", function () { setOpen(toggle.getAttribute("aria-expanded") !== "true"); });
    panel.querySelectorAll("a").forEach(function (a) { a.addEventListener("click", function () { setOpen(false); }); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") { setOpen(false); toggle.focus(); }
    });
  }

  var revealEls = document.querySelectorAll(".reveal, [data-stitch]");
  if ("IntersectionObserver" in window && !reduce()) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("is-in"); io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add("is-in"); });
  }

  if ("IntersectionObserver" in window) {
    var loopIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { en.target.classList.toggle("is-offscreen", !en.isIntersecting); });
    });
    document.querySelectorAll(".scene, .road-div").forEach(function (el) { loopIO.observe(el); });
  }

  var para = document.querySelector("[data-parallax] img");
  if (para && !reduce()) {
    var ticking = false;
    var onScroll = function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        var y = Math.min(window.scrollY, 900);
        para.style.setProperty("--parallax", (y * 0.06).toFixed(1) + "px");
        ticking = false;
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  var tape = document.querySelector(".tape__strip");
  if (tape && !reduce()) {
    var tTick = false;
    var onTape = function () {
      if (tTick) return;
      tTick = true;
      requestAnimationFrame(function () {
        var max = document.documentElement.scrollHeight - window.innerHeight;
        var p = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
        tape.style.transform = "translateX(" + ((p - 1) * 100).toFixed(2) + "%)";
        tTick = false;
      });
    };
    window.addEventListener("scroll", onTape, { passive: true });
    onTape();
  }

  var hv = document.querySelector("[data-hero-video]");
  if (hv) {
    var vid = hv.querySelector("video"), vbtn = hv.querySelector("[data-video-toggle]"), vlab = hv.querySelector("[data-video-label]");
    var userPaused = false, vVisible = false;
    var vSync = function () {
      if (!reduce() && vVisible && !userPaused) { vid.play().catch(function () {}); } else { vid.pause(); }
      if (vbtn) { vbtn.setAttribute("aria-pressed", userPaused ? "true" : "false"); vlab.textContent = userPaused ? "Play video" : "Pause video"; }
    };
    if (vbtn) vbtn.addEventListener("click", function () { userPaused = !userPaused; vSync(); });
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (es) { vVisible = es[0].isIntersecting; vSync(); }, { threshold: 0.2 }).observe(hv);
    }
    var mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.addEventListener) mq.addEventListener("change", vSync);
  }

  if (finePointer && !reduce()) {
    document.querySelectorAll("[data-tilt]").forEach(function (card) {
      var raf = 0;
      card.addEventListener("pointermove", function (e) {
        var r = card.getBoundingClientRect();
        var x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
        cancelAnimationFrame(raf);
        raf = requestAnimationFrame(function () {
          card.classList.add("is-tilting");
          card.style.setProperty("--ry", (x * 7).toFixed(2) + "deg");
          card.style.setProperty("--rx", (-y * 7).toFixed(2) + "deg");
        });
      });
      card.addEventListener("pointerleave", function () {
        cancelAnimationFrame(raf);
        card.classList.remove("is-tilting");
        card.style.removeProperty("--rx");
        card.style.removeProperty("--ry");
      });
    });
  }

  var peso = new Intl.NumberFormat("en-PH", { style: "currency", currency: "PHP", maximumFractionDigits: 0 });
  var countEls = document.querySelectorAll("[data-count]");
  var runCount = function (el) {
    var end = +el.getAttribute("data-count"), suf = el.getAttribute("data-suffix") || "", t0 = 0;
    var step = function (t) {
      if (!t0) t0 = t;
      var p = Math.min((t - t0) / 1400, 1), e = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(end * e) + suf;
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  if ("IntersectionObserver" in window && !reduce()) {
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { runCount(en.target); cio.unobserve(en.target); } });
    }, { threshold: 0.6 });
    countEls.forEach(function (el) { cio.observe(el); });
  }

  var fwrap = document.querySelector("[data-filters]");
  if (fwrap) {
    var state = { condition: "all", body: "all" };
    var cards = document.querySelectorAll(".listing");
    var countOut = document.querySelector("[data-filter-count]"), empty = document.querySelector("[data-filter-empty]");
    fwrap.addEventListener("click", function (e) {
      var btn = e.target.closest(".chip");
      if (!btn) return;
      var key = btn.getAttribute("data-filter");
      state[key] = btn.getAttribute("data-value");
      fwrap.querySelectorAll('.chip[data-filter="' + key + '"]').forEach(function (b) { b.setAttribute("aria-pressed", b === btn ? "true" : "false"); });
      var n = 0;
      cards.forEach(function (card) {
        var ok = (state.condition === "all" || card.getAttribute("data-condition") === state.condition) &&
                 (state.body === "all" || card.getAttribute("data-body") === state.body);
        card.hidden = !ok;
        card.classList.remove("is-filtering");
        if (ok) { n++; card.classList.add("is-in"); if (!reduce()) { void card.offsetWidth; card.classList.add("is-filtering"); } }
      });
      countOut.textContent = "Showing " + n + " sample listing" + (n === 1 ? "" : "s");
      empty.hidden = n !== 0;
    });
  }

  var calc = document.querySelector("[data-calc]");
  if (calc) {
    var $ = function (id) { return document.getElementById(id); };
    var outM = document.querySelector("[data-out-monthly]"), outDp = document.querySelector("[data-out-dp]"),
        outFin = document.querySelector("[data-out-fin]"), outInt = document.querySelector("[data-out-int]"),
        live = document.querySelector("[data-out-live]"), hint = document.querySelector("[data-dp-hint]");
    var shown = 0, raf2 = 0, liveTimer = 0;
    var mode = function () { return calc.querySelector('input[name="dpmode"]:checked').value; };
    var num = function (el) { var v = parseFloat(el.value); return isFinite(v) && v > 0 ? v : 0; };
    var tween = function (to) {
      cancelAnimationFrame(raf2);
      if (reduce()) { shown = to; outM.textContent = peso.format(to); return; }
      var from = shown, t0 = 0;
      outM.classList.remove("bump"); void outM.offsetWidth; outM.classList.add("bump");
      var step = function (t) {
        if (!t0) t0 = t;
        var p = Math.min((t - t0) / 600, 1), e = 1 - Math.pow(1 - p, 3);
        shown = from + (to - from) * e;
        outM.textContent = peso.format(shown);
        if (p < 1) raf2 = requestAnimationFrame(step);
      };
      raf2 = requestAnimationFrame(step);
    };
    var update = function () {
      var price = num($("c-price")), dpIn = num($("c-dp")), months = +$("c-term").value || 12, rate = num($("c-rate"));
      var dp = mode() === "pct" ? price * Math.min(dpIn, 100) / 100 : Math.min(dpIn, price);
      var fin = Math.max(price - dp, 0), interest = fin * (rate / 100) * (months / 12);
      var monthly = months ? (fin + interest) / months : 0;
      outDp.textContent = peso.format(dp); outFin.textContent = peso.format(fin); outInt.textContent = peso.format(interest);
      tween(Math.round(monthly));
      clearTimeout(liveTimer);
      liveTimer = setTimeout(function () {
        live.textContent = "Estimated monthly payment " + peso.format(Math.round(monthly)) + " for " + months + " months. Amount financed " + peso.format(fin) + ". Estimate only. Actual terms depend on the bank.";
      }, 500);
    };
    calc.querySelectorAll('input[name="dpmode"]').forEach(function (r) {
      r.addEventListener("change", function () {
        var price = num($("c-price")), v = num($("c-dp"));
        if (mode() === "php") { $("c-dp").value = Math.round(price * v / 100); hint.textContent = "Amount in pesos (₱)"; }
        else { $("c-dp").value = price ? +(v / price * 100).toFixed(1) : 0; hint.textContent = "Percent of the car price"; }
        update();
      });
    });
    calc.addEventListener("input", update);
    calc.addEventListener("change", update);
    shown = 0; update();
  }

  document.querySelectorAll("[data-carousel]").forEach(function (root) {
    var slides = [].slice.call(root.querySelectorAll("[data-slide]"));
    var dots = [].slice.call(root.querySelectorAll("[data-dot]"));
    var viewport = root.querySelector(".carousel__viewport");
    var pauseBtn = root.querySelector("[data-pause]");
    var pauseLabel = root.querySelector("[data-pause-label]");
    var current = 0, timer = null, userPaused = reduce(), hoverPause = false;
    var DELAY = 7000;
    var show = function (i) {
      current = (i + slides.length) % slides.length;
      slides.forEach(function (s, k) {
        s.classList.toggle("is-active", k === current);
        s.classList.toggle("is-before", k < current);
        s.setAttribute("aria-hidden", k === current ? "false" : "true");
      });
      dots.forEach(function (d, k) { if (k === current) d.setAttribute("aria-current", "true"); else d.removeAttribute("aria-current"); });
    };
    var running = function () { return !userPaused && !hoverPause && !reduce(); };
    var schedule = function () {
      clearTimeout(timer);
      viewport.setAttribute("aria-live", running() ? "off" : "polite");
      if (running()) timer = setTimeout(function () { show(current + 1); schedule(); }, DELAY);
    };
    var setPaused = function (p) {
      userPaused = p;
      pauseLabel.textContent = p ? "Play" : "Pause";
      pauseBtn.querySelector("svg").outerHTML = p
        ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M7 4.5v15l12-7.5z"/></svg>'
        : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M8 5v14M16 5v14"/></svg>';
      schedule();
    };
    root.querySelector("[data-prev]").addEventListener("click", function () { show(current - 1); schedule(); });
    root.querySelector("[data-next]").addEventListener("click", function () { show(current + 1); schedule(); });
    dots.forEach(function (d) { d.addEventListener("click", function () { show(+d.getAttribute("data-dot")); schedule(); }); });
    pauseBtn.addEventListener("click", function () { setPaused(!userPaused); });
    root.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight") { show(current + 1); schedule(); e.preventDefault(); }
      else if (e.key === "ArrowLeft") { show(current - 1); schedule(); e.preventDefault(); }
    });

    root.addEventListener("mouseenter", function () { hoverPause = true; schedule(); });
    root.addEventListener("mouseleave", function () { hoverPause = false; schedule(); });
    root.addEventListener("focusin", function () { hoverPause = true; schedule(); });
    root.addEventListener("focusout", function (e) { if (!root.contains(e.relatedTarget)) { hoverPause = false; schedule(); } });

    var visible = false;
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (en) { visible = en[0].isIntersecting; if (visible) schedule(); else clearTimeout(timer); }).observe(root);
    }
    document.addEventListener("visibilitychange", function () { if (document.hidden) clearTimeout(timer); else if (visible) schedule(); });
    reduceMQ.addEventListener && reduceMQ.addEventListener("change", function () { if (reduce()) { setPaused(true); pauseBtn.hidden = true; } });
    if (userPaused) { setPaused(true); pauseBtn.hidden = true; }
    show(0);
  });
  }
})();
