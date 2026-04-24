# -*- coding: utf-8 -*-
"""Tests for expected energy, carbon, and time-window cost calculations."""

from __future__ import annotations

import pytest

from green_logistics.constants import (
    CARBON_COST_PER_KG,
    EARLY_PENALTY_PER_MIN,
    FUEL_CARBON_KG_PER_L,
    FUEL_PRICE_PER_L,
    LATE_PENALTY_PER_MIN,
    VEHICLE_TYPES,
)
from green_logistics.cost import (
    ArcEnergyCost,
    TimeWindowPenalty,
    calculate_arc_energy_cost,
    calculate_time_window_penalty,
    expected_consumption_rate,
    load_factor,
)


def _fuel_rate(mu: float, sigma: float) -> float:
    return 0.0025 * (mu**2 + sigma**2) - 0.2554 * mu + 31.75


def _ev_rate(mu: float, sigma: float) -> float:
    return 0.0014 * (mu**2 + sigma**2) - 0.12 * mu + 36.19


def test_expected_consumption_rate_uses_jensen_second_moment() -> None:
    fuel_rate = expected_consumption_rate(VEHICLE_TYPES["F1"], "CONGESTED")
    ev_rate = expected_consumption_rate(VEHICLE_TYPES["E1"], "MEDIUM")

    assert fuel_rate == pytest.approx(_fuel_rate(9.8, 4.7))
    assert fuel_rate > 0.0025 * 9.8**2 - 0.2554 * 9.8 + 31.75

    assert ev_rate == pytest.approx(_ev_rate(35.4, 5.2))
    assert ev_rate > 0.0014 * 35.4**2 - 0.12 * 35.4 + 36.19


def test_load_factor_depends_on_vehicle_energy_type_and_payload_ratio() -> None:
    assert load_factor(VEHICLE_TYPES["F1"], current_weight_kg=1500.0) == pytest.approx(1.2)
    assert load_factor(VEHICLE_TYPES["E1"], current_weight_kg=3000.0) == pytest.approx(1.35)


def test_arc_energy_cost_is_accumulated_by_travel_segments() -> None:
    result = calculate_arc_energy_cost(
        distance_km=20.0,
        depart_min=510.0,
        vehicle_type=VEHICLE_TYPES["F1"],
        current_weight_kg=1500.0,
    )

    expected_liters = (
        4.9 / 100.0 * _fuel_rate(9.8, 4.7)
        + 15.1 / 100.0 * _fuel_rate(55.3, 0.1)
    ) * 1.2

    assert isinstance(result, ArcEnergyCost)
    assert result.consumption == pytest.approx(expected_liters)
    assert result.energy_cost == pytest.approx(expected_liters * FUEL_PRICE_PER_L)
    assert result.carbon_kg == pytest.approx(expected_liters * FUEL_CARBON_KG_PER_L)
    assert result.carbon_cost == pytest.approx(
        expected_liters * FUEL_CARBON_KG_PER_L * CARBON_COST_PER_KG
    )
    assert result.arrival_min == pytest.approx(540.0 + 15.1 / 55.3 * 60.0)
    assert [segment.period_key for segment in result.segments] == ["CONGESTED", "SMOOTH"]


def test_time_window_penalty_uses_arrival_time() -> None:
    early = calculate_time_window_penalty(arrival_min=540.0, earliest_min=549.0, latest_min=600.0)
    on_time = calculate_time_window_penalty(
        arrival_min=570.0, earliest_min=549.0, latest_min=600.0
    )
    late = calculate_time_window_penalty(arrival_min=610.0, earliest_min=549.0, latest_min=600.0)

    assert early == TimeWindowPenalty(wait_min=9.0, late_min=0.0, cost=9.0 * EARLY_PENALTY_PER_MIN)
    assert on_time == TimeWindowPenalty(wait_min=0.0, late_min=0.0, cost=0.0)
    assert late == TimeWindowPenalty(wait_min=0.0, late_min=10.0, cost=10.0 * LATE_PENALTY_PER_MIN)
