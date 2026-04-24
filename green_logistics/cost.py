# -*- coding: utf-8 -*-
"""Energy, carbon, and soft time-window cost utilities."""

from __future__ import annotations

from dataclasses import dataclass

from .constants import (
    CARBON_COST_PER_KG,
    EARLY_PENALTY_PER_MIN,
    ELECTRICITY_PRICE_PER_KWH,
    EV_CARBON_KG_PER_KWH,
    EV_CONSUMPTION_COEFFS,
    EV_LOAD_FACTOR,
    FUEL_CARBON_KG_PER_L,
    FUEL_CONSUMPTION_COEFFS,
    FUEL_LOAD_FACTOR,
    FUEL_PRICE_PER_L,
    LATE_PENALTY_PER_MIN,
    SPEED_PARAMS,
    VEHICLE_TYPES,
    VehicleType,
)
from .travel_time import TravelSegment, split_travel_segments


@dataclass(frozen=True)
class ArcEnergyCost:
    """Energy and carbon cost accumulated over one traveled arc."""

    consumption: float
    energy_cost: float
    carbon_kg: float
    carbon_cost: float
    arrival_min: float
    segments: tuple[TravelSegment, ...]


@dataclass(frozen=True)
class TimeWindowPenalty:
    """Soft time-window penalty components at one service node."""

    wait_min: float
    late_min: float
    cost: float


def expected_consumption_rate(vehicle_type: VehicleType | str, period_key: str) -> float:
    """Return expected liters or kWh per 100 km for a speed period."""

    vehicle = _resolve_vehicle_type(vehicle_type)
    if period_key not in SPEED_PARAMS:
        raise ValueError(f"unknown speed period: {period_key!r}")

    params = SPEED_PARAMS[period_key]
    mu = float(params["mu"])
    second_moment = mu**2 + float(params["sigma2"])

    if vehicle.energy_type == "fuel":
        a, b, c = FUEL_CONSUMPTION_COEFFS
    elif vehicle.energy_type == "ev":
        a, b, c = EV_CONSUMPTION_COEFFS
    else:
        raise ValueError(f"unsupported vehicle energy type: {vehicle.energy_type!r}")

    return a * second_moment + b * mu + c


def load_factor(vehicle_type: VehicleType | str, current_weight_kg: float) -> float:
    """Return payload correction factor for a vehicle and current load."""

    vehicle = _resolve_vehicle_type(vehicle_type)
    if current_weight_kg < 0:
        raise ValueError(f"current_weight_kg must be non-negative, got {current_weight_kg}")

    payload_ratio = current_weight_kg / vehicle.max_weight_kg
    if vehicle.energy_type == "fuel":
        return 1.0 + FUEL_LOAD_FACTOR * payload_ratio
    if vehicle.energy_type == "ev":
        return 1.0 + EV_LOAD_FACTOR * payload_ratio
    raise ValueError(f"unsupported vehicle energy type: {vehicle.energy_type!r}")


def calculate_arc_energy_cost(
    distance_km: float,
    depart_min: float,
    vehicle_type: VehicleType | str,
    current_weight_kg: float,
) -> ArcEnergyCost:
    """Calculate expected energy and carbon cost for one arc."""

    vehicle = _resolve_vehicle_type(vehicle_type)
    segments = tuple(split_travel_segments(distance_km, depart_min))
    factor = load_factor(vehicle, current_weight_kg)
    consumption = sum(
        segment.distance_km
        / 100.0
        * expected_consumption_rate(vehicle, segment.period_key)
        for segment in segments
    ) * factor

    if vehicle.energy_type == "fuel":
        energy_cost = consumption * FUEL_PRICE_PER_L
        carbon_kg = consumption * FUEL_CARBON_KG_PER_L
    elif vehicle.energy_type == "ev":
        energy_cost = consumption * ELECTRICITY_PRICE_PER_KWH
        carbon_kg = consumption * EV_CARBON_KG_PER_KWH
    else:
        raise ValueError(f"unsupported vehicle energy type: {vehicle.energy_type!r}")

    carbon_cost = carbon_kg * CARBON_COST_PER_KG
    arrival_min = segments[-1].end_min if segments else float(depart_min)
    return ArcEnergyCost(
        consumption=consumption,
        energy_cost=energy_cost,
        carbon_kg=carbon_kg,
        carbon_cost=carbon_cost,
        arrival_min=arrival_min,
        segments=segments,
    )


def calculate_time_window_penalty(
    arrival_min: float,
    earliest_min: float,
    latest_min: float,
) -> TimeWindowPenalty:
    """Calculate soft time-window wait and late penalties."""

    if latest_min < earliest_min:
        raise ValueError(
            f"latest_min must be >= earliest_min, got {latest_min} < {earliest_min}"
        )

    wait_min = max(float(earliest_min) - float(arrival_min), 0.0)
    late_min = max(float(arrival_min) - float(latest_min), 0.0)
    cost = wait_min * EARLY_PENALTY_PER_MIN + late_min * LATE_PENALTY_PER_MIN
    return TimeWindowPenalty(wait_min=wait_min, late_min=late_min, cost=cost)


def _resolve_vehicle_type(vehicle_type: VehicleType | str) -> VehicleType:
    if isinstance(vehicle_type, VehicleType):
        return vehicle_type
    if vehicle_type in VEHICLE_TYPES:
        return VEHICLE_TYPES[vehicle_type]
    raise ValueError(f"unknown vehicle type: {vehicle_type!r}")
