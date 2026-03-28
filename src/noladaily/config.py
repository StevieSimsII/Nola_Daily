from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    output_dir: Path
    data_path: Path
    teams_webhook_url: str
    teams_webhook_mode: str
    site_url: str
    request_timeout: int = 20


def derive_site_url() -> str:
    explicit = os.getenv("SITE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/") + "/"

    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    if "/" not in repository:
        return ""

    owner, repo = repository.split("/", 1)
    if repo.lower() == f"{owner.lower()}.github.io":
        return f"https://{owner}.github.io/"

    return f"https://{owner}.github.io/{repo}/"


def build_config(output_dir: str, data_path: str) -> AppConfig:
    return AppConfig(
        output_dir=Path(output_dir),
        data_path=Path(data_path),
        teams_webhook_url=os.getenv("TEAMS_WEBHOOK_URL", "").strip(),
        teams_webhook_mode=os.getenv("TEAMS_WEBHOOK_MODE", "power_automate").strip() or "power_automate",
        site_url=derive_site_url(),
    )
