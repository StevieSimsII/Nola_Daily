from __future__ import annotations

from typing import Any

import requests

from noladaily.models import ForecastPeriod

NOAA_POINT_URL = "https://api.weather.gov/points/29.9511,-90.0715"
NOAA_HEADERS = {
    "Accept": "application/geo+json",
    "User-Agent": "NolaDaily/0.1 (GitHub Actions digest generator)",
}


def _get_json(url: str, timeout: int) -> dict[str, Any]:
    response = requests.get(url, headers=NOAA_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_weather(timeout: int) -> tuple[ForecastPeriod | None, list[ForecastPeriod]]:
    point_data = _get_json(NOAA_POINT_URL, timeout)
    forecast_url = point_data["properties"]["forecast"]
    forecast_data = _get_json(forecast_url, timeout)
    periods = forecast_data.get("properties", {}).get("periods", [])

    if not periods:
        return None, []

    current = _build_period(periods[0])
    daily: list[ForecastPeriod] = []

    for raw_period in periods:
        if raw_period.get("isDaytime"):
            daily.append(_build_period(raw_period))
        if len(daily) == 7:
            break

    if len(daily) < 7:
        for raw_period in periods:
            candidate = _build_period(raw_period)
            if candidate.name not in {item.name for item in daily}:
                daily.append(candidate)
            if len(daily) == 7:
                break

    return current, daily


def _build_period(raw_period: dict[str, Any]) -> ForecastPeriod:
    return ForecastPeriod(
        name=str(raw_period.get("name", "Forecast")),
        temperature=int(raw_period.get("temperature") or 0),
        temperature_unit=str(raw_period.get("temperatureUnit", "F")),
        short_forecast=str(raw_period.get("shortForecast", "Forecast unavailable")),
        detailed_forecast=str(raw_period.get("detailedForecast", "Forecast unavailable")),
        wind_speed=str(raw_period.get("windSpeed", "")),
        wind_direction=str(raw_period.get("windDirection", "")),
    )