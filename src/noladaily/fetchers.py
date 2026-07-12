from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import quote_plus, urlencode
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

from noladaily.models import DigestItem, DigestSection

REQUEST_HEADERS = {
    "User-Agent": "NolaDaily/0.1 (daily New Orleans digest)",
}

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
WWOZ_CALENDAR_URL = "https://www.wwoz.org/calendar/livewire-music"

NEWS_SECTIONS: tuple[tuple[str, str, str], ...] = (
    (
        "City News",
        "city-news",
        "New Orleans city government, neighborhoods, public life, and major local developments.",
    ),
    (
        "Restaurants",
        "restaurants",
        "Restaurant openings, dining coverage, chef news, and standout food reporting around the city.",
    ),
    (
        "Entertainment",
        "entertainment",
        "Arts, culture, nightlife, festivals, and local entertainment headlines.",
    ),
    (
        "Concerts + Music",
        "music",
        "Live music headlines, concert coverage, and stories tied to New Orleans stages and performers.",
    ),
)

RSS_QUERIES = {
    "city-news": "New Orleans city news OR New Orleans mayor OR New Orleans council",
    "restaurants": "New Orleans restaurants OR New Orleans dining OR New Orleans chef",
    "entertainment": "New Orleans entertainment OR New Orleans arts OR New Orleans festivals",
    "music": "New Orleans concert OR New Orleans live music OR New Orleans jazz show",
}

DATE_PATTERN = re.compile(
    r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+[A-Za-z]+\s+\d{1,2}\s+at\s+\d{1,2}:\d{2}(am|pm)",
    re.IGNORECASE,
)


def build_sections(timeout: int, news_limit: int, events_limit: int) -> tuple[list[DigestSection], list[str]]:
    sections: list[DigestSection] = []
    notes: list[str] = []

    for title, slug, description in NEWS_SECTIONS:
        try:
            items = fetch_google_news(RSS_QUERIES[slug], timeout=timeout, limit=news_limit, eyebrow=title)
        except requests.RequestException as exc:
            items = []
            notes.append(f"{title}: {exc}")

        sections.append(
            DigestSection(
                title=title,
                slug=slug,
                description=description,
                items=items,
                empty_message="No fresh headlines were available for this category during the latest run.",
            )
        )

    try:
        event_items = fetch_wwoz_events(timeout=timeout, limit=events_limit)
    except requests.RequestException as exc:
        event_items = []
        notes.append(f"Upcoming Events: {exc}")

    sections.append(
        DigestSection(
            title="Upcoming Events",
            slug="events",
            description="Fresh event picks pulled from the WWOZ Livewire calendar, with venue and schedule details.",
            items=event_items,
            empty_message="The event calendar could not be refreshed during this run.",
        )
    )

    return sections, notes


def fetch_google_news(query: str, timeout: int, limit: int, eyebrow: str) -> list[DigestItem]:
    url = GOOGLE_NEWS_RSS.format(query=quote_plus(query))
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)

    items: list[DigestItem] = []
    nodes = sorted(
        root.findall(".//item"),
        key=lambda node: _parse_pubdate(_text(node.find("pubDate"))) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    for node in nodes[:limit]:
        title = _clean_text(_text(node.find("title"))) or "Untitled article"
        link = _text(node.find("link")) or ""
        description = _clean_text(_strip_html(_text(node.find("description"))))
        source = _clean_text(_text(node.find("source"))) or "Google News"
        published = _format_pubdate(_text(node.find("pubDate")))

        items.append(
            DigestItem(
                title=title,
                url=link,
                source=source,
                summary=_trim(description or f"Read the latest {eyebrow.lower()} headline."),
                published=published,
                eyebrow=eyebrow,
            )
        )

    return items


def fetch_wwoz_events(timeout: int, limit: int) -> list[DigestItem]:
    response = requests.get(WWOZ_CALENDAR_URL, headers=REQUEST_HEADERS, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    items: list[DigestItem] = []
    seen_urls: set[str] = set()
    current_venue = "WWOZ"

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        text = _clean_text(" ".join(anchor.stripped_strings))
        if not text:
            continue

        absolute_url = _absolute_url(href)
        if "/organizations/" in href:
            # Guard against navigation/footer links being mistaken for venues.
            if 0 < len(text) <= 80:
                current_venue = text
            continue

        if "/events/" not in href or absolute_url in seen_urls:
            continue

        container = anchor
        context_text = ""
        for _ in range(4):
            container = container.parent
            if container is None:
                break
            context_text = " ".join(container.stripped_strings)
            context_text = re.sub(r"\s+", " ", context_text).strip()
            if DATE_PATTERN.search(context_text):
                break

        date_match = DATE_PATTERN.search(context_text or "")
        published = date_match.group(0) if date_match else "See event page for timing"
        summary = _clean_text(f"{current_venue}. Tap through for the full listing and latest schedule details.")

        items.append(
            DigestItem(
                title=text,
                url=absolute_url,
                source="WWOZ Livewire",
                summary=summary,
                published=published,
                eyebrow="Event",
                location=current_venue,
                calendar_url=_build_calendar_url(
                    title=text,
                    location=current_venue,
                    published=published,
                    source_url=absolute_url,
                ),
            )
        )
        seen_urls.add(absolute_url)

        if len(items) == limit:
            break

    return items


def count_total_items(sections: Iterable[DigestSection]) -> int:
    return sum(len(section.items) for section in sections)


def _absolute_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return f"https://www.wwoz.org{href}"


def _strip_html(value: str) -> str:
    if not value:
        return ""
    return " ".join(BeautifulSoup(value, "html.parser").stripped_strings)


_MOJIBAKE_MARKERS = ("Ã", "â", "ð", "Â")


def _mojibake_score(value: str) -> int:
    return sum(value.count(marker) for marker in _MOJIBAKE_MARKERS)


def _clean_text(value: str) -> str:
    if not value:
        return ""

    cleaned = html.unescape(value).strip()
    score = _mojibake_score(cleaned)
    if score:
        try:
            repaired = cleaned.encode("latin-1").decode("utf-8")
        except UnicodeError:
            return cleaned
        # Only accept the repair if it actually reduced mojibake markers;
        # otherwise the text legitimately contained those characters.
        if _mojibake_score(repaired) < score:
            return repaired
    return cleaned


def _format_pubdate(value: str) -> str:
    stamp = _parse_pubdate(value)
    if stamp is None:
        return value if value else ""

    return stamp.strftime("%b %d, %Y %I:%M %p").replace(" 0", " ")


def _parse_pubdate(value: str) -> datetime | None:
    if not value:
        return None

    try:
        stamp = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None

    if stamp.tzinfo is None:
        return stamp.replace(tzinfo=timezone.utc)
    return stamp


def _text(node: ElementTree.Element | None) -> str:
    return node.text.strip() if node is not None and node.text else ""


def _trim(text: str, length: int = 220) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= length:
        return compact
    return compact[: length - 3].rstrip() + "..."


def _build_calendar_url(title: str, location: str, published: str, source_url: str) -> str:
    start_time = _parse_event_datetime(published)
    if start_time is None:
        return ""

    end_time = start_time + timedelta(hours=2)
    params = urlencode(
        {
            "action": "TEMPLATE",
            "text": title,
            "dates": f"{start_time.strftime('%Y%m%dT%H%M%S')}/{end_time.strftime('%Y%m%dT%H%M%S')}",
            "ctz": "America/Chicago",
            "details": f"Source: {source_url}",
            "location": location,
        }
    )
    return f"https://calendar.google.com/calendar/render?{params}"


def _parse_event_datetime(value: str) -> datetime | None:
    # The scraped string has no year ("Friday, July 11 at 8:00pm"). Try the
    # current year first, then next year, and keep the first candidate that
    # is not clearly in the past. This handles December scrapes of January
    # events and Feb 29 dates, which strptime's default 1900 year rejects.
    now = datetime.now()
    for year in (now.year, now.year + 1):
        try:
            parsed = datetime.strptime(f"{value} {year}", "%A, %B %d at %I:%M%p %Y")
        except ValueError:
            continue
        if parsed >= now - timedelta(days=1):
            return parsed

    return None
