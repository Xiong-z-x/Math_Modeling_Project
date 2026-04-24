# -*- coding: utf-8 -*-
"""Time-dependent travel-time integration utilities."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf, isfinite

from .constants import DAY_START_MIN, SPEED_PARAMS, SPEED_PERIODS


@dataclass(frozen=True)
class SpeedPeriod:
    """Speed-distribution parameters active over a time interval."""

    key: str
    start_min: float
    end_min: float
    mu_kmh: float
    sigma_kmh: float


@dataclass(frozen=True)
class TravelSegment:
    """One contiguous arc fragment traveled under one speed period."""

    period_key: str
    start_min: float
    end_min: float
    distance_km: float
    mu_kmh: float
    sigma_kmh: float


def speed_period_at(time_min: float) -> SpeedPeriod:
    """Return the speed period active at an absolute minute."""

    if time_min < DAY_START_MIN:
        raise ValueError(f"time_min must be >= {DAY_START_MIN}, got {time_min}")

    for start_min, end_min, key in SPEED_PERIODS:
        if start_min <= time_min < end_min:
            return _build_speed_period(key, float(start_min), float(end_min))

    last_start, _last_end, last_key = SPEED_PERIODS[-1]
    return _build_speed_period(last_key, float(last_start), inf)


def split_travel_segments(distance_km: float, depart_min: float) -> list[TravelSegment]:
    """Split an arc into speed-period fragments."""

    _validate_travel_inputs(distance_km, depart_min)
    if distance_km == 0:
        return []

    remaining_km = float(distance_km)
    time_min = float(depart_min)
    segments: list[TravelSegment] = []

    while remaining_km > 1e-10:
        period = speed_period_at(time_min)
        available_min = period.end_min - time_min
        available_km = inf if not isfinite(available_min) else period.mu_kmh * available_min / 60.0

        if available_km >= remaining_km - 1e-10:
            travel_min = remaining_km / period.mu_kmh * 60.0
            end_min = time_min + travel_min
            segment_distance = remaining_km
            remaining_km = 0.0
        else:
            end_min = period.end_min
            segment_distance = available_km
            remaining_km -= segment_distance

        segments.append(
            TravelSegment(
                period_key=period.key,
                start_min=time_min,
                end_min=end_min,
                distance_km=segment_distance,
                mu_kmh=period.mu_kmh,
                sigma_kmh=period.sigma_kmh,
            )
        )
        time_min = end_min

    return segments


def calculate_arrival_time(distance_km: float, depart_min: float) -> float:
    """Return the absolute arrival minute for a distance and departure time."""

    segments = split_travel_segments(distance_km, depart_min)
    if not segments:
        return float(depart_min)
    return segments[-1].end_min


def _build_speed_period(key: str, start_min: float, end_min: float) -> SpeedPeriod:
    params = SPEED_PARAMS[key]
    return SpeedPeriod(
        key=key,
        start_min=start_min,
        end_min=end_min,
        mu_kmh=float(params["mu"]),
        sigma_kmh=float(params["sigma"]),
    )


def _validate_travel_inputs(distance_km: float, depart_min: float) -> None:
    if distance_km < 0:
        raise ValueError(f"distance_km must be non-negative, got {distance_km}")
    if depart_min < DAY_START_MIN:
        raise ValueError(f"depart_min must be >= {DAY_START_MIN}, got {depart_min}")
