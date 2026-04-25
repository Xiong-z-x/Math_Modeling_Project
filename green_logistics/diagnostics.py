# -*- coding: utf-8 -*-
"""Diagnostics for residual lateness and Problem 2 policy readiness."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .constants import DAY_START_MIN, VEHICLE_TYPES
from .data_processing.loader import ProblemData
from .initial_solution import RouteSpec
from .policies import GreenZonePolicyEvaluator
from .scheduler import preferred_departure_min
from .solution import Route, Solution, evaluate_route
from .travel_time import calculate_arrival_time


def diagnose_late_stops(problem: ProblemData, solution: Solution) -> pd.DataFrame:
    """Classify late stops in a scheduled solution."""

    node_lookup = _node_lookup(problem)
    split_counts = problem.service_nodes.groupby("customer_id")["node_id"].count().to_dict()
    route_positions = _trip_positions_by_vehicle(solution)
    previous_routes = _previous_routes_by_vehicle(solution)
    rows: list[dict[str, Any]] = []

    for route_index, route in enumerate(solution.routes, start=1):
        trip_position = route_positions.get(id(route), 1)
        previous_route = previous_routes.get(id(route))
        previous_green_count = _route_green_stop_count(problem, previous_route, node_lookup)
        previous_fuel_feasible = _route_fuel_feasible(problem, previous_route) if previous_route is not None else False
        fresh_route = _fresh_route_for_same_trip(problem, route)
        fresh_by_node = {stop.service_node_id: stop for stop in fresh_route.stops}

        for stop in route.stops:
            if stop.late_min <= 1e-9:
                continue
            node = node_lookup[int(stop.service_node_id)]
            distance = float(problem.distance_matrix.loc[0, int(stop.customer_id)])
            direct_arrival = calculate_arrival_time(distance, DAY_START_MIN)
            direct_late = max(0.0, direct_arrival - float(stop.latest_min))
            fresh_stop = fresh_by_node[int(stop.service_node_id)]
            fresh_late = float(fresh_stop.late_min)
            classification = _late_classification(
                direct_late_min=direct_late,
                fresh_route_late_min=fresh_late,
                trip_position_on_vehicle=trip_position,
                route_depart_min=route.depart_min,
            )
            is_green = bool(node.get("is_green_zone", False))
            is_ev = VEHICLE_TYPES[route.vehicle_type_id].energy_type == "ev"
            ev_cascade_blocked = (
                is_green
                and is_ev
                and direct_late <= 1e-9
                and fresh_late <= 1e-9
                and previous_route is not None
                and trip_position > 1
            )
            policy_wait_late = (
                VEHICLE_TYPES[route.vehicle_type_id].energy_type == "fuel"
                and is_green
                and route.depart_min > DAY_START_MIN + 1e-9
                and stop.arrival_min >= GreenZonePolicyEvaluator().end_min - 1e-9
                and direct_late <= 1e-9
            )
            previous_trip_id = "" if previous_route is None else (previous_route.trip_id or "")
            rows.append(
                {
                    "route_index": route_index,
                    "trip_id": route.trip_id or f"R{route_index:04d}",
                    "physical_vehicle_id": route.physical_vehicle_id or "",
                    "vehicle_type": route.vehicle_type_id,
                    "service_node_id": int(stop.service_node_id),
                    "customer_id": int(stop.customer_id),
                    "earliest_min": float(stop.earliest_min),
                    "latest_min": float(stop.latest_min),
                    "arrival_min": float(stop.arrival_min),
                    "late_min": float(stop.late_min),
                    "route_depart_min": float(route.depart_min),
                    "route_return_min": float(route.return_min),
                    "trip_position_on_vehicle": trip_position,
                    "direct_arrival_from_depot_0800": direct_arrival,
                    "direct_late_min": direct_late,
                    "fresh_route_arrival_min": float(fresh_stop.arrival_min),
                    "fresh_route_late_min": fresh_late,
                    "same_customer_split_count": int(split_counts.get(int(stop.customer_id), 1)),
                    "is_green_zone": is_green,
                    "policy_induced_late": bool(ev_cascade_blocked or policy_wait_late),
                    "ev_cascade_blocked": bool(ev_cascade_blocked),
                    "same_vehicle_previous_trip_id": previous_trip_id,
                    "previous_route_green_stop_count": int(previous_green_count),
                    "previous_route_fuel_feasible": bool(previous_fuel_feasible),
                    "previous_route_arrive_before_restricted_end": bool(
                        previous_route is not None and previous_route.return_min < GreenZonePolicyEvaluator().end_min
                    ),
                    "blocking_previous_trip_id": previous_trip_id if ev_cascade_blocked else "",
                    "blocking_trip_fuel_feasible": bool(ev_cascade_blocked and previous_fuel_feasible),
                    "policy_wait_late": bool(policy_wait_late),
                    "classification": classification,
                }
            )

    return pd.DataFrame(rows)


def diagnose_green_zone_capacity(problem: ProblemData) -> pd.DataFrame:
    """Summarize green-zone demand and one-trip EV capacity."""

    nodes = problem.service_nodes.copy()
    green_nodes = nodes[nodes["is_green_zone"].astype(bool)]
    e1 = VEHICLE_TYPES["E1"]
    e2 = VEHICLE_TYPES["E2"]
    ev_types = [vehicle for vehicle in VEHICLE_TYPES.values() if vehicle.energy_type == "ev"]
    row = {
        "green_customer_count": int(len(problem.active_green_customer_ids)),
        "green_service_node_count": int(len(green_nodes)),
        "green_total_weight_kg": float(green_nodes["demand_weight"].sum()),
        "green_total_volume_m3": float(green_nodes["demand_volume"].sum()),
        "ev_total_weight_capacity_once_kg": float(sum(vehicle.max_weight_kg * vehicle.count for vehicle in ev_types)),
        "ev_total_volume_capacity_once_m3": float(sum(vehicle.max_volume_m3 * vehicle.count for vehicle in ev_types)),
        "e1_capacity_once_weight_kg": float(e1.max_weight_kg * e1.count),
        "e1_capacity_once_volume_m3": float(e1.max_volume_m3 * e1.count),
        "e2_capacity_once_weight_kg": float(e2.max_weight_kg * e2.count),
        "e2_capacity_once_volume_m3": float(e2.max_volume_m3 * e2.count),
        "green_nodes_feasible_by_E2_count": int(
            (
                (green_nodes["demand_weight"] <= e2.max_weight_kg + 1e-9)
                & (green_nodes["demand_volume"] <= e2.max_volume_m3 + 1e-9)
            ).sum()
        ),
        "green_nodes_need_E1_count": int(
            (
                (green_nodes["demand_weight"] > e2.max_weight_kg + 1e-9)
                | (green_nodes["demand_volume"] > e2.max_volume_m3 + 1e-9)
            ).sum()
        ),
    }
    return pd.DataFrame([row])


def diagnose_problem2_policy_conflicts(problem: ProblemData, solution: Solution) -> pd.DataFrame:
    """Identify stops that would violate the Problem 2 green-zone policy."""

    node_lookup = _node_lookup(problem)
    policy = GreenZonePolicyEvaluator()
    rows: list[dict[str, Any]] = []
    for route_index, route in enumerate(solution.routes, start=1):
        is_fuel = route.vehicle_type.energy_type == "fuel"
        for stop in route.stops:
            node = node_lookup[int(stop.service_node_id)]
            is_green = bool(node.get("is_green_zone", False))
            in_restricted_window = policy.start_min <= stop.arrival_min < policy.end_min
            would_violate = policy.stop_violation(problem, stop, route.vehicle_type_id)
            rows.append(
                {
                    "route_index": route_index,
                    "trip_id": route.trip_id or f"R{route_index:04d}",
                    "physical_vehicle_id": route.physical_vehicle_id or "",
                    "vehicle_type": route.vehicle_type_id,
                    "service_node_id": int(stop.service_node_id),
                    "customer_id": int(stop.customer_id),
                    "arrival_min": float(stop.arrival_min),
                    "is_green_zone": is_green,
                    "is_fuel_vehicle": is_fuel,
                    "would_violate_problem2_policy": would_violate,
                }
            )
    return pd.DataFrame(rows)


def write_problem_diagnostics(problem: ProblemData, solution: Solution, output_dir: Path) -> dict[str, Path]:
    """Write diagnostics CSV/Markdown files for Problem 1 handoff."""

    output_dir.mkdir(parents=True, exist_ok=True)
    late = diagnose_late_stops(problem, solution)
    green = diagnose_green_zone_capacity(problem)
    conflicts = diagnose_problem2_policy_conflicts(problem, solution)

    paths = {
        "late_stop_diagnosis_csv": output_dir / "late_stop_diagnosis.csv",
        "late_stop_diagnosis_md": output_dir / "late_stop_diagnosis.md",
        "green_zone_capacity_csv": output_dir / "green_zone_capacity.csv",
        "problem2_policy_conflicts_csv": output_dir / "problem2_policy_conflicts.csv",
    }
    late.to_csv(paths["late_stop_diagnosis_csv"], index=False, encoding="utf-8-sig")
    green.to_csv(paths["green_zone_capacity_csv"], index=False, encoding="utf-8-sig")
    conflicts.to_csv(paths["problem2_policy_conflicts_csv"], index=False, encoding="utf-8-sig")
    paths["late_stop_diagnosis_md"].write_text(_late_markdown(late), encoding="utf-8")
    return paths


def _fresh_route_for_same_trip(problem: ProblemData, route: Route) -> Route:
    spec = RouteSpec(route.vehicle_type_id, route.service_node_ids)
    depart_min = preferred_departure_min(problem, spec, available_min=DAY_START_MIN)
    return evaluate_route(problem, route.vehicle_type_id, route.service_node_ids, depart_min=depart_min)


def _late_classification(
    *,
    direct_late_min: float,
    fresh_route_late_min: float,
    trip_position_on_vehicle: int,
    route_depart_min: float,
) -> str:
    if direct_late_min > 1e-9:
        return "Type A direct-infeasible"
    if fresh_route_late_min > 1e-9:
        return "Type C route-order/local-optimum"
    if trip_position_on_vehicle > 1 and route_depart_min > DAY_START_MIN + 1e-9:
        return "Type B multi-trip cascade"
    return "Type C route-order/local-optimum"


def _trip_positions_by_vehicle(solution: Solution) -> dict[int, int]:
    positions: dict[int, int] = {}
    by_vehicle: dict[str, list[Route]] = {}
    for route in solution.routes:
        key = route.physical_vehicle_id or f"route-{id(route)}"
        by_vehicle.setdefault(key, []).append(route)
    for routes in by_vehicle.values():
        for position, route in enumerate(sorted(routes, key=lambda item: item.depart_min), start=1):
            positions[id(route)] = position
    return positions


def _previous_routes_by_vehicle(solution: Solution) -> dict[int, Route | None]:
    previous: dict[int, Route | None] = {}
    by_vehicle: dict[str, list[Route]] = {}
    for route in solution.routes:
        key = route.physical_vehicle_id or f"route-{id(route)}"
        by_vehicle.setdefault(key, []).append(route)
    for routes in by_vehicle.values():
        prior: Route | None = None
        for route in sorted(routes, key=lambda item: item.depart_min):
            previous[id(route)] = prior
            prior = route
    return previous


def _route_green_stop_count(
    problem: ProblemData,
    route: Route | None,
    node_lookup: dict[int, dict[str, object]] | None = None,
) -> int:
    if route is None:
        return 0
    lookup = node_lookup or _node_lookup(problem)
    return sum(1 for node_id in route.service_node_ids if bool(lookup[int(node_id)].get("is_green_zone", False)))


def _route_fuel_feasible(problem: ProblemData, route: Route | None) -> bool:
    if route is None:
        return False
    policy = GreenZonePolicyEvaluator()
    for vehicle_type_id, vehicle in VEHICLE_TYPES.items():
        if vehicle.energy_type != "fuel":
            continue
        if route.total_weight_kg > vehicle.max_weight_kg + 1e-9:
            continue
        if route.total_volume_m3 > vehicle.max_volume_m3 + 1e-9:
            continue
        candidate = evaluate_route(
            problem,
            vehicle_type_id,
            route.service_node_ids,
            depart_min=route.depart_min,
            fixed_cost=route.fixed_cost,
        )
        if policy.is_route_allowed(problem, candidate):
            return True
    return False


def _node_lookup(problem: ProblemData) -> dict[int, dict[str, object]]:
    return {
        int(row["node_id"]): row
        for row in problem.service_nodes.to_dict(orient="records")
    }


def _late_markdown(late: pd.DataFrame) -> str:
    lines = [
        "# Late Stop Diagnosis",
        "",
        "Type A means direct travel from depot at 08:00 is already late.",
        "Type B means the same trip can be on time when started fresh, but physical-vehicle reuse delays it.",
        "Type C means route order or trip composition still causes lateness even when the trip starts fresh.",
        "",
    ]
    if late.empty:
        lines.append("No late stops.")
    else:
        counts = late["classification"].value_counts().to_dict()
        lines.append("## Counts")
        lines.extend(f"- {name}: {count}" for name, count in sorted(counts.items()))
        lines.append("")
        lines.append("## Stops")
        for row in late.itertuples():
            lines.append(
                f"- {row.trip_id} node {row.service_node_id} customer {row.customer_id}: "
                f"late {row.late_min:.2f} min, {row.classification}"
            )
    lines.append("")
    return "\n".join(lines)
