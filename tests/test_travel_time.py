# -*- coding: utf-8 -*-
"""Tests for time-dependent travel-time integration."""

from __future__ import annotations

import math

import pytest

from green_logistics.travel_time import (
    TravelSegment,
    calculate_arrival_time,
    split_travel_segments,
    speed_period_at,
)


def test_speed_period_lookup_respects_boundaries() -> None:
    assert speed_period_at(480).key == "CONGESTED"
    assert speed_period_at(539.999).key == "CONGESTED"
    assert speed_period_at(540).key == "SMOOTH"
    assert speed_period_at(600).key == "MEDIUM"
    assert speed_period_at(690).key == "CONGESTED"
    assert speed_period_at(780).key == "SMOOTH"
    assert speed_period_at(1020).key == "MEDIUM"
    assert speed_period_at(1500).key == "MEDIUM"


def test_calculate_arrival_time_within_one_period() -> None:
    arrival = calculate_arrival_time(distance_km=9.8, depart_min=480)

    assert arrival == pytest.approx(540.0)


def test_split_travel_segments_crosses_period_boundary() -> None:
    segments = split_travel_segments(distance_km=20.0, depart_min=510.0)

    assert segments == [
        TravelSegment(
            period_key="CONGESTED",
            start_min=510.0,
            end_min=540.0,
            distance_km=4.9,
            mu_kmh=9.8,
            sigma_kmh=4.7,
        ),
        TravelSegment(
            period_key="SMOOTH",
            start_min=540.0,
            end_min=540.0 + (20.0 - 4.9) / 55.3 * 60.0,
            distance_km=15.1,
            mu_kmh=55.3,
            sigma_kmh=0.1,
        ),
    ]

    assert sum(segment.distance_km for segment in segments) == pytest.approx(20.0)
    assert segments[-1].end_min == pytest.approx(
        540.0 + (20.0 - 4.9) / 55.3 * 60.0
    )


def test_arrival_time_is_fifo_monotone_across_speed_changes() -> None:
    previous_arrival = -math.inf

    for depart_min in range(480, 18 * 60, 5):
        arrival = calculate_arrival_time(distance_km=35.0, depart_min=float(depart_min))
        assert arrival >= previous_arrival
        previous_arrival = arrival


def test_invalid_travel_inputs_raise() -> None:
    with pytest.raises(ValueError, match="distance"):
        calculate_arrival_time(distance_km=-1.0, depart_min=480.0)

    with pytest.raises(ValueError, match="depart"):
        calculate_arrival_time(distance_km=1.0, depart_min=479.0)
