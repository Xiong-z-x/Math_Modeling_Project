# -*- coding: utf-8 -*-
"""Dynamic-event state helpers for Problem 3."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

import pandas as pd

from .data_processing.loader import ProblemData
from .solution import Solution


DynamicEventType = Literal["cancel", "new_order", "time_window_change", "address_change"]


@dataclass(frozen=True)
class DynamicEvent:
    """One scenario event used by the Problem 3 rolling-horizon layer."""

    event_type: DynamicEventType
    event_time_min: float
    service_node_id: int | None = None
    new_service_node_id: int | None = None
    proxy_customer_id: int | None = None
    demand_weight_kg: float | None = None
    demand_volume_m3: float | None = None
    earliest_min: float | None = None
    latest_min: float | None = None
    description: str = ""


@dataclass(frozen=True)
class RouteSnapshot:
    """Route-level execution state at a dynamic event time."""

    route_index: int
    trip_id: str
    physical_vehicle_id: str
    vehicle_type_id: str
    depart_min: float
    return_min: float
    service_node_ids: tuple[int, ...]
    status: str
    fixed_cost: float


@dataclass(frozen=True)
class VisitSnapshot:
    """Stop-level execution state at a dynamic event time."""

    route_index: int
    trip_id: str
    physical_vehicle_id: str
    vehicle_type_id: str
    stop_index: int
    service_node_id: int
    customer_id: int
    arrival_min: float
    departure_min: float
    status: str


@dataclass(frozen=True)
class DynamicSnapshot:
    """Frozen/current/future partition for one baseline solution."""

    event_time_min: float
    routes: tuple[RouteSnapshot, ...]
    visits: tuple[VisitSnapshot, ...]
    locked_route_ids: tuple[str, ...]
    adjustable_route_ids: tuple[str, ...]
    completed_node_ids: tuple[int, ...]
    locked_node_ids: tuple[int, ...]
    adjustable_node_ids: tuple[int, ...]


@dataclass(frozen=True)
class DynamicProblemUpdate:
    """Problem data after applying a dynamic event to the adjustable future."""

    problem: ProblemData
    event: DynamicEvent
    required_node_ids: tuple[int, ...]
    residual_node_ids: tuple[int, ...]
    cancelled_node_ids: tuple[int, ...] = ()
    added_node_ids: tuple[int, ...] = ()
    changed_node_ids: tuple[int, ...] = ()
    note: str = ""


def build_dynamic_snapshot(solution: Solution, event_time_min: float) -> DynamicSnapshot:
    """Classify a scheduled solution into locked and adjustable parts."""

    route_rows: list[RouteSnapshot] = []
    visit_rows: list[VisitSnapshot] = []
    locked_route_ids: list[str] = []
    adjustable_route_ids: list[str] = []
    completed_nodes: list[int] = []
    locked_nodes: list[int] = []
    adjustable_nodes: list[int] = []
    event_time = float(event_time_min)

    for route_index, route in enumerate(solution.routes, start=1):
        trip_id = route.trip_id or f"T{route_index:04d}"
        physical_vehicle_id = route.physical_vehicle_id or ""
        if route.depart_min > event_time + 1e-9:
            route_status = "unstarted_adjustable"
            adjustable_route_ids.append(trip_id)
        elif route.return_min <= event_time + 1e-9:
            route_status = "locked_completed"
            locked_route_ids.append(trip_id)
        else:
            route_status = "locked_active"
            locked_route_ids.append(trip_id)

        route_rows.append(
            RouteSnapshot(
                route_index=route_index,
                trip_id=trip_id,
                physical_vehicle_id=physical_vehicle_id,
                vehicle_type_id=route.vehicle_type_id,
                depart_min=float(route.depart_min),
                return_min=float(route.return_min),
                service_node_ids=tuple(int(node_id) for node_id in route.service_node_ids),
                status=route_status,
                fixed_cost=float(route.fixed_cost),
            )
        )

        for stop_index, stop in enumerate(route.stops, start=1):
            node_id = int(stop.service_node_id)
            if stop.departure_min <= event_time + 1e-9:
                visit_status = "completed"
                completed_nodes.append(node_id)
                locked_nodes.append(node_id)
            elif route_status == "unstarted_adjustable":
                visit_status = "unstarted_adjustable"
                adjustable_nodes.append(node_id)
            else:
                visit_status = "locked_onboard"
                locked_nodes.append(node_id)

            visit_rows.append(
                VisitSnapshot(
                    route_index=route_index,
                    trip_id=trip_id,
                    physical_vehicle_id=physical_vehicle_id,
                    vehicle_type_id=route.vehicle_type_id,
                    stop_index=stop_index,
                    service_node_id=node_id,
                    customer_id=int(stop.customer_id),
                    arrival_min=float(stop.arrival_min),
                    departure_min=float(stop.departure_min),
                    status=visit_status,
                )
            )

    return DynamicSnapshot(
        event_time_min=event_time,
        routes=tuple(route_rows),
        visits=tuple(visit_rows),
        locked_route_ids=tuple(locked_route_ids),
        adjustable_route_ids=tuple(adjustable_route_ids),
        completed_node_ids=tuple(sorted(completed_nodes)),
        locked_node_ids=tuple(sorted(set(locked_nodes))),
        adjustable_node_ids=tuple(sorted(adjustable_nodes)),
    )


def apply_dynamic_event(
    problem: ProblemData,
    snapshot: DynamicSnapshot,
    event: DynamicEvent,
) -> DynamicProblemUpdate:
    """Apply one event to the future residual problem without touching locked nodes."""

    if abs(float(event.event_time_min) - snapshot.event_time_min) > 1e-9:
        raise ValueError("event time does not match dynamic snapshot time")

    service_nodes = problem.service_nodes.copy(deep=True).reset_index(drop=True)
    node_to_customer = dict(problem.node_to_customer)
    adjustable = set(snapshot.adjustable_node_ids)
    cancelled: tuple[int, ...] = ()
    added: tuple[int, ...] = ()
    changed: tuple[int, ...] = ()
    note = ""

    if event.event_type == "cancel":
        node_id = _require_service_node(event)
        _ensure_adjustable(node_id, adjustable)
        service_nodes = service_nodes[service_nodes["node_id"].astype(int) != node_id].reset_index(drop=True)
        node_to_customer.pop(node_id, None)
        cancelled = (node_id,)
        adjustable.discard(node_id)
        note = f"cancelled adjustable service node {node_id}"

    elif event.event_type == "new_order":
        node_id = _require_new_service_node(event, service_nodes)
        proxy_customer_id = _require_proxy_customer(event, problem)
        service_nodes = pd.concat(
            [
                service_nodes,
                pd.DataFrame(
                    [
                        {
                            "node_id": node_id,
                            "customer_id": proxy_customer_id,
                            "split_index": 1,
                            "split_count": 1,
                            "demand_weight": _require_float(event.demand_weight_kg, "demand_weight_kg"),
                            "demand_volume": _require_float(event.demand_volume_m3, "demand_volume_m3"),
                            "earliest_min": _require_float(event.earliest_min, "earliest_min"),
                            "latest_min": _require_float(event.latest_min, "latest_min"),
                            "is_green_zone": _is_green_customer(problem, proxy_customer_id),
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
        node_to_customer[node_id] = proxy_customer_id
        adjustable.add(node_id)
        added = (node_id,)
        note = f"added proxy service node {node_id} at customer {proxy_customer_id}"

    elif event.event_type == "time_window_change":
        node_id = _require_service_node(event)
        _ensure_adjustable(node_id, adjustable)
        mask = service_nodes["node_id"].astype(int) == node_id
        if event.earliest_min is not None:
            service_nodes.loc[mask, "earliest_min"] = float(event.earliest_min)
        if event.latest_min is not None:
            service_nodes.loc[mask, "latest_min"] = float(event.latest_min)
        changed = (node_id,)
        note = f"changed time window for adjustable service node {node_id}"

    elif event.event_type == "address_change":
        node_id = _require_service_node(event)
        _ensure_adjustable(node_id, adjustable)
        proxy_customer_id = _require_proxy_customer(event, problem)
        mask = service_nodes["node_id"].astype(int) == node_id
        service_nodes.loc[mask, "customer_id"] = proxy_customer_id
        service_nodes.loc[mask, "is_green_zone"] = _is_green_customer(problem, proxy_customer_id)
        node_to_customer[node_id] = proxy_customer_id
        changed = (node_id,)
        note = f"changed address for node {node_id} to proxy customer {proxy_customer_id}"

    else:
        raise ValueError(f"unsupported dynamic event type: {event.event_type!r}")

    service_nodes = service_nodes.sort_values("node_id").reset_index(drop=True)
    updated_problem = replace(
        problem,
        service_nodes=service_nodes,
        node_to_customer=node_to_customer,
        active_green_customer_ids=_active_green_customer_ids(problem, service_nodes),
    )
    all_required = tuple(sorted(service_nodes["node_id"].astype(int).tolist()))
    residual = tuple(sorted(node_id for node_id in adjustable if node_id in set(all_required)))
    return DynamicProblemUpdate(
        problem=updated_problem,
        event=event,
        required_node_ids=all_required,
        residual_node_ids=residual,
        cancelled_node_ids=cancelled,
        added_node_ids=added,
        changed_node_ids=changed,
        note=note,
    )


def _require_service_node(event: DynamicEvent) -> int:
    if event.service_node_id is None:
        raise ValueError(f"{event.event_type} event requires service_node_id")
    return int(event.service_node_id)


def _require_new_service_node(event: DynamicEvent, service_nodes: pd.DataFrame) -> int:
    if event.new_service_node_id is None:
        raise ValueError("new_order event requires new_service_node_id")
    node_id = int(event.new_service_node_id)
    existing = set(service_nodes["node_id"].astype(int).tolist())
    if node_id in existing:
        raise ValueError(f"new service node already exists: {node_id}")
    return node_id


def _require_proxy_customer(event: DynamicEvent, problem: ProblemData) -> int:
    if event.proxy_customer_id is None:
        raise ValueError(f"{event.event_type} event requires proxy_customer_id")
    customer_id = int(event.proxy_customer_id)
    if customer_id not in set(int(value) for value in problem.distance_matrix.index):
        raise ValueError(f"proxy customer {customer_id} is missing from distance matrix")
    return customer_id


def _require_float(value: float | None, field_name: str) -> float:
    if value is None:
        raise ValueError(f"new_order event requires {field_name}")
    return float(value)


def _ensure_adjustable(node_id: int, adjustable: set[int]) -> None:
    if node_id not in adjustable:
        raise ValueError(f"service node {node_id} is locked at the event time")


def _is_green_customer(problem: ProblemData, customer_id: int) -> bool:
    return int(customer_id) in set(int(value) for value in problem.green_customer_ids)


def _active_green_customer_ids(problem: ProblemData, service_nodes: pd.DataFrame) -> list[int]:
    green_customers = set(int(value) for value in problem.green_customer_ids)
    active = sorted(
        {
            int(row["customer_id"])
            for row in service_nodes.to_dict(orient="records")
            if int(row["customer_id"]) in green_customers
        }
    )
    return active
