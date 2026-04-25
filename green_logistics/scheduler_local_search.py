# -*- coding: utf-8 -*-
"""Small scheduler-level repairs for residual late trips."""

from __future__ import annotations

from typing import Mapping, Sequence

from .constants import VEHICLE_TYPES
from .data_processing.loader import ProblemData
from .initial_solution import RouteSpec
from .metrics import SearchScoreWeights, score_solution, solution_quality_metrics
from .scheduler import SchedulingConfig, route_demand, schedule_route_specs
from .solution import Route, Solution


def rescue_late_routes(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    solution: Solution | None = None,
    *,
    vehicle_counts: Mapping[str, int] | None = None,
    config: SchedulingConfig | None = None,
    max_passes: int = 2,
) -> tuple[tuple[RouteSpec, ...], Solution]:
    """Try targeted retyping/splitting moves for routes with actual lateness."""

    cfg = config or SchedulingConfig()
    current_specs = tuple(specs)
    current_solution = solution or schedule_route_specs(
        problem,
        current_specs,
        vehicle_counts=vehicle_counts,
        config=cfg,
    )

    for _pass_index in range(max_passes):
        improved = False
        late_routes = sorted(
            (route for route in current_solution.routes if any(stop.late_min > 1e-9 for stop in route.stops)),
            key=lambda route: max((stop.late_min for stop in route.stops), default=0.0),
            reverse=True,
        )
        for route in late_routes:
            for candidate_specs in _candidate_spec_sets(problem, current_specs, route):
                candidate_solution = schedule_route_specs(
                    problem,
                    candidate_specs,
                    vehicle_counts=vehicle_counts,
                    config=cfg,
                )
                if _is_quality_better(candidate_solution, current_solution, cfg.score_weights):
                    current_specs = candidate_specs
                    current_solution = candidate_solution
                    improved = True
                    break
            if improved:
                break
        if not improved:
            break

    return current_specs, current_solution


def _candidate_spec_sets(
    problem: ProblemData,
    specs: tuple[RouteSpec, ...],
    route: Route,
) -> tuple[tuple[RouteSpec, ...], ...]:
    candidates: list[tuple[RouteSpec, ...]] = []
    route_nodes = tuple(int(node_id) for node_id in route.service_node_ids)
    route_index = _find_spec_index(specs, route_nodes)
    if route_index is None:
        return ()

    for vehicle_type_id in _feasible_vehicle_type_ids(problem, route_nodes):
        if vehicle_type_id == route.vehicle_type_id:
            continue
        candidates.append(_replace_spec(specs, route_index, (RouteSpec(vehicle_type_id, route_nodes),)))

    if len(route_nodes) > 1:
        late_positions = [
            index for index, stop in enumerate(route.stops)
            if stop.late_min > 1e-9
        ]
        split_positions = set(range(1, len(route_nodes)))
        if late_positions:
            first_late = late_positions[0]
            if first_late > 0:
                split_positions.add(first_late)
            if first_late + 1 < len(route_nodes):
                split_positions.add(first_late + 1)

        for split_pos in sorted(split_positions):
            left = route_nodes[:split_pos]
            right = route_nodes[split_pos:]
            replacement = tuple(
                spec for spec in (_retyped_spec(problem, left), _retyped_spec(problem, right)) if spec is not None
            )
            if len(replacement) == 2:
                candidates.append(_replace_spec(specs, route_index, replacement))

        singleton_replacement = tuple(
            spec for spec in (_retyped_spec(problem, (node_id,)) for node_id in route_nodes) if spec is not None
        )
        if len(singleton_replacement) == len(route_nodes):
            candidates.append(_replace_spec(specs, route_index, singleton_replacement))

    return tuple(dict.fromkeys(candidates))


def _is_quality_better(candidate: Solution, incumbent: Solution, weights: SearchScoreWeights) -> bool:
    candidate_metrics = solution_quality_metrics(candidate)
    incumbent_metrics = solution_quality_metrics(incumbent)
    candidate_key = (
        candidate_metrics.return_after_midnight_count,
        candidate_metrics.late_stop_count,
        round(candidate_metrics.max_late_min, 9),
        round(candidate_metrics.total_late_min, 9),
        round(score_solution(candidate, weights), 9),
        round(candidate.total_cost, 9),
    )
    incumbent_key = (
        incumbent_metrics.return_after_midnight_count,
        incumbent_metrics.late_stop_count,
        round(incumbent_metrics.max_late_min, 9),
        round(incumbent_metrics.total_late_min, 9),
        round(score_solution(incumbent, weights), 9),
        round(incumbent.total_cost, 9),
    )
    return candidate.is_complete and candidate.is_capacity_feasible and candidate_key < incumbent_key


def _replace_spec(
    specs: tuple[RouteSpec, ...],
    route_index: int,
    replacement: Sequence[RouteSpec],
) -> tuple[RouteSpec, ...]:
    return specs[:route_index] + tuple(replacement) + specs[route_index + 1 :]


def _find_spec_index(specs: Sequence[RouteSpec], route_nodes: tuple[int, ...]) -> int | None:
    for index, spec in enumerate(specs):
        if tuple(spec.service_node_ids) == route_nodes:
            return index
    return None


def _retyped_spec(problem: ProblemData, service_node_ids: Sequence[int]) -> RouteSpec | None:
    if not service_node_ids:
        return None
    vehicle_type_id = _smallest_feasible_vehicle_id_or_none(problem, service_node_ids)
    if vehicle_type_id is None:
        return None
    return RouteSpec(vehicle_type_id, tuple(int(node_id) for node_id in service_node_ids))


def _feasible_vehicle_type_ids(problem: ProblemData, service_node_ids: Sequence[int]) -> tuple[str, ...]:
    weight, volume = route_demand(problem, service_node_ids)
    feasible: list[str] = []
    for vehicle_type_id, vehicle in VEHICLE_TYPES.items():
        if weight <= vehicle.max_weight_kg + 1e-9 and volume <= vehicle.max_volume_m3 + 1e-9:
            feasible.append(vehicle_type_id)
    return tuple(feasible)


def _smallest_feasible_vehicle_id_or_none(problem: ProblemData, service_node_ids: Sequence[int]) -> str | None:
    feasible = _feasible_vehicle_type_ids(problem, service_node_ids)
    for vehicle_type_id in ("F3", "F2", "F1", "E2", "E1"):
        if vehicle_type_id in feasible:
            return vehicle_type_id
    return None
