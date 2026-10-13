(function () {
  "use strict";
  var S = window.OksCars, me = document.currentScript, form = document.querySelector("[data-owner-form]");
  if (!S || !form) return;
  var LOGO = me.getAttribute("data-logo"), PHONE = me.getAttribute("data-phone") || "";
  var C = { ink: "#1A1313", red: "#A60E0F", redHi: "#E05C54", gold: "#D09F51", goldLt: "#E9CC8E", goldDk: "#9C6E2F", yellow: "#DBA923" };
  var STAMP = { Reserved: "#E8731A", Sold: "#A60E0F" };
  var MAX_BYTES = 200 * 1024, MAX_UPLOAD = 15 * 1024 * 1024, TYPES = ["image/jpeg", "image/png", "image/webp"];
  var $ = function (s) { return document.querySelector(s); };
  var statusOut = $("[data-owner-status]"), list = $("[data-owner-list]"), preview = $("[data-preview]"), dl = $("[data-download]");
  var seed = [], cars = [], post = null;
  var cardCfg = { logo: list.getAttribute("data-logo"), phone: list.getAttribute("data-phone"), badge: "Illustrative photo, not the actual unit", tag: "p", sizes: "300px" };
  var photoFor = function (c) { return c.upload || c.img2x || c.img; };
  var DISPLAY = '"Barlow Condensed", "Barlow Condensed Fallback", "Arial Narrow", sans-serif', BODY = '"Barlow", "Barlow Fallback", Arial, sans-serif';
  var thisYear = new Date().getFullYear();
  form.year.max = thisYear + 1;

  function say(msg, err) { statusOut.textContent = msg; statusOut.classList.toggle("is-error", !!err); }
  function setErr(name, msg) {
    var p = form.querySelector('[data-err="' + name + '"]'), input = form.elements[name];
    p.textContent = msg || ""; p.hidden = !msg;
    if (msg) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid");
    return !msg;
  }
  function loadImg(src) {
    return new Promise(function (res, rej) { var im = new Image(); im.decoding = "async"; im.onload = function () { res(im); }; im.onerror = function () { rej(new Error("image")); }; im.src = src; });
  }
  function readFile(f) { return new Promise(function (res, rej) { var r = new FileReader(); r.onload = function () { res(r.result); }; r.onerror = rej; r.readAsDataURL(f); }); }
  function blobToDataURL(b) { return readFile(b); }
  function toBlob(cv, q) { return new Promise(function (res) { cv.toBlob(res, "image/jpeg", q); }); }

  function validate(editing) {
    var ok = true, y = form.year.value.trim(), f = form.photo.files[0];
    ok = setErr("year", !/^\d{4}$/.test(y) || +y < 1980 || +y > thisYear + 1 ? "Enter a 4-digit year from 1980 to " + (thisYear + 1) + "." : "") && ok;
    ok = setErr("make", !form.make.value.trim() ? "Enter the make, for example Toyota." : "") && ok;
    ok = setErr("model", !form.model.value.trim() ? "Enter the model, for example Vios 1.3 XLE CVT." : "") && ok;
    var pe = "";
    if (!f && !editing) pe = "Choose a photo of the car.";
    else if (f && TYPES.indexOf(f.type) < 0) pe = "Use a JPG, PNG or WebP image.";
    else if (f && f.size > MAX_UPLOAD) pe = "That photo is over 15 MB. Choose a smaller one.";
    ok = setErr("photo", pe) && ok;
    if (!ok) { var bad = form.querySelector('[aria-invalid="true"]'); if (bad) bad.focus(); }
    return ok;
  }

  async function compressUpload(im) {
    var sc = Math.min(1, 1080 / Math.max(im.naturalWidth, im.naturalHeight)), cv = document.createElement("canvas");
    cv.width = Math.round(im.naturalWidth * sc); cv.height = Math.round(im.naturalHeight * sc);
    var x = cv.getContext("2d"); x.fillStyle = "#fff"; x.fillRect(0, 0, cv.width, cv.height); x.drawImage(im, 0, 0, cv.width, cv.height);
    var q = 0.86, b = await toBlob(cv, q);
    while (b.size > 150 * 1024 && q > 0.4) { q = Math.round((q - 0.06) * 100) / 100; b = await toBlob(cv, q); }
    return { url: await blobToDataURL(b), bytes: b.size, width: cv.width, height: cv.height };
  }

  function fitFont(x, text, weight, family, size, maxW) {
    do { x.font = weight + " " + size + "px " + family; size -= 2; } while (x.measureText(text).width > maxW && size > 20);
  }
  function roundRect(x, l, t, w, h, r) { x.beginPath(); x.moveTo(l + r, t); x.arcTo(l + w, t, l + w, t + h, r); x.arcTo(l + w, t + h, l, t + h, r); x.arcTo(l, t + h, l, t, r); x.arcTo(l, t, l + w, t, r); x.closePath(); }
  async function drawPost(photo, car) {
    await Promise.all([document.fonts.load('800 80px "Barlow Condensed"'), document.fonts.load('700 40px "Barlow Condensed"'), document.fonts.load('600 40px "Barlow"'), document.fonts.load('400 20px "Barlow"')]);
    await document.fonts.ready;
    var logo = await loadImg(LOGO);
    var W = 1080, cv = document.createElement("canvas"); cv.width = cv.height = W;
    var x = cv.getContext("2d");

    var M = 60, HB = 272;
    function gold(x0, y0, x1, y1) { var g = x.createLinearGradient(x0, y0, x1, y1); g.addColorStop(0, C.goldDk); g.addColorStop(0.3, C.goldLt); g.addColorStop(0.55, C.gold); g.addColorStop(0.8, "#F3DFAE"); g.addColorStop(1, C.goldDk); return g; }
    function line(pts, w, style) { x.beginPath(); x.moveTo(pts[0], pts[1]); for (var k = 2; k < pts.length; k += 2) x.lineTo(pts[k], pts[k + 1]); x.lineWidth = w; x.strokeStyle = style; x.stroke(); }
    function poly(pts, fill) { x.beginPath(); x.moveTo(pts[0], pts[1]); for (var k = 2; k < pts.length; k += 2) x.lineTo(pts[k], pts[k + 1]); x.closePath(); x.fillStyle = fill; x.fill(); }

    var bg = x.createRadialGradient(540, 620, 80, 540, 620, 820); bg.addColorStop(0, "#FFFDF9"); bg.addColorStop(1, "#F1EBE1");
    x.fillStyle = bg; x.fillRect(0, 0, W, W);

    var hg = x.createLinearGradient(0, 0, 0, HB); hg.addColorStop(0, "#241A19"); hg.addColorStop(1, "#0E0A0A");
    x.fillStyle = hg; x.fillRect(0, 0, W, HB);
    var f1 = x.createLinearGradient(760, 0, 1080, HB); f1.addColorStop(0, "rgba(110,10,11,0)"); f1.addColorStop(0.55, "rgba(110,10,11,.55)"); f1.addColorStop(1, "rgba(150,16,17,.8)");
    poly([800, 0, W, 0, W, HB, 690, HB], f1);
    var f2 = x.createLinearGradient(900, 0, 1080, HB); f2.addColorStop(0, "rgba(233,204,142,0)"); f2.addColorStop(0.7, "rgba(233,204,142,.10)"); f2.addColorStop(1, "rgba(243,223,174,.22)");
    poly([930, 0, W, 0, W, HB, 850, HB], f2);
    line([800, 0, 690, HB], 1.5, gold(690, HB, 800, 0)); line([930, 0, 850, HB], 1.5, gold(850, HB, 930, 0));
    x.fillStyle = gold(0, 0, W, 0); x.fillRect(0, HB, W, 4);
    x.fillStyle = "rgba(208,159,81,.55)"; x.fillRect(0, HB + 9, W, 1);

    var LC = 138, LR = 78;
    x.save(); x.beginPath(); x.arc(M + LR, LC, LR, 0, Math.PI * 2); x.closePath(); x.fillStyle = "#050404"; x.fill(); x.clip(); x.drawImage(logo, M, LC - LR, LR * 2, LR * 2); x.restore();
    x.beginPath(); x.arc(M + LR, LC, LR + 5, 0, Math.PI * 2); x.lineWidth = 3; x.strokeStyle = gold(M, LC - LR, M + 2 * LR, LC + LR); x.stroke();

    var TX = M + 2 * LR + 34;
    x.textAlign = "left"; x.textBaseline = "alphabetic";
    x.fillStyle = "#FBF6EC"; x.font = '800 74px ' + DISPLAY; x.fillText("OKS CARS", TX, 122);
    if ("letterSpacing" in x) x.letterSpacing = "7px";
    x.fillStyle = C.goldLt; x.font = '600 21px ' + BODY; x.fillText("AUTO FINANCING", TX + 2, 158);
    if ("letterSpacing" in x) x.letterSpacing = "0px";
    x.fillStyle = gold(TX, 0, TX + 330, 0); x.fillRect(TX, 178, 330, 1.5);
    x.save(); x.translate(TX + 13, 214); x.scale(1.05, 1.05); x.fillStyle = C.goldLt; x.beginPath();
    x.moveTo(-11, -12); x.quadraticCurveTo(-15, -2, -6, 8); x.quadraticCurveTo(3, 16, 12, 12); x.lineTo(8, 4); x.lineTo(3, 7); x.quadraticCurveTo(-3, 3, -6, -4); x.lineTo(-3, -8); x.closePath(); x.fill(); x.restore();
    x.fillStyle = "#FBF6EC"; x.font = '600 34px ' + BODY; x.fillText(PHONE, TX + 40, 226);

    x.textAlign = "center"; if ("letterSpacing" in x) x.letterSpacing = "9px";
    x.fillStyle = C.red; x.font = '700 40px ' + DISPLAY; var TG = "CASH · TRADE-IN · FINANCING"; x.fillText(TG, 540 + 4, 338);
    var tw = x.measureText(TG).width; if ("letterSpacing" in x) x.letterSpacing = "0px";
    x.fillStyle = gold(M, 0, 540 - tw / 2 - 24, 0); x.fillRect(M, 324, 540 - tw / 2 - 24 - M, 1.5);
    x.fillStyle = gold(540 + tw / 2 + 24, 0, W - M, 0); x.fillRect(540 + tw / 2 + 24, 324, W - M - (540 + tw / 2 + 24), 1.5);

    var bf = x.createLinearGradient(880, 1080, 1080, 940); bf.addColorStop(0, "#1A1313"); bf.addColorStop(1, "#3A1414");
    poly([W, 952, W, W, 868, W], bf); line([W, 952, 868, W], 1.5, gold(868, W, W, 952));
    line([0, 1000, 80, W], 1.5, gold(0, 1000, 80, W)); line([0, 1030, 50, W], 1, "rgba(156,110,47,.7)");

    var L = M, T = 372, PW = W - 2 * M, PH = 556;
    x.save(); x.shadowColor = "rgba(20,10,8,.28)"; x.shadowBlur = 26; x.shadowOffsetY = 10; x.fillStyle = "#fff"; x.fillRect(L, T, PW, PH); x.restore();
    x.save(); x.beginPath(); x.rect(L, T, PW, PH); x.clip();
    var s = Math.max(PW / photo.naturalWidth, PH / photo.naturalHeight), dw = photo.naturalWidth * s, dh = photo.naturalHeight * s;
    x.drawImage(photo, L + (PW - dw) / 2, T + (PH - dh) / 2, dw, dh);
    x.restore();
    x.lineWidth = 2; x.strokeStyle = gold(L, T, L + PW, T + PH); x.strokeRect(L - 10, T - 10, PW + 20, PH + 20);
    x.lineWidth = 1; x.strokeStyle = "rgba(156,110,47,.6)"; x.strokeRect(L - 16, T - 16, PW + 32, PH + 32);

    if (STAMP[car.status]) {
      var word = car.status.toUpperCase();
      x.save(); x.translate(L + PW / 2, T + PH / 2); x.rotate(-30 * Math.PI / 180);
      if ("letterSpacing" in x) x.letterSpacing = "14px";
      fitFont(x, word, "800", DISPLAY, 230, 820);
      x.textAlign = "center"; x.textBaseline = "middle"; x.lineJoin = "round";
      x.lineWidth = 12; x.strokeStyle = "rgba(255,255,255,.9)"; x.strokeText(word, 0, 0);
      x.globalAlpha = 0.92; x.fillStyle = STAMP[car.status]; x.fillText(word, 0, 0);
      x.restore();
    }

    var t = S.title(car); x.textAlign = "center"; x.textBaseline = "alphabetic"; x.fillStyle = C.ink;
    fitFont(x, t, "800", DISPLAY, 62, 760); x.fillText(t, 540, 1008);
    if ("letterSpacing" in x) x.letterSpacing = "4px";
    x.fillStyle = "#6A5E54"; x.font = '600 15px ' + BODY; var FT = "DEMO CONCEPT POST · OKS CARS AUTO FINANCING"; x.fillText(FT, 542, 1044);
    var fw = x.measureText(FT).width; if ("letterSpacing" in x) x.letterSpacing = "0px";
    x.fillStyle = "rgba(156,110,47,.7)"; x.fillRect(540 - fw / 2 - 70, 1039, 50, 1); x.fillRect(540 + fw / 2 + 20, 1039, 50, 1);

    var q = 0.92, blob = await toBlob(cv, q);
    while (blob.size > MAX_BYTES && q > 0.42) { q = Math.round((q - 0.06) * 100) / 100; blob = await toBlob(cv, q); }
    return { dataURL: await blobToDataURL(blob), bytes: blob.size, quality: q, width: cv.width, height: cv.height };
  }

  var PEN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="m13.5 6.5 4 4"/></svg>';
  var BIN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6"/></svg>';
  function refresh() {
    cars = S.merged(seed, S.load());
    $("[data-owner-count]").textContent = "(" + cars.length + ")";
    if (!cars.length) { list.innerHTML = '<li class="owner-list__loading">No cars yet. Add one above, or reset the demo data.</li>'; return; }
    list.innerHTML = cars.map(function (c) {
      var t = S.esc(S.title(c)), origin = c.seed ? (c.edited ? "Sample listing, edited here" : "Sample listing") : "Added in this browser";
      return '<li class="owner-car" data-id="' + S.esc(c.id) + '">' + S.cardArt(c, cardCfg) +
        '<div class="owner-car__foot"><div class="owner-car__text">' + S.specList(c) + '<p class="owner-car__origin">' + origin + (c.status ? "" : " · No status") + "</p></div>" +
        '<div class="owner-car__actions"><button type="button" class="icon-btn" data-edit aria-label="Edit ' + t + '">' + PEN + '</button>' +
        '<button type="button" class="icon-btn icon-btn--danger" data-delete aria-label="Delete ' + t + '">' + BIN + "</button></div></div></li>";
    }).join("");
  }
  function resetForm() {
    form.reset(); form.id.value = ""; form.condition.value = "Second-hand";
    $("[data-form-title]").textContent = "Add a car"; $("[data-submit-label]").textContent = "Save car and make post"; $("[data-cancel-edit]").hidden = true;
  }
  function startEdit(c) {
    resetForm(); form.id.value = c.id; form.year.value = c.year || ""; form.make.value = c.make || ""; form.model.value = c.model || ""; form.status.value = c.status || "";
    form.condition.value = c.condition === "Brand-new" ? "Brand-new" : "Second-hand";
    form.body.value = c.body || ""; form.trans.value = c.trans || ""; form.fuel.value = c.fuel || "";
    form.features.value = (Array.isArray(c.features) ? c.features : (c.extra ? [c.extra] : [])).join(", ");
    $("[data-form-title]").textContent = "Edit " + S.title(c); $("[data-submit-label]").textContent = "Save changes and remake post"; $("[data-cancel-edit]").hidden = false;
    makePost(c).catch(function () {});
    say("Editing " + S.title(c) + ". Choose a new photo only if you want to replace it."); form.year.focus();
  }
  async function makePost(car) {
    var out = await drawPost(await loadImg(photoFor(car)), car);
    post = { url: out.dataURL, name: ("okscars-" + S.title(car)).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-+$/, "") + ".jpg" };
    preview.src = out.dataURL; preview.alt = "Social post preview for the " + S.title(car); preview.hidden = false; $("[data-preview-empty]").hidden = true; dl.hidden = false;
    $("[data-preview-meta]").textContent = "1080 × 1080 JPG, " + Math.round(out.bytes / 1024) + " KB (quality " + Math.round(out.quality * 100) + "). Made in your browser; not saved.";
    return out;
  }
  dl.addEventListener("click", function () {
    if (!post) return;
    var a = document.createElement("a"); a.href = post.url; a.download = post.name; document.body.appendChild(a); a.click(); a.remove();
  });

  list.addEventListener("click", function (e) {
    var btn = e.target.closest("button"); if (!btn) return;
    var id = btn.closest("[data-id]").getAttribute("data-id"), c = cars.filter(function (k) { return k.id === id; })[0]; if (!c) return;
    if (btn.hasAttribute("data-edit")) { startEdit(c); return; }
    if (!window.confirm("Delete the " + S.title(c) + "? This only changes the demo data in this browser.")) return;
    var st = S.load(); delete st.over[id]; if (c.seed && st.tomb.indexOf(id) < 0) st.tomb.push(id);
    var err = S.save(st); if (err) { say("Couldn't save: browser storage is unavailable.", true); return; }
    if (form.id.value === id) resetForm();
    refresh(); say("Deleted the " + S.title(c) + ".");
  });
  $("[data-cancel-edit]").addEventListener("click", function () { resetForm(); say("Editing cancelled."); });
  $("[data-reset]").addEventListener("click", function () {
    if (!window.confirm("Reset the demo data? This removes every car you added, edited or deleted in this browser.")) return;
    try { localStorage.removeItem(S.KEY); } catch (e) {  }
    resetForm(); preview.hidden = true; dl.hidden = true; post = null; $("[data-preview-empty]").hidden = false; $("[data-preview-meta]").textContent = "";
    refresh(); say("Demo data reset to the sample listings.");
  });

  var busy = false;
  form.addEventListener("submit", async function (e) {
    e.preventDefault(); if (busy) return;
    var id = form.id.value, prev = id ? cars.filter(function (k) { return k.id === id; })[0] : null;
    if (!validate(!!prev)) { say("Please fix the highlighted fields.", true); return; }
    busy = true; say("Making the post…");
    try {
      var f = form.photo.files[0], up = null;
      if (f) {
        var photo;
        try { photo = await loadImg(await readFile(f)); } catch (err) { setErr("photo", "That file couldn't be read as an image. Try another photo."); form.photo.focus(); throw null; }
        if (photo.naturalWidth < 400 || photo.naturalHeight < 300) { setErr("photo", "That photo is too small. Use one at least 400 × 300 pixels."); form.photo.focus(); throw null; }
        up = await compressUpload(photo);
      }
      var car = { year: +form.year.value, make: form.make.value.trim(), model: form.model.value.trim(), status: S.cleanStatus(form.status.value) };
      car.name = car.make + " " + car.model;
      car.condition = form.condition.value === "Brand-new" ? "Brand-new" : "Second-hand";
      car.body = form.body.value; car.trans = form.trans.value; car.fuel = form.fuel.value;
      car.features = form.features.value.split(",").map(function (f) { return f.trim().replace(/\s+/g, " ").slice(0, 40); }).filter(Boolean).slice(0, 6);
      var st = S.load(), newId = id || "local-" + Date.now().toString(36), had = st.over[newId];
      var rec = Object.assign({}, had || {}, car, { id: newId, updated: Date.now() });
      delete rec.image; delete rec.source; delete rec.extra;
      var base = prev && prev.seed ? seed.filter(function (k) { return k.id === newId; })[0] : null;
      if (base) {
        Object.keys(car).forEach(function (k) {
          var sv = base[k] == null ? "" : base[k], nv = car[k] == null ? "" : car[k];
          if (JSON.stringify(sv) === JSON.stringify(nv)) delete rec[k];
        });
      }
      if (up) rec.upload = up.url;
      if (!prev) rec.created = Date.now();
      if (base && Object.keys(rec).every(function (k) { return k === "id" || k === "updated"; })) delete st.over[newId];
      else st.over[newId] = rec;
      var err = S.save(st);
      if (err) {
        var full = err && (err.name === "QuotaExceededError" || err.code === 22 || err.code === 1014);
        say(full ? "Browser storage is full, so this car wasn't saved. Delete a car or use Reset demo data, then try again." : "Couldn't save: browser storage is unavailable.", true);
        throw null;
      }
      refresh(); resetForm();
      var saved = cars.filter(function (k) { return k.id === newId; })[0];
      say((prev ? "Saved changes to the " : "Saved the ") + S.title(car) + (up ? " (photo stored at " + Math.round(up.bytes / 1024) + " KB)" : "") + ". It shows on the Cars for sale page in this browser. Making the social post…");
      await makePost(saved);
      say((prev ? "Saved changes to the " : "Saved the ") + S.title(car) + (up ? " (photo stored at " + Math.round(up.bytes / 1024) + " KB)" : "") + ". It shows on the Cars for sale page in this browser, and its post is ready to download.");
    } catch (err) { if (err) { console.error(err); say("Something went wrong making the post. Try another photo.", true); } }
    busy = false;
  });

  S.fetchSeed().then(function (s) { seed = s; refresh(); }).catch(function () { seed = []; refresh(); say("Couldn't load the sample listings (data/cars.json). Showing only cars saved in this browser.", true); });
})();
