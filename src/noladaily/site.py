from __future__ import annotations

import json
from html import escape
from pathlib import Path

from noladaily.models import DailyDigest, DigestItem, DigestSection, ForecastPeriod


def write_site(digest: DailyDigest, output_dir: Path, data_path: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(digest.to_dict(), indent=2), encoding="utf-8")
    (output_dir / "index.html").write_text(render_index(digest), encoding="utf-8")
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")


def render_index(digest: DailyDigest) -> str:
    total_items = sum(len(section.items) for section in digest.sections)
    event_count = len(next((section.items for section in digest.sections if section.slug == "events"), []))
    nav_links = "".join(
        f'<a class="nav-link" href="#{escape(section.slug)}"><span>{escape(section.title)}</span><strong>{len(section.items)}</strong></a>'
        for section in digest.sections
    )
    nav_links += f'<a class="nav-link" href="#forecast"><span>Forecast</span><strong>{len(digest.seven_day_forecast)}</strong></a>'
    tag_buttons = "".join(
        f'<button class="tag-pill" type="button" data-filter="{escape(section.slug)}">{escape(section.title)}</button>'
        for section in digest.sections
    )
    sections_html = "\n".join(render_section(section) for section in digest.sections)
    forecast_html = "\n".join(render_forecast(period) for period in digest.seven_day_forecast)
    source_note_block = render_source_notes(digest)

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Nola Daily</title>
    <meta name="description" content="Daily New Orleans news, dining, entertainment, live music, events, and weather.">
    <meta name="theme-color" content="#0d1117">
    <link rel="stylesheet" href="assets/styles.css">
  </head>
  <body>
    <div class="app" id="top">
      <aside class="sidebar">
        <div class="sidebar-header">
          <a class="brand" href="#top" aria-label="Nola Daily home">
            <span class="brand-mark">ND</span>
            <span>
              <strong>Nola Daily</strong>
              <em>New Orleans refreshed daily.</em>
            </span>
          </a>
          <div class="count">{total_items} links &middot; {event_count} events</div>
        </div>
        <div class="search-wrap">
          <input id="search" type="search" placeholder="Search Nola Daily..." autocomplete="off">
        </div>
        <div class="tags-wrap" id="filters">
          <button class="tag-pill active" type="button" data-filter="all">All</button>
          {tag_buttons}
        </div>
        <nav class="nav-list" aria-label="Section navigation">
          {nav_links}
        </nav>
        {render_current_forecast(digest.current_forecast)}
        <div class="sidebar-footer">
          <span>{escape(digest.generated_label)}</span>
          <a href="https://steviesimsii.github.io/Second_Brain/" target="_blank" rel="noopener">Second Brain</a>
        </div>
      </aside>

      <main class="main">
        <section class="welcome">
          <div class="eyebrow">Daily digest</div>
          <h1>The city in one focused scan.</h1>
          <p>{escape(digest.lead)}</p>
          <div class="hero-stats" aria-label="Digest summary">
            <span>{escape(digest.generated_label)}</span>
            <span>{total_items} fresh links</span>
            <span>{event_count} event picks</span>
          </div>
        </section>

        {sections_html}

        <section class="section" id="forecast">
          <div class="section-header">
            <div>
              <div class="eyebrow">Weather</div>
              <h2>7 day forecast</h2>
              <p>A quick local weather scan for planning the week ahead.</p>
            </div>
            <div class="section-count">{len(digest.seven_day_forecast)} days</div>
          </div>
          <div class="forecast-grid">
            {forecast_html}
          </div>
        </section>

        {source_note_block}

        <footer class="footer">
          <span>Built for a calm, readable daily check-in from your phone or laptop.</span>
          <a href="#top">Back to top</a>
        </footer>
      </main>
    </div>
    <script>
      const search = document.getElementById("search");
      const filters = document.getElementById("filters");
      const cards = Array.from(document.querySelectorAll("[data-search]"));
      let activeFilter = "all";

      function applyFilters() {{
        const query = (search?.value || "").trim().toLowerCase();
        let visible = 0;
        cards.forEach((card) => {{
          const matchesQuery = !query || card.dataset.search.includes(query);
          const matchesFilter = activeFilter === "all" || card.dataset.section === activeFilter;
          const show = matchesQuery && matchesFilter;
          card.hidden = !show;
          if (show) visible += 1;
        }});
        document.body.classList.toggle("is-filtering", Boolean(query) || activeFilter !== "all");
        document.documentElement.style.setProperty("--visible-count", `"${{visible}} results"`);
      }}

      search?.addEventListener("input", applyFilters);
      filters?.addEventListener("click", (event) => {{
        const button = event.target.closest("[data-filter]");
        if (!button) return;
        activeFilter = button.dataset.filter;
        filters.querySelectorAll(".tag-pill").forEach((pill) => pill.classList.toggle("active", pill === button));
        applyFilters();
      }});
    </script>
  </body>
</html>
"""


def render_source_notes(digest: DailyDigest) -> str:
    if not digest.source_notes:
        return ""

    source_notes = "".join(f"<li>{escape(note)}</li>" for note in digest.source_notes)
    return f"""
        <section class="section section-notes" id="source-notes">
          <div class="section-header">
            <div>
              <div class="eyebrow">Run Notes</div>
              <h2>Source refresh notes</h2>
              <p>Some providers were unavailable or partial during this build.</p>
            </div>
          </div>
          <div class="section-empty source-notes">
            <ul>{source_notes}</ul>
          </div>
        </section>
    """


def render_section(section: DigestSection) -> str:
    cards = "\n".join(render_card(item, section.slug) for item in section.items)
    empty = f'<div class="section-empty"><p>{escape(section.empty_message)}</p></div>' if not section.items else ""
    body = cards or empty
    return f"""
        <section class="section" id="{escape(section.slug)}">
          <div class="section-header">
            <div>
              <div class="eyebrow">Fresh picks</div>
              <h2>{escape(section.title)}</h2>
              <p>{escape(section.description)}</p>
            </div>
            <div class="section-count">{_count_label(len(section.items))}</div>
          </div>
          <div class="story-grid">
            {body}
          </div>
        </section>
    """


def render_card(item: DigestItem, section_slug: str) -> str:
    if item.calendar_url:
        return render_event_card(item, section_slug)

    meta_bits = [bit for bit in [item.published, item.source, item.location] if bit]
    meta_html = "".join(f"<span>{escape(bit)}</span>" for bit in meta_bits)
    search_text = _search_text(item)
    return f"""
      <article class="story-card" data-section="{escape(section_slug)}" data-search="{search_text}">
        <div class="story-kicker">{escape(item.eyebrow or item.source)}</div>
        <h3><a class="story-link" href="{escape(item.url)}" target="_blank" rel="noreferrer">{escape(item.title)}</a></h3>
        <p class="story-summary">{escape(item.summary)}</p>
        <div class="card-meta">{meta_html}</div>
        <div class="card-actions">
          <a class="card-action ghost" href="{escape(item.url)}" target="_blank" rel="noreferrer">Read story</a>
        </div>
      </article>
    """


def render_event_card(item: DigestItem, section_slug: str) -> str:
    meta_bits = [bit for bit in [item.published, item.location, item.source] if bit]
    meta_html = "".join(f"<span>{escape(bit)}</span>" for bit in meta_bits)
    calendar_action = (
        f'<a class="card-action secondary" href="{escape(item.calendar_url)}" target="_blank" rel="noreferrer">Add to calendar</a>'
        if item.calendar_url
        else ""
    )
    return f"""
      <article class="story-card story-card-event" data-section="{escape(section_slug)}" data-search="{_search_text(item)}">
        <div class="story-kicker">{escape(item.eyebrow or item.source)}</div>
        <h3><a class="story-link" href="{escape(item.url)}" target="_blank" rel="noreferrer">{escape(item.title)}</a></h3>
        <p class="story-summary">{escape(item.summary)}</p>
        <div class="card-meta">{meta_html}</div>
        <div class="card-actions">
          <a class="card-action primary" href="{escape(item.url)}" target="_blank" rel="noreferrer">Open event</a>
          {calendar_action}
        </div>
      </article>
    """


def render_forecast(period: ForecastPeriod) -> str:
    emoji = _weather_emoji(period.short_forecast)
    return f"""
      <article class="forecast-card">
        <div class="forecast-icon" aria-hidden="true">{escape(emoji)}</div>
        <div class="forecast-copy">
          <h3>{escape(period.name)}</h3>
          <div class="forecast-temp">{period.temperature}&deg;{escape(period.temperature_unit)}</div>
          <p>{escape(period.short_forecast)}</p>
          <p class="card-meta"><span>{escape(period.wind_direction)} {escape(period.wind_speed)}</span></p>
        </div>
      </article>
    """


def render_current_forecast(period: ForecastPeriod | None) -> str:
    if period is None:
        return """
        <aside class="weather-panel weather-panel-empty">
          <div class="eyebrow">Current weather</div>
          <h2>Forecast unavailable</h2>
          <p>The NOAA feed did not return the current conditions during this run.</p>
        </aside>
        """

    emoji = _weather_emoji(period.short_forecast)
    return f"""
        <aside class="weather-panel">
          <div class="eyebrow">Current weather</div>
          <div class="weather-row">
            <div class="weather-icon" aria-hidden="true">{escape(emoji)}</div>
            <div>
              <h2>{escape(period.name)}</h2>
              <div class="weather-temp">{period.temperature}&deg;{escape(period.temperature_unit)}</div>
            </div>
          </div>
          <p>{escape(period.short_forecast)}</p>
          <div class="weather-meta">
            <span>{escape(period.wind_direction)} {escape(period.wind_speed)}</span>
          </div>
        </aside>
    """


def _search_text(item: DigestItem) -> str:
    return escape(" ".join([item.title, item.summary, item.source, item.eyebrow, item.location]).lower(), quote=True)


def _count_label(count: int) -> str:
    noun = "link" if count == 1 else "links"
    return f"{count} {noun}"


def _weather_emoji(short_forecast: str) -> str:
    lowered = short_forecast.lower()
    if "thunder" in lowered:
        return "\u26c8\ufe0f"
    if "snow" in lowered or "sleet" in lowered or "ice" in lowered:
        return "\u2744\ufe0f"
    if "rain" in lowered or "showers" in lowered or "drizzle" in lowered:
        return "\U0001f327\ufe0f"
    if "fog" in lowered or "mist" in lowered or "haze" in lowered:
        return "\U0001f32b\ufe0f"
    if "wind" in lowered or "breezy" in lowered:
        return "\U0001f4a8"
    if "cloudy" in lowered or "partly sunny" in lowered or "partly cloudy" in lowered:
        return "\u26c5"
    if "sunny" in lowered or "clear" in lowered:
        return "\u2600\ufe0f"
    return "\U0001f324\ufe0f"
