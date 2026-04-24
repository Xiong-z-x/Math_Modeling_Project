# -*- coding: utf-8 -*-
"""Central constants for the green logistics solver.

All numeric parameters from the problem statement and supplement live here so
calculation modules do not hard-code domain values.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VehicleType:
    """Static parameters for one vehicle class."""

    vehicle_id: str
    energy_type: str
    max_weight_kg: float
    max_volume_m3: float
    count: int
    label: str


DAY_START_MIN = 8 * 60
SERVICE_TIME_MIN = 20
FIXED_COST_PER_VEHICLE = 400.0

GREEN_ZONE_CENTER = (0.0, 0.0)
GREEN_ZONE_RADIUS_KM = 10.0

DEFAULT_SPLIT_WEIGHT_KG = 3000.0
DEFAULT_SPLIT_VOLUME_M3 = 15.0

EARLY_PENALTY_PER_MIN = 20.0 / 60.0
LATE_PENALTY_PER_MIN = 50.0 / 60.0

FUEL_PRICE_PER_L = 7.61
ELECTRICITY_PRICE_PER_KWH = 1.64
CARBON_COST_PER_KG = 0.65
FUEL_CARBON_KG_PER_L = 2.547
EV_CARBON_KG_PER_KWH = 0.501
FUEL_LOAD_FACTOR = 0.40
EV_LOAD_FACTOR = 0.35
FUEL_CONSUMPTION_COEFFS = (0.0025, -0.2554, 31.75)
EV_CONSUMPTION_COEFFS = (0.0014, -0.12, 36.19)

VEHICLE_TYPES = {
    "F1": VehicleType("F1", "fuel", 3000.0, 13.5, 60, "fuel_large"),
    "F2": VehicleType("F2", "fuel", 1500.0, 10.8, 50, "fuel_medium"),
    "F3": VehicleType("F3", "fuel", 1250.0, 6.5, 50, "fuel_small"),
    "E1": VehicleType("E1", "ev", 3000.0, 15.0, 10, "ev_large"),
    "E2": VehicleType("E2", "ev", 1250.0, 8.5, 15, "ev_small"),
}

SPEED_PARAMS = {
    "CONGESTED": {"mu": 9.8, "sigma": 4.7, "sigma2": 4.7**2},
    "SMOOTH": {"mu": 55.3, "sigma": 0.1, "sigma2": 0.1**2},
    "MEDIUM": {"mu": 35.4, "sigma": 5.2, "sigma2": 5.2**2},
}

SPEED_PERIODS = [
    (8 * 60, 9 * 60, "CONGESTED"),
    (9 * 60, 10 * 60, "SMOOTH"),
    (10 * 60, 11 * 60 + 30, "MEDIUM"),
    (11 * 60 + 30, 13 * 60, "CONGESTED"),
    (13 * 60, 15 * 60, "SMOOTH"),
    (15 * 60, 17 * 60, "MEDIUM"),
    (17 * 60, 24 * 60, "MEDIUM"),
]
