from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from noladaily.config import build_config
from noladaily.fetchers import build_sections, count_total_items
from noladaily.models import DailyDigest
from noladaily.site import write_site
from noladaily.teams import load_digest_from_file, send_notification, send_sample_notification
from noladaily.weather import fetch_weather

CENTRAL_TIME = ZoneInfo("America/Chicago")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the Nola Daily digest site and optional Teams notification.")
    parser.add_argument("--output-dir", default="docs", help="Directory where the static site should be written.")
    parser.add_argument("--data-path", default="docs/data/digest.json", help="Path for the generated digest JSON.")
    parser.add_argument("--news-limit", type=int, default=6, help="Number of items per news section.")
    parser.add_argument("--events-limit", type=int, default=12, help="Number of event items to include.")
    parser.add_argument("--skip-teams", action="store_true", help="Skip sending a Teams notification during a full refresh.")
    parser.add_argument("--teams-required", action="store_true", help="Fail the run if a Teams notification is requested but not delivered.")
    parser.add_argument("--teams-sample", action="store_true", help="Send a sample Teams notification and exit.")
    parser.add_argument("--teams-from-file", help="Send a Teams notification from an existing digest JSON file and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = build_config(output_dir=args.output_dir, data_path=args.data_path)

    if args.teams_sample:
        send_sample_notification(
            webhook_url=config.teams_webhook_url,
            mode=config.teams_webhook_mode,
            site_url=config.site_url,
            timeout=config.request_timeout,
            required=args.teams_required,
        )
        return 0

    if args.teams_from_file:
        digest = load_digest_from_file(Path(args.teams_from_file))
        send_notification(
            digest,
            webhook_url=config.teams_webhook_url,
            mode=config.teams_webhook_mode,
            site_url=config.site_url,
            timeout=config.request_timeout,
            required=args.teams_required,
        )
        return 0

    digest = build_digest(news_limit=args.news_limit, events_limit=args.events_limit, timeout=config.request_timeout)
    write_site(digest, output_dir=config.output_dir, data_path=config.data_path)

    if not args.skip_teams:
        send_notification(
            digest,
            webhook_url=config.teams_webhook_url,
            mode=config.teams_webhook_mode,
            site_url=config.site_url,
            timeout=config.request_timeout,
            required=args.teams_required,
        )

    return 0


def build_digest(news_limit: int, events_limit: int, timeout: int) -> DailyDigest:
    sections, notes = build_sections(timeout=timeout, news_limit=news_limit, events_limit=events_limit)

    try:
        current_forecast, seven_day_forecast = fetch_weather(timeout=timeout)
    except Exception as exc:
        current_forecast, seven_day_forecast = None, []
        notes.append(f"Weather: {exc}")

    now = datetime.now(CENTRAL_TIME)
    lead = _build_lead(total_items=count_total_items(sections), event_count=len(next((section.items for section in sections if section.slug == "events"), [])))

    return DailyDigest(
        generated_at=now.isoformat(),
        generated_label=now.strftime("%b %d, %Y at %I:%M %p CT").replace(" 0", " "),
        lead=lead,
        current_forecast=current_forecast,
        seven_day_forecast=seven_day_forecast,
        sections=sections,
        source_notes=notes,
    )


def _build_lead(total_items: int, event_count: int) -> str:
    return (
        f"A calm daily scan of New Orleans with {total_items} fresh links across news, dining, entertainment, music, and {event_count} event picks, plus the latest local forecast."
    )


if __name__ == "__main__":
    raise SystemExit(main())