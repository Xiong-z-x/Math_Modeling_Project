# -*- coding: utf-8 -*-
"""Feasible initial-solution construction for Problem 1."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Iterable, Mapping, Sequence

from .constants import DAY_START_MIN, FIXED_COST_PER_VEHICLE, VEHICLE_TYPES
from .data_processing.loader import ProblemData
from .solution import Route, Solution, evaluate_route, evaluate_solution
from .travel_time import calculate_arrival_time

LATE_SCHEDULING_PRIORITY = 2.0


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


def schedule_route_specs(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    *,
    vehicle_counts: Mapping[str, int] | None = None,
    required_node_ids: Iterable[int] | None = None,
) -> Solution:
    """Assign trip specs to physical vehicles and evaluate their actual timings."""

    counts = dict(vehicle_counts or {key: vehicle.count for key, vehicle in VEHICLE_TYPES.items()})
    required = set(
        int(node_id)
        for node_id in (
            required_node_ids
            if required_node_ids is not None
            else problem.service_nodes["node_id"].astype(int).tolist()
        )
    )
    ordered_specs = sorted(specs, key=lambda spec: _spec_time_key(problem, spec))
    vehicles_by_type: dict[str, list[dict[str, object]]] = {}
    scheduled_routes: list[Route] = []

    for spec_index, spec in enumerate(ordered_specs, start=1):
        candidate_type_ids = _candidate_vehicle_type_ids(problem, spec, counts)
        if not candidate_type_ids:
            raise ValueError(f"no feasible vehicle type available for trip {spec_index}")

        best_route: Route | None = None
        best_vehicle: dict[str, object] | None = None
        best_vehicle_pool: list[dict[str, object]] | None = None
        best_is_new = False
        best_score = inf

        for vehicle_type_id in candidate_type_ids:
            existing = vehicles_by_type.setdefault(vehicle_type_id, [])

            for vehicle in existing:
                depart_min = _preferred_departure_min(
                    problem,
                    spec,
                    available_min=float(vehicle["available_min"]),
                )
                candidate = evaluate_route(
                    problem,
                    vehicle_type_id,
                    spec.service_node_ids,
                    depart_min=depart_min,
                    fixed_cost=0.0,
                    physical_vehicle_id=str(vehicle["vehicle_id"]),
                    trip_id=f"T{spec_index:04d}",
                )
                candidate_score = _scheduling_selection_score(candidate)
                if candidate_score < best_score:
                    best_route = candidate
                    best_vehicle = vehicle
                    best_vehicle_pool = existing
                    best_is_new = False
                    best_score = candidate_score

            if len(existing) < counts[vehicle_type_id]:
                vehicle_id = f"{vehicle_type_id}-{len(existing) + 1:03d}"
                depart_min = _preferred_departure_min(
                    problem,
                    spec,
                    available_min=float(DAY_START_MIN),
                )
                candidate = evaluate_route(
                    problem,
                    vehicle_type_id,
                    spec.service_node_ids,
                    depart_min=depart_min,
                    fixed_cost=FIXED_COST_PER_VEHICLE,
                    physical_vehicle_id=vehicle_id,
                    trip_id=f"T{spec_index:04d}",
                )
                candidate_score = _scheduling_selection_score(candidate)
                if candidate_score < best_score:
                    best_route = candidate
                    best_vehicle = {"vehicle_id": vehicle_id, "available_min": DAY_START_MIN}
                    best_vehicle_pool = existing
                    best_is_new = True
                    best_score = candidate_score

        if best_route is None or best_vehicle is None or best_vehicle_pool is None:
            raise ValueError(
                f"no physical vehicle available for trip {spec_index}"
            )

        best_vehicle["available_min"] = best_route.return_min
        if best_is_new:
            best_vehicle_pool.append(best_vehicle)
        scheduled_routes.append(best_route)

    return evaluate_solution(scheduled_routes, required_node_ids=required)


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


def _candidate_vehicle_type_ids(
    problem: ProblemData,
    spec: RouteSpec,
    vehicle_counts: Mapping[str, int],
) -> tuple[str, ...]:
    weight, volume = _route_demand(problem, spec.service_node_ids)
    feasible: list[str] = []
    for vehicle_type_id, count in vehicle_counts.items():
        if count <= 0 or vehicle_type_id not in VEHICLE_TYPES:
            continue
        vehicle = VEHICLE_TYPES[vehicle_type_id]
        if weight <= vehicle.max_weight_kg + 1e-9 and volume <= vehicle.max_volume_m3 + 1e-9:
            feasible.append(vehicle_type_id)
    return tuple(feasible)


def _route_demand(problem: ProblemData, service_node_ids: Sequence[int]) -> tuple[float, float]:
    lookup = _service_node_lookup(problem)
    weight = sum(float(lookup[int(node_id)]["demand_weight"]) for node_id in service_node_ids)
    volume = sum(float(lookup[int(node_id)]["demand_volume"]) for node_id in service_node_ids)
    return weight, volume


def _spec_time_key(problem: ProblemData, spec: RouteSpec) -> tuple[float, float, int]:
    lookup = _service_node_lookup(problem)
    earliest_values = [float(lookup[node_id]["earliest_min"]) for node_id in spec.service_node_ids]
    latest_values = [float(lookup[node_id]["latest_min"]) for node_id in spec.service_node_ids]
    return (min(earliest_values), min(latest_values), min(spec.service_node_ids))


def _preferred_departure_min(problem: ProblemData, spec: RouteSpec, *, available_min: float) -> float:
    """Delay departure so the first stop arrives near its earliest time."""

    first_node_id = int(spec.service_node_ids[0])
    lookup = _service_node_lookup(problem)
    first_node = lookup[first_node_id]
    first_customer_id = int(first_node["customer_id"])
    earliest_min = float(first_node["earliest_min"])
    distance = float(problem.distance_matrix.loc[0, first_customer_id])

    if calculate_arrival_time(distance, available_min) >= earliest_min:
        return available_min

    low = float(available_min)
    high = max(float(available_min), earliest_min)
    while calculate_arrival_time(distance, high) < earliest_min:
        high += 30.0

    for _ in range(50):
        mid = (low + high) / 2.0
        if calculate_arrival_time(distance, mid) < earliest_min:
            low = mid
        else:
            high = mid
    return high


def _scheduling_selection_score(route: Route) -> float:
    late_minutes = sum(stop.late_min for stop in route.stops)
    return route.total_cost + late_minutes * LATE_SCHEDULING_PRIORITY
