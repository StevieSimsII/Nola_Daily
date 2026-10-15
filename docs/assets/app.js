(function () {
  "use strict";

  var REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  initTheme();
  initMenu();
  initScrollHeader();

  fetch("data/digest.json", { cache: "no-store" })
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(render)
    .catch(function (err) {
      var el = document.getElementById("digest-loading");
      if (el) {
        el.innerHTML =
          "<p>The daily edition couldn’t be loaded (" +
          esc(String(err.message || err)) +
          "). Try a refresh, or check back after the morning run.</p>";
      }
    });

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function safeUrl(u) {
    u = String(u || "").trim();
    return /^https?:\/\//i.test(u) ? u : "";
  }

  function cleanTitle(title, source) {
    var t = String(title || "").trim();
    var src = String(source || "").trim();
    var seps = [" - ", " | ", " – ", " — "];
    for (var i = 0; i < seps.length; i++) {
      var sep = seps[i];
      if (t.indexOf(sep) === -1) continue;
      var parts = t.split(sep);
      var right = parts[parts.length - 1].trim();
      var looksLikeSource =
        (src && right.toLowerCase() === src.toLowerCase()) ||
        (/^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(right) && right.length < 40);
      if (looksLikeSource) return parts.slice(0, -1).join(sep).trim();
    }
    return t;
  }

  function render(d) {
    var sections = d.sections || [];
    var nav = document.getElementById("topnav");
    nav.innerHTML =
      sections
        .map(function (s) {
          return '<a href="#' + esc(s.slug) + '">' + esc(s.title) + "</a>";
        })
        .join("") + '<a href="#forecast">Forecast</a>';

    document.getElementById("hero-lead").textContent = d.lead || "";
    var total = sections.reduce(function (n, s) {
      return n + (s.items || []).length;
    }, 0);
    var events = sections.filter(function (s) {
      return s.slug === "events";
    })[0];
    document.getElementById("hero-meta").innerHTML =
      "<span>" +
      esc(d.generated_label || "") +
      "</span><span>" +
      total +
      " stories</span><span>" +
      (events && events.items ? events.items.length : 0) +
      " event picks</span>";
    document.getElementById("topbar-date").textContent = (d.generated_label || "").split(" at ")[0];
    document.getElementById("footer-generated").textContent =
      "Edition generated " + (d.generated_label || "") + " · refreshed every morning.";

    renderHeroWeather(d.current_forecast);

    var main = document.getElementById("digest");
    main.innerHTML = sections
      .map(function (s, i) {
        return sectionHtml(s, i);
      })
      .join("");

    document.getElementById("forecast-strip").innerHTML =
      (d.seven_day_forecast || []).map(forecastHtml).join("") ||
      '<p class="empty-note">The NOAA feed was unavailable this run.</p>';

    if ((d.source_notes || []).length) {
      document.getElementById("source-notes").innerHTML =
        '<section class="notes"><p class="section-eyebrow">Run notes</p><ul>' +
        d.source_notes
          .map(function (n) {
            return "<li>" + esc(n) + "</li>";
          })
          .join("") +
        "</ul></section>";
    }

    closeMenu();
  }

  function sectionHtml(s, i) {
    var items = s.items || [];
    var isEvents = s.slug === "events";
    var body;
    var index = String(i + 1).padStart(2, "0");

    if (!items.length) {
      body = '<p class="empty-note">' + esc(s.empty_message || "Nothing fresh this run.") + "</p>";
    } else if (isEvents) {
      body = '<div class="event-list">' + items.map(eventHtml).join("") + "</div>";
    } else {
      var lead = items[0];
      var rest = items.slice(1);
      body =
        featureHtml(lead) +
        (rest.length ? '<div class="story-grid">' + rest.map(storyHtml).join("") + "</div>" : "");
    }

    return (
      '<section class="section" id="' +
      esc(s.slug) +
      '">' +
      '<div class="section-head">' +
      '<p class="section-eyebrow">' +
      index +
      " — " +
      esc(s.title) +
      "</p>" +
      '<h2 class="section-title">' +
      esc(s.title) +
      "</h2>" +
      '<p class="section-desc">' +
      esc(s.description || "") +
      "</p></div>" +
      body +
      "</section>"
    );
  }

  function metaHtml(bits) {
    return bits
      .filter(Boolean)
      .map(function (b) {
        return "<span>" + esc(b) + "</span>";
      })
      .join("");
  }

  function isRedundantSummary(summary, title) {
    var s = String(summary || "").trim();
    var t = String(title || "").trim();
    if (!s) return true;
    if (!t) return false;
    var sNorm = s.toLowerCase();
    var tNorm = t.toLowerCase();
    if (sNorm === tNorm || sNorm.indexOf(tNorm) === 0) return true;
    if (sNorm.indexOf("read the latest") === 0) return true;
    return false;
  }

  function summaryHtml(cls, summary, title) {
    if (isRedundantSummary(summary, title)) return "";
    return '<p class="' + cls + '">' + esc(summary) + "</p>";
  }

  function featureHtml(it) {
    var url = safeUrl(it.url);
    var title = cleanTitle(it.title, it.source);
    return (
      '<article class="feature">' +
      '<p class="kicker">' +
      esc(it.eyebrow || it.source || "") +
      "</p>" +
      "<h3><a href=\"" +
      esc(url) +
      '" target="_blank" rel="noreferrer noopener">' +
      esc(title) +
      "</a></h3>" +
      summaryHtml("feature-summary", it.summary, title) +
      '<div class="meta">' +
      metaHtml([it.published, it.source, it.location]) +
      "</div></article>"
    );
  }

  function storyHtml(it) {
    var url = safeUrl(it.url);
    var title = cleanTitle(it.title, it.source);
    return (
      '<article class="story">' +
      '<p class="kicker">' +
      esc(it.source || it.eyebrow || "") +
      "</p>" +
      "<h3><a href=\"" +
      esc(url) +
      '" target="_blank" rel="noreferrer noopener">' +
      esc(title) +
      "</a></h3>" +
      summaryHtml("story-summary", it.summary, title) +
      '<div class="meta">' +
      metaHtml([it.published]) +
      "</div></article>"
    );
  }

  function eventHtml(it) {
    var url = safeUrl(it.url);
    var cal = safeUrl(it.calendar_url);
    return (
      '<article class="event">' +
      '<div class="event-when">' +
      esc(it.published || "See listing") +
      "</div>" +
      '<div class="event-body">' +
      "<h3><a href=\"" +
      esc(url) +
      '" target="_blank" rel="noreferrer noopener">' +
      esc(it.title) +
      "</a></h3>" +
      '<div class="meta">' +
      metaHtml([it.location, it.source]) +
      "</div></div>" +
      '<div class="event-actions">' +
      '<a class="btn btn-small btn-primary" href="' +
      esc(url) +
      '" target="_blank" rel="noreferrer noopener">Listing</a>' +
      (cal
        ? '<a class="btn btn-small btn-ghost" href="' +
          esc(cal) +
          '" target="_blank" rel="noreferrer noopener">Calendar</a>'
        : "") +
      "</div></article>"
    );
  }

  function weatherIcon(sf) {
    var t = String(sf || "").toLowerCase();
    if (t.indexOf("thunder") > -1) return boltIcon();
    if (/snow|sleet|ice/.test(t)) return snowIcon();
    if (/rain|shower|drizzle/.test(t)) return rainIcon();
    if (/fog|mist|haze/.test(t)) return fogIcon();
    if (/cloud|partly/.test(t)) return cloudIcon();
    if (/sunny|clear/.test(t)) return sunIcon();
    return moonIcon();
  }

  function sunIcon() {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M3 12h2M19 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
  }
  function moonIcon() {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4 7 7 0 0 0 20 14.5Z"/></svg>';
  }
  function cloudIcon() {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M7 18h10a4 4 0 0 0 .3-8 6 6 0 0 0-11.4 1.6A3.5 3.5 0 0 0 7 18Z"/></svg>';
  }
  function rainIcon() {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M7 16h10a4 4 0 0 0 .3-8 6 6 0 0 0-11.4 1.6A3.5 3.5 0 0 0 7 16Z"/><path d="M8.5 19.5 7.5 22M12 19.5 11 22M15.5 19.5 14.5 22"/></svg>';
  }
  function boltIcon() {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M13 3 6 14h6l-1 7 7-11h-6l1-7Z"/></svg>';
  }
  function snowIcon() {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M12 4v16M6 7l12 10M18 7 6 17"/></svg>';
  }
  function fogIcon() {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M4 10h16M6 14h12M8 18h8"/></svg>';
  }

  function renderHeroWeather(w) {
    var el = document.getElementById("hero-weather");
    if (!w) {
      el.innerHTML = '<p class="hw-label">Current weather</p><p>Unavailable this run.</p>';
      return;
    }
    el.innerHTML =
      '<p class="hw-label">' +
      esc(w.name || "Now") +
      '</p><div class="hw-main"><span class="hw-icon">' +
      weatherIcon(w.short_forecast) +
      '</span><span class="hw-temp">' +
      esc(w.temperature) +
      "°<small>" +
      esc(w.temperature_unit || "F") +
      "</small></span></div><p class=\"hw-desc\">" +
      esc(w.short_forecast || "") +
      '</p><p class="hw-wind">' +
      esc(((w.wind_direction || "") + " " + (w.wind_speed || "")).trim()) +
      "</p>";
  }

  function forecastHtml(p) {
    return (
      '<article class="fc-card">' +
      '<p class="fc-name">' +
      esc(p.name) +
      '</p><div class="fc-icon">' +
      weatherIcon(p.short_forecast) +
      '</div><p class="fc-temp">' +
      esc(p.temperature) +
      "°</p><p class=\"fc-desc\">" +
      esc(p.short_forecast || "") +
      "</p></article>"
    );
  }

  function initTheme() {
    var btn = document.getElementById("theme-toggle");
    var meta = document.getElementById("theme-color");
    function apply(theme) {
      document.documentElement.dataset.theme = theme;
      try {
        localStorage.setItem("nola-theme", theme);
      } catch (e) {}
      btn.setAttribute("aria-label", theme === "dark" ? "Switch to light theme" : "Switch to dark theme");
      if (meta) meta.setAttribute("content", theme === "light" ? "#f3f1eb" : "#07090d");
    }
    apply(document.documentElement.dataset.theme || "dark");
    btn.addEventListener("click", function () {
      apply(document.documentElement.dataset.theme === "light" ? "dark" : "light");
    });
  }

  function initMenu() {
    var btn = document.getElementById("menu-toggle");
    var nav = document.getElementById("topnav");
    btn.addEventListener("click", function () {
      var open = !nav.classList.contains("is-open");
      nav.classList.toggle("is-open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });
    nav.addEventListener("click", function (e) {
      if (e.target.tagName === "A") closeMenu();
    });
  }

  function closeMenu() {
    var btn = document.getElementById("menu-toggle");
    var nav = document.getElementById("topnav");
    nav.classList.remove("is-open");
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-label", "Open menu");
  }

  function initScrollHeader() {
    var topbar = document.getElementById("topbar");
    var ticking = false;
    function frame() {
      topbar.classList.toggle("is-scrolled", (window.scrollY || 0) > 8);
      ticking = false;
    }
    window.addEventListener(
      "scroll",
      function () {
        if (REDUCED) {
          frame();
          return;
        }
        if (!ticking) {
          ticking = true;
          requestAnimationFrame(frame);
        }
      },
      { passive: true }
    );
    frame();
  }
})();
