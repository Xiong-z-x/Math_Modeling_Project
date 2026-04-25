# -*- coding: utf-8 -*-
"""Feasible initial-solution construction for Problem 1."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Mapping, Sequence

from .constants import VEHICLE_TYPES
from .data_processing.loader import ProblemData
from .solution import Solution


@dataclass(frozen=True)
class RouteSpec:
    """Unevaluated depot-to-depot trip specification."""

    vehicle_type_id: str
    service_node_ids: tuple[int, ...]


def construct_initial_solution(
    problem: ProblemData,
    *,
    max_stops_per_trip: int = 3,
) -> Solution:
    """Build a capacity-feasible and schedulable initial solution."""

    specs = construct_initial_route_specs(problem, max_stops_per_trip=max_stops_per_trip)
    return schedule_route_specs(problem, specs)


def construct_initial_route_specs(
    problem: ProblemData,
    *,
    max_stops_per_trip: int = 3,
) -> tuple[RouteSpec, ...]:
    """Create capacity-feasible trip specs with a time-window ordered first fit."""

    node_records = _service_node_lookup(problem)
    sorted_nodes = sorted(
        node_records.values(),
        key=lambda row: (
            float(row["earliest_min"]),
            float(row["latest_min"]),
            -float(row["demand_weight"]),
            int(row["node_id"]),
        ),
    )
    mutable_routes: list[dict[str, object]] = []

    for node in sorted_nodes:
        best_index = _best_append_route_index(mutable_routes, node, max_stops_per_trip)
        if best_index is None:
            weight = float(node["demand_weight"])
            volume = float(node["demand_volume"])
            mutable_routes.append(
                {
                    "node_ids": [int(node["node_id"])],
                    "weight": weight,
                    "volume": volume,
                    "earliest": float(node["earliest_min"]),
                    "latest": float(node["latest_min"]),
                }
            )
        else:
            route = mutable_routes[best_index]
            route["node_ids"].append(int(node["node_id"]))  # type: ignore[index, union-attr]
            route["weight"] = float(route["weight"]) + float(node["demand_weight"])
            route["volume"] = float(route["volume"]) + float(node["demand_volume"])
            route["earliest"] = min(float(route["earliest"]), float(node["earliest_min"]))
            route["latest"] = max(float(route["latest"]), float(node["latest_min"]))

    return tuple(
        RouteSpec(
            vehicle_type_id=_smallest_feasible_vehicle_id(
                float(route["weight"]),
                float(route["volume"]),
            ),
            service_node_ids=tuple(int(node_id) for node_id in route["node_ids"]),  # type: ignore[union-attr]
        )
        for route in mutable_routes
    )


def _best_append_route_index(
    routes: Sequence[dict[str, object]],
    node: Mapping[str, object],
    max_stops_per_trip: int,
) -> int | None:
    best_index: int | None = None
    best_score = inf
    node_weight = float(node["demand_weight"])
    node_volume = float(node["demand_volume"])
    node_earliest = float(node["earliest_min"])

    for index, route in enumerate(routes):
        node_ids = route["node_ids"]  # type: ignore[assignment]
        if len(node_ids) >= max_stops_per_trip:  # type: ignore[arg-type]
            continue
        total_weight = float(route["weight"]) + node_weight
        total_volume = float(route["volume"]) + node_volume
        vehicle_type_id = _smallest_feasible_vehicle_id_or_none(total_weight, total_volume)
        if vehicle_type_id is None:
            continue

        time_gap = abs(node_earliest - float(route["earliest"]))
        if time_gap > 150:
            continue
        vehicle = VEHICLE_TYPES[vehicle_type_id]
        weight_spare = vehicle.max_weight_kg - total_weight
        volume_spare = vehicle.max_volume_m3 - total_volume
        score = time_gap * 5.0 + weight_spare + volume_spare * 100.0
        if score < best_score:
            best_score = score
            best_index = index

    return best_index


def _smallest_feasible_vehicle_id(weight_kg: float, volume_m3: float) -> str:
    vehicle_type_id = _smallest_feasible_vehicle_id_or_none(weight_kg, volume_m3)
    if vehicle_type_id is None:
        raise ValueError(
            f"demand ({weight_kg:.3f} kg, {volume_m3:.3f} m3) exceeds all vehicle capacities"
        )
    return vehicle_type_id


def _smallest_feasible_vehicle_id_or_none(weight_kg: float, volume_m3: float) -> str | None:
    for vehicle_type_id in ("F3", "E2", "F2", "F1", "E1"):
        vehicle = VEHICLE_TYPES[vehicle_type_id]
        if weight_kg <= vehicle.max_weight_kg + 1e-9 and volume_m3 <= vehicle.max_volume_m3 + 1e-9:
            if vehicle_type_id.startswith("E"):
                continue
            return vehicle_type_id
    for vehicle_type_id in ("E2", "E1"):
        vehicle = VEHICLE_TYPES[vehicle_type_id]
        if weight_kg <= vehicle.max_weight_kg + 1e-9 and volume_m3 <= vehicle.max_volume_m3 + 1e-9:
            return vehicle_type_id
    return None


def _service_node_lookup(problem: ProblemData) -> dict[int, dict[str, object]]:
    return {
        int(row["node_id"]): row
        for row in problem.service_nodes.to_dict(orient="records")
    }


from .scheduler import schedule_route_specs  # noqa: E402  # compatibility import
