from __future__ import annotations

import json
from pathlib import Path

import requests

from noladaily.models import DailyDigest, DigestItem, DigestSection, ForecastPeriod


def send_notification(
    digest: DailyDigest,
    webhook_url: str,
    mode: str,
    site_url: str,
    timeout: int,
    required: bool,
) -> bool:
    if not webhook_url:
        if required:
            raise RuntimeError("TEAMS_WEBHOOK_URL is required for this run.")
        return False

    featured = list(_featured_items(digest))
    if not featured:
        if required:
            raise RuntimeError("No digest items were available to send to Teams.")
        return False

    adaptive_card = build_adaptive_card(digest, featured, site_url)
    payload = build_payload(mode=mode, adaptive_card=adaptive_card, digest=digest, featured=featured, site_url=site_url)

    response = requests.post(webhook_url, json=payload, timeout=timeout)
    if response.status_code >= 400:
        message = f"Teams notification failed with status {response.status_code}: {response.text[:300]}"
        if required:
            raise RuntimeError(message)
        return False
    return True


def send_sample_notification(webhook_url: str, mode: str, site_url: str, timeout: int, required: bool) -> bool:
    digest = _sample_digest()
    return send_notification(digest, webhook_url=webhook_url, mode=mode, site_url=site_url, timeout=timeout, required=required)


def load_digest_from_file(path: Path) -> DailyDigest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    current = payload.get("current_forecast")
    sections = []
    for raw_section in payload.get("sections", []):
        sections.append(
            DigestSection(
                title=raw_section["title"],
                slug=raw_section["slug"],
                description=raw_section["description"],
                empty_message=raw_section.get("empty_message", "No items available."),
                items=[DigestItem(**raw_item) for raw_item in raw_section.get("items", [])],
            )
        )

    forecast = [ForecastPeriod(**raw_period) for raw_period in payload.get("seven_day_forecast", [])]
    return DailyDigest(
        generated_at=payload["generated_at"],
        generated_label=payload["generated_label"],
        lead=payload["lead"],
        current_forecast=ForecastPeriod(**current) if current else None,
        seven_day_forecast=forecast,
        sections=sections,
        source_notes=payload.get("source_notes", []),
    )


def build_payload(mode: str, adaptive_card: dict, digest: DailyDigest, featured: list[DigestItem], site_url: str) -> dict:
    mode_key = mode.lower().replace("-", "_")
    if mode_key == "teams":
        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": adaptive_card,
                }
            ],
        }

    return adaptive_card


def build_adaptive_card(digest: DailyDigest, featured: list[DigestItem], site_url: str) -> dict:
    body: list[dict] = [
        {
            "type": "TextBlock",
            "size": "Large",
            "weight": "Bolder",
            "text": f"Nola Daily | {digest.generated_label}",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "spacing": "Small",
            "text": digest.lead,
            "wrap": True,
        },
    ]

    if digest.current_forecast:
        weather = digest.current_forecast
        body.append(
            {
                "type": "TextBlock",
                "spacing": "Medium",
                "text": f"Weather: {weather.name} | {weather.temperature}°{weather.temperature_unit} | {weather.short_forecast}",
                "wrap": True,
            }
        )

    for item in featured[:3]:
        body.extend(
            [
                {
                    "type": "TextBlock",
                    "spacing": "Medium",
                    "weight": "Bolder",
                    "text": item.title,
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "spacing": "None",
                    "text": f"{item.source} | {item.location or item.published or 'Open link'}",
                    "isSubtle": True,
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "spacing": "Small",
                    "text": item.summary,
                    "wrap": True,
                },
            ]
        )

    actions = [
        {"type": "Action.OpenUrl", "title": "Open Featured Story", "url": featured[0].url},
    ]
    if site_url:
        actions.append({"type": "Action.OpenUrl", "title": "Open Site", "url": site_url})

    return {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": body,
        "actions": actions,
    }


def _featured_items(digest: DailyDigest):
    for section in digest.sections:
        if section.items:
            yield section.items[0]


def _sample_digest() -> DailyDigest:
    section = DigestSection(
        title="City News",
        slug="city-news",
        description="Sample content",
        items=[
            DigestItem(
                title="Sample Nola Daily headline",
                url="https://example.com/story",
                source="Sample Source",
                summary="This is a realistic sample payload used to validate your Teams or Power Automate notification path.",
                published="Today",
                eyebrow="City News",
            )
        ],
    )
    return DailyDigest(
        generated_at="2026-03-28T07:00:00-05:00",
        generated_label="Mar 28, 2026 at 7:00 AM CT",
        lead="Your daily New Orleans briefing is ready with fresh headlines, live events, and weather.",
        current_forecast=ForecastPeriod(
            name="Today",
            temperature=74,
            temperature_unit="F",
            short_forecast="Mostly sunny",
            detailed_forecast="Mostly sunny with a light breeze.",
            wind_speed="5 to 10 mph",
            wind_direction="SE",
        ),
        seven_day_forecast=[],
        sections=[section],
        source_notes=[],
    )
