"""Write the digest data payload for the static site.

The front-end (docs/index.html + docs/assets/styles.css) is a hand-crafted
static page that fetches docs/data/digest.json client-side. The daily run
only refreshes the JSON, so design changes never collide with data commits.
"""

from __future__ import annotations

import json
from pathlib import Path

from noladaily.models import DailyDigest


def write_site(digest: DailyDigest, output_dir: Path, data_path: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(digest.to_dict(), indent=2), encoding="utf-8")
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")
