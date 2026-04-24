# -*- coding: utf-8 -*-
"""Route and solution evaluation for Problem 1."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence

from .constants import SERVICE_TIME_MIN, VEHICLE_TYPES, VehicleType
from .cost import calculate_arc_energy_cost, calculate_time_window_penalty
from .data_processing.loader import ProblemData


@dataclass(frozen=True)
class ArcRecord:
    """One traveled arc in a route/trip evaluation."""

    from_customer_id: int
    to_customer_id: int
    distance_km: float
    depart_min: float
    arrival_min: float
    load_weight_kg: float
    load_volume_m3: float
    energy_cost: float
    carbon_cost: float
    carbon_kg: float
    consumption: float


@dataclass(frozen=True)
class StopRecord:
    """Service timing and load state at one virtual service node."""

    service_node_id: int
    customer_id: int
    earliest_min: float
    latest_min: float
    arrival_min: float
    wait_min: float
    late_min: float
    service_start_min: float
    departure_min: float
    demand_weight_kg: float
    demand_volume_m3: float
    load_before_service_kg: float
    load_before_service_m3: float
    load_after_service_kg: float
    load_after_service_m3: float
    penalty_cost: float


@dataclass(frozen=True)
class Route:
    """A depot-to-depot trip served by one vehicle type."""

    vehicle_type_id: str
    vehicle_type: VehicleType
    service_node_ids: tuple[int, ...]
    customer_ids: tuple[int, ...]
    depart_min: float
    return_min: float
    stops: tuple[StopRecord, ...]
    arcs: tuple[ArcRecord, ...]
    total_weight_kg: float
    total_volume_m3: float
    total_distance_km: float
    fixed_cost: float
    energy_cost: float
    carbon_cost: float
    carbon_kg: float
    penalty_cost: float
    total_cost: float
    physical_vehicle_id: str | None = None
    trip_id: str | None = None

    @property
    def is_capacity_feasible(self) -> bool:
        return (
            self.total_weight_kg <= self.vehicle_type.max_weight_kg + 1e-9
            and self.total_volume_m3 <= self.vehicle_type.max_volume_m3 + 1e-9
        )


@dataclass(frozen=True)
class Solution:
    """Evaluated set of depot-to-depot trips."""

    routes: tuple[Route, ...]
    required_node_ids: tuple[int, ...]
    missing_node_ids: tuple[int, ...]
    duplicate_node_ids: tuple[int, ...]
    fixed_cost: float
    energy_cost: float
    carbon_cost: float
    carbon_kg: float
    penalty_cost: float
    total_distance_km: float
    total_cost: float
    vehicle_trip_usage_by_type: dict[str, int]
    vehicle_physical_usage_by_type: dict[str, int]

    @property
    def is_complete(self) -> bool:
        return not self.missing_node_ids and not self.duplicate_node_ids

    @property
    def is_capacity_feasible(self) -> bool:
        return all(route.is_capacity_feasible for route in self.routes)


def evaluate_route(
    problem: ProblemData,
    vehicle_type: VehicleType | str,
    service_node_ids: Sequence[int],
    *,
    depart_min: float,
    fixed_cost: float = 0.0,
    physical_vehicle_id: str | None = None,
    trip_id: str | None = None,
) -> Route:
    """Evaluate one depot-to-depot trip.

    `service_node_ids` are internal virtual service-node IDs. Distances are
    always looked up with original `customer_id` values.
    """

    vehicle = _resolve_vehicle_type(vehicle_type)
    node_ids = tuple(int(node_id) for node_id in service_node_ids)
    nodes = _service_node_records(problem, node_ids)

    total_weight = sum(float(node["demand_weight"]) for node in nodes)
    total_volume = sum(float(node["demand_volume"]) for node in nodes)
    remaining_weight = total_weight
    remaining_volume = total_volume
    current_customer_id = 0
    current_time = float(depart_min)

    stops: list[StopRecord] = []
    arcs: list[ArcRecord] = []
    customer_ids: list[int] = []

    energy_cost = 0.0
    carbon_cost = 0.0
    carbon_kg = 0.0
    total_distance = 0.0
    penalty_cost = 0.0

    for node in nodes:
        service_node_id = int(node["node_id"])
        customer_id = int(node["customer_id"])
        customer_ids.append(customer_id)

        distance = _distance_km(problem, current_customer_id, customer_id)
        arc = calculate_arc_energy_cost(distance, current_time, vehicle, remaining_weight)
        arcs.append(
            ArcRecord(
                from_customer_id=current_customer_id,
                to_customer_id=customer_id,
                distance_km=distance,
                depart_min=current_time,
                arrival_min=arc.arrival_min,
                load_weight_kg=remaining_weight,
                load_volume_m3=remaining_volume,
                energy_cost=arc.energy_cost,
                carbon_cost=arc.carbon_cost,
                carbon_kg=arc.carbon_kg,
                consumption=arc.consumption,
            )
        )
        energy_cost += arc.energy_cost
        carbon_cost += arc.carbon_cost
        carbon_kg += arc.carbon_kg
        total_distance += distance

        penalty = calculate_time_window_penalty(
            arc.arrival_min,
            float(node["earliest_min"]),
            float(node["latest_min"]),
        )
        earliest_min = float(node["earliest_min"])
        latest_min = float(node["latest_min"])
        service_start = max(arc.arrival_min, earliest_min)
        departure = service_start + SERVICE_TIME_MIN
        demand_weight = float(node["demand_weight"])
        demand_volume = float(node["demand_volume"])
        after_weight = max(remaining_weight - demand_weight, 0.0)
        after_volume = max(remaining_volume - demand_volume, 0.0)

        stops.append(
            StopRecord(
                service_node_id=service_node_id,
                customer_id=customer_id,
                earliest_min=earliest_min,
                latest_min=latest_min,
                arrival_min=arc.arrival_min,
                wait_min=penalty.wait_min,
                late_min=penalty.late_min,
                service_start_min=service_start,
                departure_min=departure,
                demand_weight_kg=demand_weight,
                demand_volume_m3=demand_volume,
                load_before_service_kg=remaining_weight,
                load_before_service_m3=remaining_volume,
                load_after_service_kg=after_weight,
                load_after_service_m3=after_volume,
                penalty_cost=penalty.cost,
            )
        )
        penalty_cost += penalty.cost

        remaining_weight = after_weight
        remaining_volume = after_volume
        current_customer_id = customer_id
        current_time = departure

    if node_ids:
        return_distance = _distance_km(problem, current_customer_id, 0)
        return_arc = calculate_arc_energy_cost(return_distance, current_time, vehicle, remaining_weight)
        arcs.append(
            ArcRecord(
                from_customer_id=current_customer_id,
                to_customer_id=0,
                distance_km=return_distance,
                depart_min=current_time,
                arrival_min=return_arc.arrival_min,
                load_weight_kg=remaining_weight,
                load_volume_m3=remaining_volume,
                energy_cost=return_arc.energy_cost,
                carbon_cost=return_arc.carbon_cost,
                carbon_kg=return_arc.carbon_kg,
                consumption=return_arc.consumption,
            )
        )
        energy_cost += return_arc.energy_cost
        carbon_cost += return_arc.carbon_cost
        carbon_kg += return_arc.carbon_kg
        total_distance += return_distance
        return_min = return_arc.arrival_min
    else:
        return_min = current_time

    total_cost = fixed_cost + energy_cost + carbon_cost + penalty_cost
    return Route(
        vehicle_type_id=vehicle.vehicle_id,
        vehicle_type=vehicle,
        service_node_ids=node_ids,
        customer_ids=tuple(customer_ids),
        depart_min=float(depart_min),
        return_min=return_min,
        stops=tuple(stops),
        arcs=tuple(arcs),
        total_weight_kg=total_weight,
        total_volume_m3=total_volume,
        total_distance_km=total_distance,
        fixed_cost=float(fixed_cost),
        energy_cost=energy_cost,
        carbon_cost=carbon_cost,
        carbon_kg=carbon_kg,
        penalty_cost=penalty_cost,
        total_cost=total_cost,
        physical_vehicle_id=physical_vehicle_id,
        trip_id=trip_id,
    )


def evaluate_solution(
    routes: Iterable[Route],
    *,
    required_node_ids: Iterable[int] | None = None,
) -> Solution:
    """Aggregate evaluated routes and check node coverage."""

    route_tuple = tuple(routes)
    required = tuple(sorted(int(node_id) for node_id in (required_node_ids or ())))
    served = [node_id for route in route_tuple for node_id in route.service_node_ids]
    served_counts = Counter(served)
    duplicate_nodes = tuple(sorted(node_id for node_id, count in served_counts.items() if count > 1))
    missing_nodes = tuple(sorted(set(required) - set(served)))

    fixed_cost = sum(route.fixed_cost for route in route_tuple)
    energy_cost = sum(route.energy_cost for route in route_tuple)
    carbon_cost = sum(route.carbon_cost for route in route_tuple)
    carbon_kg = sum(route.carbon_kg for route in route_tuple)
    penalty_cost = sum(route.penalty_cost for route in route_tuple)
    total_distance = sum(route.total_distance_km for route in route_tuple)
    total_cost = sum(route.total_cost for route in route_tuple)
    trip_usage = Counter(route.vehicle_type_id for route in route_tuple)
    if any(route.physical_vehicle_id for route in route_tuple):
        by_type: dict[str, set[str]] = {}
        for route in route_tuple:
            if route.physical_vehicle_id:
                by_type.setdefault(route.vehicle_type_id, set()).add(route.physical_vehicle_id)
        physical_usage = Counter({vehicle_type_id: len(ids) for vehicle_type_id, ids in by_type.items()})
    else:
        physical_usage = trip_usage.copy()

    return Solution(
        routes=route_tuple,
        required_node_ids=required,
        missing_node_ids=missing_nodes,
        duplicate_node_ids=duplicate_nodes,
        fixed_cost=fixed_cost,
        energy_cost=energy_cost,
        carbon_cost=carbon_cost,
        carbon_kg=carbon_kg,
        penalty_cost=penalty_cost,
        total_distance_km=total_distance,
        total_cost=total_cost,
        vehicle_trip_usage_by_type=dict(sorted(trip_usage.items())),
        vehicle_physical_usage_by_type=dict(sorted(physical_usage.items())),
    )


def _resolve_vehicle_type(vehicle_type: VehicleType | str) -> VehicleType:
    if isinstance(vehicle_type, VehicleType):
        return vehicle_type
    if vehicle_type in VEHICLE_TYPES:
        return VEHICLE_TYPES[vehicle_type]
    raise ValueError(f"unknown vehicle type: {vehicle_type!r}")


def _service_node_records(problem: ProblemData, node_ids: Sequence[int]) -> list[dict[str, object]]:
    service_nodes = problem.service_nodes.set_index("node_id", drop=False)
    records: list[dict[str, object]] = []
    missing = [node_id for node_id in node_ids if node_id not in service_nodes.index]
    if missing:
        raise ValueError(f"unknown service node IDs: {missing}")
    for node_id in node_ids:
        records.append(service_nodes.loc[int(node_id)].to_dict())
    return records


def _distance_km(problem: ProblemData, from_customer_id: int, to_customer_id: int) -> float:
    return float(problem.distance_matrix.loc[int(from_customer_id), int(to_customer_id)])
