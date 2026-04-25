# -*- coding: utf-8 -*-
"""Lightweight trip descriptors for scheduling, diagnostics, and policies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .constants import DAY_START_MIN
from .data_processing.loader import ProblemData
from .initial_solution import RouteSpec
from .scheduler import preferred_departure_min, service_node_lookup
from .solution import evaluate_route


@dataclass(frozen=True)
class TripDescriptor:
    """Compact description of an unevaluated depot-to-depot trip."""

    vehicle_type_id: str
    service_node_ids: tuple[int, ...]
    customer_ids: tuple[int, ...]
    total_weight_kg: float
    total_volume_m3: float
    earliest_window_min: float
    latest_window_min: float
    preferred_departure_min: float
    estimated_duration_min: float
    min_latest_slack_min: float
    is_green_zone_touched: bool
    green_stop_count: int


def describe_route_spec(problem: ProblemData, spec: RouteSpec) -> TripDescriptor:
    """Build a descriptor for a route spec without changing solver behavior."""

    lookup = service_node_lookup(problem)
    records = [lookup[int(node_id)] for node_id in spec.service_node_ids]
    customer_ids = tuple(int(record["customer_id"]) for record in records)
    total_weight = sum(float(record["demand_weight"]) for record in records)
    total_volume = sum(float(record["demand_volume"]) for record in records)
    earliest = min(float(record["earliest_min"]) for record in records)
    latest = min(float(record["latest_min"]) for record in records)
    green_count = sum(1 for record in records if bool(record.get("is_green_zone", False)))
    depart_min = preferred_departure_min(problem, spec, available_min=DAY_START_MIN)
    route = evaluate_route(problem, spec.vehicle_type_id, spec.service_node_ids, depart_min=depart_min)
    min_slack = min((stop.latest_min - stop.arrival_min for stop in route.stops), default=0.0)

    return TripDescriptor(
        vehicle_type_id=spec.vehicle_type_id,
        service_node_ids=tuple(int(node_id) for node_id in spec.service_node_ids),
        customer_ids=customer_ids,
        total_weight_kg=total_weight,
        total_volume_m3=total_volume,
        earliest_window_min=earliest,
        latest_window_min=latest,
        preferred_departure_min=depart_min,
        estimated_duration_min=route.return_min - route.depart_min,
        min_latest_slack_min=float(min_slack),
        is_green_zone_touched=green_count > 0,
        green_stop_count=green_count,
    )


def describe_route_specs(problem: ProblemData, specs: Sequence[RouteSpec]) -> tuple[TripDescriptor, ...]:
    """Describe multiple route specs."""

    return tuple(describe_route_spec(problem, spec) for spec in specs)
