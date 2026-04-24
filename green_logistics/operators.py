# -*- coding: utf-8 -*-
"""Destroy and repair operators for ALNS."""

from __future__ import annotations

from random import Random
from typing import Callable, Sequence

from .constants import DAY_START_MIN, VEHICLE_TYPES
from .data_processing.loader import ProblemData
from .initial_solution import RouteSpec
from .solution import evaluate_route


DestroyOperator = Callable[[ProblemData, Sequence[RouteSpec], Random, int], tuple[tuple[RouteSpec, ...], tuple[int, ...]]]
RepairOperator = Callable[[ProblemData, Sequence[RouteSpec], Sequence[int]], tuple[RouteSpec, ...]]


def random_remove(
    specs: Sequence[RouteSpec],
    rng: Random,
    *,
    remove_count: int,
) -> tuple[tuple[RouteSpec, ...], tuple[int, ...]]:
    """Remove random service nodes from route specs."""

    all_nodes = [node_id for spec in specs for node_id in spec.service_node_ids]
    selected = tuple(rng.sample(all_nodes, min(remove_count, len(all_nodes))))
    return _remove_nodes(specs, selected), selected


def random_remove_operator(
    _problem: ProblemData,
    specs: Sequence[RouteSpec],
    rng: Random,
    remove_count: int,
) -> tuple[tuple[RouteSpec, ...], tuple[int, ...]]:
    return random_remove(specs, rng, remove_count=remove_count)


def worst_cost_remove(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    _rng: Random,
    remove_count: int,
) -> tuple[tuple[RouteSpec, ...], tuple[int, ...]]:
    """Remove nodes with largest local route-cost contribution."""

    contributions: list[tuple[float, int]] = []
    for spec in specs:
        if not spec.service_node_ids:
            continue
        old_cost = _local_route_cost(problem, spec)
        for node_id in spec.service_node_ids:
            remaining = tuple(item for item in spec.service_node_ids if item != node_id)
            new_cost = _local_route_cost(problem, _retyped_spec(problem, remaining)) if remaining else 0.0
            contributions.append((old_cost - new_cost, node_id))
    selected = tuple(node_id for _score, node_id in sorted(contributions, reverse=True)[:remove_count])
    return _remove_nodes(specs, selected), selected


def related_remove(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    rng: Random,
    remove_count: int,
) -> tuple[tuple[RouteSpec, ...], tuple[int, ...]]:
    """Remove nodes related by customer distance and time-window proximity."""

    all_nodes = [node_id for spec in specs for node_id in spec.service_node_ids]
    if not all_nodes:
        return tuple(specs), ()

    lookup = _node_lookup(problem)
    seed = rng.choice(all_nodes)
    seed_record = lookup[seed]
    seed_customer = int(seed_record["customer_id"])
    seed_earliest = float(seed_record["earliest_min"])
    scored: list[tuple[float, int]] = []
    for node_id in all_nodes:
        record = lookup[node_id]
        customer_id = int(record["customer_id"])
        distance = float(problem.distance_matrix.loc[seed_customer, customer_id])
        time_gap = abs(seed_earliest - float(record["earliest_min"]))
        same_customer_bonus = -1000.0 if customer_id == seed_customer else 0.0
        scored.append((distance * 10.0 + time_gap + same_customer_bonus, node_id))
    selected = tuple(node_id for _score, node_id in sorted(scored)[:remove_count])
    return _remove_nodes(specs, selected), selected


def time_penalty_remove(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    _rng: Random,
    remove_count: int,
) -> tuple[tuple[RouteSpec, ...], tuple[int, ...]]:
    """Remove nodes with largest current wait/late penalty in local routes."""

    penalties: list[tuple[float, int]] = []
    for spec in specs:
        route = evaluate_route(problem, spec.vehicle_type_id, spec.service_node_ids, depart_min=DAY_START_MIN)
        for stop in route.stops:
            penalties.append((stop.penalty_cost, stop.service_node_id))
    selected = tuple(node_id for _score, node_id in sorted(penalties, reverse=True)[:remove_count])
    return _remove_nodes(specs, selected), selected


def greedy_insert(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    removed_node_ids: Sequence[int],
) -> tuple[RouteSpec, ...]:
    """Insert each node into the cheapest local position."""

    current = tuple(specs)
    for node_id in removed_node_ids:
        current = _apply_insertion(current, _best_insertion(problem, current, int(node_id)))
    return current


def regret2_insert(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    removed_node_ids: Sequence[int],
) -> tuple[RouteSpec, ...]:
    """Regret-2 repair: insert nodes whose second-best option is much worse."""

    current = tuple(specs)
    remaining = [int(node_id) for node_id in removed_node_ids]
    while remaining:
        best_choice: tuple[float, int, _Insertion] | None = None
        for node_id in remaining:
            options = _insertion_options(problem, current, node_id)
            first = options[0]
            second_delta = options[1].delta_cost if len(options) > 1 else first.delta_cost + 1000.0
            regret = second_delta - first.delta_cost
            if best_choice is None or regret > best_choice[0]:
                best_choice = (regret, node_id, first)
        assert best_choice is not None
        current = _apply_insertion(current, best_choice[2])
        remaining.remove(best_choice[1])
    return current


def time_oriented_insert(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    removed_node_ids: Sequence[int],
) -> tuple[RouteSpec, ...]:
    """Repair nodes ordered by earliest time window."""

    lookup = _node_lookup(problem)
    ordered = sorted(
        (int(node_id) for node_id in removed_node_ids),
        key=lambda node_id: (float(lookup[node_id]["earliest_min"]), node_id),
    )
    return greedy_insert(problem, specs, ordered)


DESTROY_OPERATORS: dict[str, DestroyOperator] = {
    "random_remove": random_remove_operator,
    "worst_cost_remove": worst_cost_remove,
    "related_remove": related_remove,
    "time_penalty_remove": time_penalty_remove,
}

REPAIR_OPERATORS: dict[str, RepairOperator] = {
    "greedy_insert": greedy_insert,
    "regret2_insert": regret2_insert,
    "time_oriented_insert": time_oriented_insert,
}


class _Insertion(tuple):
    __slots__ = ()

    @property
    def route_index(self) -> int | None:
        return self[0]

    @property
    def new_spec(self) -> RouteSpec:
        return self[1]

    @property
    def delta_cost(self) -> float:
        return self[2]


def _make_insertion(route_index: int | None, new_spec: RouteSpec, delta_cost: float) -> _Insertion:
    return _Insertion((route_index, new_spec, float(delta_cost)))


def _best_insertion(problem: ProblemData, specs: Sequence[RouteSpec], node_id: int) -> _Insertion:
    return _insertion_options(problem, specs, node_id)[0]


def _insertion_options(problem: ProblemData, specs: Sequence[RouteSpec], node_id: int) -> list[_Insertion]:
    options: list[_Insertion] = []
    for route_index, spec in enumerate(specs):
        old_cost = _local_route_cost(problem, spec)
        for pos in range(len(spec.service_node_ids) + 1):
            candidate_nodes = spec.service_node_ids[:pos] + (node_id,) + spec.service_node_ids[pos:]
            candidate_spec = _retyped_spec(problem, candidate_nodes)
            if candidate_spec is None:
                continue
            new_cost = _local_route_cost(problem, candidate_spec)
            options.append(_make_insertion(route_index, candidate_spec, new_cost - old_cost))

    new_spec = _retyped_spec(problem, (node_id,))
    if new_spec is None:
        raise ValueError(f"service node {node_id} does not fit any vehicle")
    options.append(_make_insertion(None, new_spec, _local_route_cost(problem, new_spec)))
    return sorted(options, key=lambda option: option.delta_cost)


def _apply_insertion(specs: Sequence[RouteSpec], insertion: _Insertion) -> tuple[RouteSpec, ...]:
    result = list(specs)
    if insertion.route_index is None:
        result.append(insertion.new_spec)
    else:
        result[insertion.route_index] = insertion.new_spec
    return _drop_empty_specs(result)


def _remove_nodes(specs: Sequence[RouteSpec], selected_nodes: Sequence[int]) -> tuple[RouteSpec, ...]:
    selected = set(int(node_id) for node_id in selected_nodes)
    remaining: list[RouteSpec] = []
    for spec in specs:
        nodes = tuple(node_id for node_id in spec.service_node_ids if node_id not in selected)
        if nodes:
            remaining.append(RouteSpec(spec.vehicle_type_id, nodes))
    return tuple(remaining)


def _drop_empty_specs(specs: Sequence[RouteSpec]) -> tuple[RouteSpec, ...]:
    return tuple(spec for spec in specs if spec.service_node_ids)


def _local_route_cost(problem: ProblemData, spec: RouteSpec | None) -> float:
    if spec is None or not spec.service_node_ids:
        return 0.0
    return evaluate_route(problem, spec.vehicle_type_id, spec.service_node_ids, depart_min=DAY_START_MIN).total_cost


def _retyped_spec(problem: ProblemData, service_node_ids: Sequence[int]) -> RouteSpec | None:
    if not service_node_ids:
        return None
    weight, volume = _route_demand(problem, service_node_ids)
    vehicle_type_id = _smallest_feasible_vehicle_id_or_none(weight, volume)
    if vehicle_type_id is None:
        return None
    return RouteSpec(vehicle_type_id, tuple(int(node_id) for node_id in service_node_ids))


def _route_demand(problem: ProblemData, service_node_ids: Sequence[int]) -> tuple[float, float]:
    lookup = _node_lookup(problem)
    weight = sum(float(lookup[int(node_id)]["demand_weight"]) for node_id in service_node_ids)
    volume = sum(float(lookup[int(node_id)]["demand_volume"]) for node_id in service_node_ids)
    return weight, volume


def _smallest_feasible_vehicle_id_or_none(weight_kg: float, volume_m3: float) -> str | None:
    for vehicle_type_id in ("F3", "F2", "F1", "E2", "E1"):
        vehicle = VEHICLE_TYPES[vehicle_type_id]
        if weight_kg <= vehicle.max_weight_kg + 1e-9 and volume_m3 <= vehicle.max_volume_m3 + 1e-9:
            return vehicle_type_id
    return None


def _node_lookup(problem: ProblemData) -> dict[int, dict[str, object]]:
    return {
        int(row["node_id"]): row
        for row in problem.service_nodes.to_dict(orient="records")
    }
