from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class DigestItem:
    title: str
    url: str
    source: str
    summary: str
    published: str = ""
    eyebrow: str = ""
    location: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class DigestSection:
    title: str
    slug: str
    description: str
    items: list[DigestItem] = field(default_factory=list)
    empty_message: str = "No fresh items were available during this run."

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "slug": self.slug,
            "description": self.description,
            "empty_message": self.empty_message,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(slots=True)
class ForecastPeriod:
    name: str
    temperature: int
    temperature_unit: str
    short_forecast: str
    detailed_forecast: str
    wind_speed: str
    wind_direction: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class DailyDigest:
    generated_at: str
    generated_label: str
    lead: str
    current_forecast: ForecastPeriod | None
    seven_day_forecast: list[ForecastPeriod]
    sections: list[DigestSection]
    source_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "generated_label": self.generated_label,
            "lead": self.lead,
            "current_forecast": self.current_forecast.to_dict() if self.current_forecast else None,
            "seven_day_forecast": [period.to_dict() for period in self.seven_day_forecast],
            "sections": [section.to_dict() for section in self.sections],
            "source_notes": list(self.source_notes),
        }
