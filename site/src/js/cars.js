/* Oks Cars demo: listing store. Seed = data/cars.json (public). Owner-mode changes live ONLY in this browser's
   localStorage under one key: { over: {id: fields}, tomb: [deleted seed ids] }. No backend, nothing is uploaded. */
(function () {
  "use strict";
  var KEY = "okscars-demo-cars-v1";
  var esc = function (s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (ch) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]; }); };
  var STATUSES = ["Reserved", "Sold"];                       // blank = no badge / no stamp
  function cleanStatus(s) { return STATUSES.indexOf(s) >= 0 ? s : ""; }
  function load() {
    try { var d = JSON.parse(localStorage.getItem(KEY) || "{}"); return { over: d.over || {}, tomb: d.tomb || [] }; }
    catch (e) { return { over: {}, tomb: [] }; }
  }
  function save(st) { try { localStorage.setItem(KEY, JSON.stringify(st)); return null; } catch (e) { return e; } }
  function isEmpty(st) { return !st.tomb.length && !Object.keys(st.over).length; }
  function title(c) { return [c.year, c.make, c.model].filter(Boolean).join(" "); }
  function merged(seed, st) {
    var ids = {}, seedOut = [], local = [];
    seed.forEach(function (s) {
      ids[s.id] = 1;
      if (st.tomb.indexOf(s.id) >= 0) return;
      var o = st.over[s.id];
      seedOut.push(Object.assign({}, s, o || {}, { seed: true, edited: !!o }));
    });
    Object.keys(st.over).forEach(function (id) {
      if (ids[id] || st.tomb.indexOf(id) >= 0) return;
      local.push(Object.assign({}, st.over[id], { seed: false, edited: false }));
    });
    local.sort(function (a, b) { return (b.created || 0) - (a.created || 0); });   // newest owner posts first
    return local.concat(seedOut).map(function (c) { c.status = cleanStatus(c.status); return c; });
  }
  var seedPromise = null;
  function fetchSeed() {
    if (!seedPromise) seedPromise = fetch("data/cars.json", { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error("cars.json " + r.status); return r.json();
    }).then(function (d) { return (d.cars || []).map(function (c) { c.status = cleanStatus(c.status); return c; }); });
    return seedPromise;
  }
  // Shared HTML/CSS card art: photo as the cover background, logo + phone + stamp (Reserved/Sold only) + title as real text.
  function cardArt(c, o) {
    var t = esc(title(c)), hid = o.headingId ? ' id="' + esc(o.headingId) + '"' : "", tag = o.tag || "h3", img;
    if (c.upload) img = '<img class="car-card__photo" src="' + esc(c.upload) + '" width="600" height="450" alt="Photo of the ' + t + '" decoding="async">';
    else img = '<img class="car-card__photo" src="' + esc(c.img) + '" srcset="' + esc(c.img) + " 600w, " + esc(c.img2x) + ' 1200w" sizes="' + (o.sizes || "(min-width: 1040px) 380px, (min-width: 680px) 46vw, 92vw") + '" width="600" height="450" alt="' + esc(c.alt || "Photo of the " + title(c)) + '" loading="lazy" decoding="async">';
    var stamp = c.status ? '<p class="car-card__stamp car-card__stamp--' + c.status.toLowerCase() + '"><span class="visually-hidden">Status: </span>' + esc(c.status) + "</p>" : "";
    var badge = c.upload ? "Owner's photo, saved in this browser only" : (o.badge || "");
    return '<div class="listing__art car-card">' + img +
      '<div class="car-card__top"><img class="car-card__logo" src="' + esc(o.logo) + '" width="40" height="40" alt="Oks Cars logo" decoding="async"><span class="car-card__phone">' + esc(o.phone) + '</span><span class="badge-sample">' + (c.upload ? "Owner demo" : "Sample listing") + "</span></div>" + stamp +
      '<div class="car-card__bottom">' + (badge ? '<span class="ph-badge image-badge">' + esc(badge) + "</span>" : "") + "<" + tag + ' class="car-card__title"' + hid + ">" + t + "</" + tag + "></div></div>";
  }
  // Dot-separated spec line: condition, body type, transmission, fuel, then features (array; legacy "extra" string too).
  function specList(c) {
    var f = Array.isArray(c.features) ? c.features : (c.extra ? [c.extra] : []);
    var items = [c.condition, c.body, c.trans, c.fuel].concat(f).filter(function (x) { return x && String(x).trim(); });
    return items.length ? '<ul class="listing__specs" aria-label="Details">' + items.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul>" : "";
  }
  function statusBadge(s) { return s ? '<span class="status-badge status-badge--' + s.toLowerCase() + '">' + esc(s) + "</span>" : ""; }
  window.OksCars = { KEY: KEY, esc: esc, load: load, save: save, isEmpty: isEmpty, merged: merged, fetchSeed: fetchSeed, title: title, statusBadge: statusBadge, cardArt: cardArt, specList: specList, cleanStatus: cleanStatus };

  // ---------- cars-for-sale.html: re-render the cards from seed + local overrides ----------
  var wrap = document.querySelector("[data-listings]");
  if (!wrap) return;
  var st = load();
  if (isEmpty(st)) return;          // server-rendered seed cards are already identical: no DOM swap, no layout shift
  fetchSeed().then(function (seed) {
    var cars = merged(seed, st), badge = wrap.getAttribute("data-badge"), fb = wrap.getAttribute("data-fb");
    var cfg = { badge: badge, logo: wrap.getAttribute("data-logo"), phone: wrap.getAttribute("data-phone") };
    wrap.innerHTML = cars.map(function (c, i) {
      var t = title(c), hid = "l-" + c.id;
      return '<article class="listing reveal is-in" style="--d: ' + ((i % 3) * 0.08) + 's" data-id="' + esc(c.id) + '" data-condition="' + esc(c.condition || "") + '" data-body="' + esc(c.body || "") + '" aria-labelledby="' + esc(hid) + '">' +
        cardArt(c, Object.assign({ headingId: hid }, cfg)) +
        '<div class="listing__body">' + specList(c) +
        '<p class="listing__price">Ask for price</p><div class="btn-row"><a class="btn btn--gold btn--sm" href="financing.html#calc">Estimate monthly</a><a class="btn btn--ghost btn--sm" href="' + esc(fb) + '" target="_blank" rel="noopener">Inquire<span class="visually-hidden"> about the ' + esc(t) + " on Facebook (opens in a new tab)</span></a></div></div></article>";
    }).join("");
    var count = document.querySelector("[data-filter-count]");
    if (count) count.textContent = "Showing " + cars.length + " sample listing" + (cars.length === 1 ? "" : "s");
    document.querySelectorAll("[data-filters] .chip").forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-value") === "all" ? "true" : "false"); });
    document.dispatchEvent(new CustomEvent("okscars:listings"));
  }).catch(function () { /* keep the server-rendered seed cards */ });
})();
