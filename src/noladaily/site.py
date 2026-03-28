from __future__ import annotations

import json
from html import escape
from pathlib import Path

from noladaily.models import DailyDigest, DigestSection, ForecastPeriod


def write_site(digest: DailyDigest, output_dir: Path, data_path: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(digest.to_dict(), indent=2), encoding="utf-8")
    (output_dir / "index.html").write_text(render_index(digest), encoding="utf-8")
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")


def render_index(digest: DailyDigest) -> str:
    nav_links = "".join(
        f'<a href="#{escape(section.slug)}">{escape(section.title)}</a>' for section in digest.sections
    )

    sections_html = "\n".join(render_section(section) for section in digest.sections)
    forecast_html = "\n".join(render_forecast(period) for period in digest.seven_day_forecast)
    source_notes = "".join(f"<li>{escape(note)}</li>" for note in digest.source_notes)
    source_note_block = (
        f'<section class="section"><div class="section-empty"><p>Some sources had trouble during this run.</p><ul>{source_notes}</ul></div></section>'
        if digest.source_notes
        else ""
    )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Nola Daily</title>
    <meta name="description" content="Daily New Orleans news, dining, entertainment, live music, events, and weather.">
    <meta name="theme-color" content="#143a32">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Manrope:wght@400;500;600;700;800&family=Cormorant+Garamond:wght@500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="assets/styles.css">
  </head>
  <body>
    <header class="topbar">
      <div class="topbar-inner">
        <a class="brand" href="#top">
          <span class="brand-copy">
            <strong>Nola Daily</strong>
            <span>New Orleans refreshed daily.</span>
          </span>
        </a>
        <nav class="topbar-links" aria-label="Section navigation">
          {nav_links}
        </nav>
      </div>
    </header>

    <main class="page-shell" id="top">
      {sections_html}

      <section class="section" id="forecast">
        <div class="section-header">
          <h2>7 Day Forecast</h2>
          <p>NOAA outlook for New Orleans, optimized for quick daily planning.</p>
        </div>
        <div class="grid forecast-grid">
          {forecast_html}
        </div>
      </section>

      {source_note_block}

      <footer class="footer">
        <div class="footer-copy">Built for a light, readable daily check-in from your phone.</div>
        <a href="#top">Back to top</a>
      </footer>
    </main>
  </body>
</html>
"""


def render_section(section: DigestSection) -> str:
    cards = "\n".join(render_card(item) for item in section.items)
    empty = f'<div class="section-empty"><p>{escape(section.empty_message)}</p></div>' if not section.items else ""
    body = cards or empty
    return f"""
      <section class="section" id="{escape(section.slug)}">
        <div class="section-header">
          <h2>{escape(section.title)}</h2>
          <p>{escape(section.description)}</p>
        </div>
        <div class="grid story-grid">
          {body}
        </div>
      </section>
    """


def render_card(item) -> str:
    if item.calendar_url:
        return render_event_card(item)

    meta_bits = [bit for bit in [item.source, item.location, item.published] if bit]
    meta_html = "".join(f"<span>{escape(bit)}</span>" for bit in meta_bits)
    return f"""
      <article class="story-card">
        <div class="story-kicker">{escape(item.eyebrow or item.source)}</div>
        <h3><a class="story-link" href="{escape(item.url)}" target="_blank" rel="noreferrer">{escape(item.title)}</a></h3>
        <p>{escape(item.summary)}</p>
        <div class="card-meta">{meta_html}</div>
      </article>
    """


def render_forecast(period: ForecastPeriod) -> str:
    emoji = _weather_emoji(period.short_forecast)
    label = _weather_label(period.short_forecast)
    return f"""
      <article class="forecast-card">
        <h3>{escape(emoji)} {escape(period.name)}</h3>
        <div class="forecast-temp">{period.temperature}°{escape(period.temperature_unit)}</div>
        <p>{escape(label)}</p>
        <p class="card-meta"><span>{escape(period.wind_direction)} {escape(period.wind_speed)}</span></p>
      </article>
    """


def render_event_card(item) -> str:
    meta_bits = [bit for bit in [item.source, item.location, item.published] if bit]
    meta_html = "".join(f"<span>{escape(bit)}</span>" for bit in meta_bits)
    calendar_action = (
        f'<a class="card-action secondary" href="{escape(item.calendar_url)}" target="_blank" rel="noreferrer">Add to calendar</a>'
        if item.calendar_url
        else ""
    )
    return f"""
      <article class="story-card story-card-event">
        <div class="story-kicker">{escape(item.eyebrow or item.source)}</div>
        <h3><a class="story-link" href="{escape(item.url)}" target="_blank" rel="noreferrer">{escape(item.title)}</a></h3>
        <p>{escape(item.summary)}</p>
        <div class="card-meta">{meta_html}</div>
        <div class="card-actions">
          <a class="card-action primary" href="{escape(item.url)}" target="_blank" rel="noreferrer">Open event</a>
          {calendar_action}
        </div>
      </article>
    """


def _weather_emoji(short_forecast: str) -> str:
    lowered = short_forecast.lower()
    if "thunder" in lowered:
        return "⛈️"
    if "snow" in lowered or "sleet" in lowered or "ice" in lowered:
        return "❄️"
    if "rain" in lowered or "showers" in lowered or "drizzle" in lowered:
        return "🌧️"
    if "fog" in lowered or "mist" in lowered or "haze" in lowered:
        return "🌫️"
    if "wind" in lowered or "breezy" in lowered:
        return "💨"
    if "cloudy" in lowered or "partly sunny" in lowered or "partly cloudy" in lowered:
        return "⛅"
    if "sunny" in lowered or "clear" in lowered:
        return "☀️"
    return "🌤️"


def _weather_label(short_forecast: str) -> str:
    return f"{_weather_emoji(short_forecast)} {short_forecast}".strip()
