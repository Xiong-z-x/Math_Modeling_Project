# -*- coding: utf-8 -*-
"""Destroy and repair operators for ALNS."""

from __future__ import annotations

from random import Random
from typing import Callable, Sequence

from .constants import DAY_START_MIN, VEHICLE_TYPES
from .data_processing.loader import ProblemData
from .initial_solution import RouteSpec
from .policies import GreenZonePolicyEvaluator
from .solution import Solution, evaluate_route


DestroyOperator = Callable[
    [ProblemData, Sequence[RouteSpec], Solution, Random, int],
    tuple[tuple[RouteSpec, ...], tuple[int, ...]],
]
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
    _solution: Solution,
    rng: Random,
    remove_count: int,
) -> tuple[tuple[RouteSpec, ...], tuple[int, ...]]:
    return random_remove(specs, rng, remove_count=remove_count)


def worst_cost_remove(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    _solution: Solution,
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
    _solution: Solution,
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
    _solution: Solution,
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


def actual_late_remove(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    solution: Solution,
    rng: Random,
    remove_count: int,
) -> tuple[tuple[RouteSpec, ...], tuple[int, ...]]:
    """Remove service nodes that are actually late after physical scheduling."""

    late_stops: list[tuple[float, int]] = []
    for route in solution.routes:
        for stop in route.stops:
            if stop.late_min > 1e-9:
                late_stops.append((float(stop.late_min), int(stop.service_node_id)))
    if not late_stops:
        return random_remove_operator(problem, specs, solution, rng, remove_count)

    selected = tuple(
        node_id
        for _late_min, node_id in sorted(late_stops, reverse=True)[:remove_count]
    )
    return _remove_nodes(specs, selected), selected


def late_suffix_remove(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    solution: Solution,
    rng: Random,
    remove_count: int,
) -> tuple[tuple[RouteSpec, ...], tuple[int, ...]]:
    """Remove the suffix beginning at the first late stop on the worst route."""

    routes_with_late = [
        route for route in solution.routes if any(stop.late_min > 1e-9 for stop in route.stops)
    ]
    if not routes_with_late:
        return random_remove_operator(problem, specs, solution, rng, remove_count)

    target = max(
        routes_with_late,
        key=lambda route: max((stop.late_min for stop in route.stops), default=0.0),
    )
    suffix_nodes: list[int] = []
    found_late = False
    for stop in target.stops:
        if stop.late_min > 1e-9:
            found_late = True
        if found_late:
            suffix_nodes.append(int(stop.service_node_id))
    selected = tuple(suffix_nodes[:remove_count])
    return _remove_nodes(specs, selected), selected


def midnight_route_remove(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    solution: Solution,
    rng: Random,
    remove_count: int,
) -> tuple[tuple[RouteSpec, ...], tuple[int, ...]]:
    """Remove nodes from the route that returns latest after midnight."""

    midnight_routes = [route for route in solution.routes if route.return_min >= 24 * 60]
    if not midnight_routes:
        return random_remove_operator(problem, specs, solution, rng, remove_count)

    target = max(midnight_routes, key=lambda route: route.return_min)
    selected = tuple(int(node_id) for node_id in target.service_node_ids[:remove_count])
    return _remove_nodes(specs, selected), selected


def late_route_split(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    solution: Solution,
    rng: Random,
    remove_count: int,
) -> tuple[tuple[RouteSpec, ...], tuple[int, ...]]:
    """Split the worst late multi-stop route into two independent trip specs."""

    splittable = [
        route
        for route in solution.routes
        if len(route.service_node_ids) > 1
        and any(stop.late_min > 1e-9 for stop in route.stops)
    ]
    if not splittable:
        return random_remove_operator(problem, specs, solution, rng, remove_count)

    target = max(
        splittable,
        key=lambda route: max((stop.late_min for stop in route.stops), default=0.0),
    )
    nodes = target.service_node_ids
    split_pos: int | None = None
    for index, stop in enumerate(target.stops):
        if stop.late_min > 1e-9:
            split_pos = index
            break
    if split_pos is None or split_pos <= 0:
        split_pos = max(1, len(nodes) // 2)
    if split_pos >= len(nodes):
        split_pos = len(nodes) - 1

    prefix = nodes[:split_pos]
    suffix = nodes[split_pos:]
    replacement = [
        spec for spec in (_retyped_spec(problem, prefix), _retyped_spec(problem, suffix)) if spec is not None
    ]

    result: list[RouteSpec] = []
    replaced = False
    for spec in specs:
        if not replaced and spec.service_node_ids == nodes:
            result.extend(replacement)
            replaced = True
        else:
            result.append(spec)
    if not replaced:
        return random_remove_operator(problem, specs, solution, rng, remove_count)
    return tuple(result), ()


def policy_conflict_remove(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    solution: Solution,
    rng: Random,
    remove_count: int,
) -> tuple[tuple[RouteSpec, ...], tuple[int, ...]]:
    """Remove nodes from fuel routes that violate or risk the green-zone policy."""

    policy = GreenZonePolicyEvaluator()
    selected: list[int] = []
    for route in solution.routes:
        conflict_stops = policy.violating_stops(problem, route)
        if conflict_stops:
            first_conflict = min(
                route.stops.index(stop)
                for stop in conflict_stops
            )
            selected.extend(int(stop.service_node_id) for stop in route.stops[first_conflict:])
        elif route.vehicle_type.energy_type == "fuel":
            green_positions = [
                index for index, stop in enumerate(route.stops)
                if _is_green_node(problem, int(stop.service_node_id))
            ]
            if green_positions:
                first_green = min(green_positions)
                selected.extend(int(stop.service_node_id) for stop in route.stops[first_green:])
        if len(selected) >= remove_count:
            break

    if not selected:
        return random_remove_operator(problem, specs, solution, rng, remove_count)
    unique_selected = tuple(dict.fromkeys(selected[:remove_count]))
    return _remove_nodes(specs, unique_selected), unique_selected


def green_fuel_route_split(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    solution: Solution,
    rng: Random,
    remove_count: int,
) -> tuple[tuple[RouteSpec, ...], tuple[int, ...]]:
    """Split fuel routes that mix green-zone stops with other work."""

    fuel_green_routes = [
        route for route in solution.routes
        if route.vehicle_type.energy_type == "fuel"
        and any(_is_green_node(problem, int(node_id)) for node_id in route.service_node_ids)
    ]
    if not fuel_green_routes:
        return random_remove_operator(problem, specs, solution, rng, remove_count)

    target = max(
        fuel_green_routes,
        key=lambda route: (
            len(route.service_node_ids),
            max((stop.late_min for stop in route.stops), default=0.0),
        ),
    )
    route_nodes = tuple(int(node_id) for node_id in target.service_node_ids)
    route_index = _find_spec_index(specs, route_nodes)
    if route_index is None:
        return random_remove_operator(problem, specs, solution, rng, remove_count)

    green_nodes = tuple(node_id for node_id in route_nodes if _is_green_node(problem, node_id))
    non_green_nodes = tuple(node_id for node_id in route_nodes if node_id not in set(green_nodes))
    replacement: list[RouteSpec] = []
    if non_green_nodes:
        non_green_spec = _retyped_spec(problem, non_green_nodes)
        if non_green_spec is not None:
            replacement.append(non_green_spec)
    replacement.extend(_ev_specs_for_nodes(problem, green_nodes))
    if not replacement:
        return random_remove_operator(problem, specs, solution, rng, remove_count)
    return _replace_spec(tuple(specs), route_index, replacement), ()


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


def ev_priority_insert(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    removed_node_ids: Sequence[int],
) -> tuple[RouteSpec, ...]:
    """Repair green-zone nodes with EV-first insertions."""

    current = tuple(specs)
    lookup = _node_lookup(problem)
    ordered = sorted(
        (int(node_id) for node_id in removed_node_ids),
        key=lambda node_id: (float(lookup[node_id]["earliest_min"]), node_id),
    )
    for node_id in ordered:
        if _is_green_node(problem, node_id):
            current = _apply_insertion(current, _best_ev_insertion(problem, current, node_id))
        else:
            current = _apply_insertion(current, _best_insertion(problem, current, node_id))
    return current


def post_16_fuel_repair(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    removed_node_ids: Sequence[int],
) -> tuple[RouteSpec, ...]:
    """Repair green-zone nodes as explicit post-16:00 fuel candidates."""

    current = tuple(specs)
    for node_id in removed_node_ids:
        node_id = int(node_id)
        if _is_green_node(problem, node_id):
            current = current + (
                RouteSpec(
                    "F1",
                    (node_id,),
                    allowed_vehicle_type_ids=("F1",),
                    policy_service_mode="post_16_fuel",
                ),
            )
        else:
            current = _apply_insertion(current, _best_insertion(problem, current, node_id))
    return current


DESTROY_OPERATORS: dict[str, DestroyOperator] = {
    "random_remove": random_remove_operator,
    "worst_cost_remove": worst_cost_remove,
    "related_remove": related_remove,
    "time_penalty_remove": time_penalty_remove,
    "actual_late_remove": actual_late_remove,
    "late_suffix_remove": late_suffix_remove,
    "midnight_route_remove": midnight_route_remove,
    "late_route_split": late_route_split,
    "policy_conflict_remove": policy_conflict_remove,
    "green_fuel_route_split": green_fuel_route_split,
}

REPAIR_OPERATORS: dict[str, RepairOperator] = {
    "greedy_insert": greedy_insert,
    "regret2_insert": regret2_insert,
    "time_oriented_insert": time_oriented_insert,
    "ev_priority_insert": ev_priority_insert,
    "post_16_fuel_repair": post_16_fuel_repair,
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
            remaining.append(
                RouteSpec(
                    spec.vehicle_type_id,
                    nodes,
                    allowed_vehicle_type_ids=spec.allowed_vehicle_type_ids,
                    policy_service_mode=spec.policy_service_mode,
                )
            )
    return tuple(remaining)


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


def _ev_specs_for_nodes(problem: ProblemData, service_node_ids: Sequence[int]) -> tuple[RouteSpec, ...]:
    specs: list[RouteSpec] = []
    for node_id in service_node_ids:
        vehicle_type_id = _smallest_feasible_ev_id_or_none(problem, (int(node_id),))
        if vehicle_type_id is None:
            fuel_spec = _retyped_spec(problem, (int(node_id),))
            if fuel_spec is not None:
                specs.append(fuel_spec)
            continue
        specs.append(
            RouteSpec(
                vehicle_type_id,
                (int(node_id),),
                allowed_vehicle_type_ids=("E1", "E2"),
                policy_service_mode="ev_green",
            )
        )
    return tuple(specs)


def _best_ev_insertion(problem: ProblemData, specs: Sequence[RouteSpec], node_id: int) -> _Insertion:
    options: list[_Insertion] = []
    for route_index, spec in enumerate(specs):
        if spec.allowed_vehicle_type_ids is not None and not set(spec.allowed_vehicle_type_ids) & {"E1", "E2"}:
            continue
        if spec.vehicle_type_id not in {"E1", "E2"} and spec.allowed_vehicle_type_ids is None:
            continue
        old_cost = _local_route_cost(problem, spec)
        for pos in range(len(spec.service_node_ids) + 1):
            candidate_nodes = spec.service_node_ids[:pos] + (node_id,) + spec.service_node_ids[pos:]
            vehicle_type_id = _smallest_feasible_ev_id_or_none(problem, candidate_nodes)
            if vehicle_type_id is None:
                continue
            candidate_spec = RouteSpec(
                vehicle_type_id,
                tuple(candidate_nodes),
                allowed_vehicle_type_ids=("E1", "E2"),
                policy_service_mode="ev_green",
            )
            new_cost = _local_route_cost(problem, candidate_spec)
            options.append(_make_insertion(route_index, candidate_spec, new_cost - old_cost))

    new_vehicle_type_id = _smallest_feasible_ev_id_or_none(problem, (node_id,))
    if new_vehicle_type_id is not None:
        new_spec = RouteSpec(
            new_vehicle_type_id,
            (node_id,),
            allowed_vehicle_type_ids=("E1", "E2"),
            policy_service_mode="ev_green",
        )
        options.append(_make_insertion(None, new_spec, _local_route_cost(problem, new_spec)))

    if not options:
        return _best_insertion(problem, specs, node_id)
    return sorted(options, key=lambda option: option.delta_cost)[0]


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


def _smallest_feasible_ev_id_or_none(problem: ProblemData, service_node_ids: Sequence[int]) -> str | None:
    weight, volume = _route_demand(problem, service_node_ids)
    for vehicle_type_id in ("E2", "E1"):
        vehicle = VEHICLE_TYPES[vehicle_type_id]
        if weight <= vehicle.max_weight_kg + 1e-9 and volume <= vehicle.max_volume_m3 + 1e-9:
            return vehicle_type_id
    return None


def _is_green_node(problem: ProblemData, node_id: int) -> bool:
    return bool(_node_lookup(problem)[int(node_id)]["is_green_zone"])


def _node_lookup(problem: ProblemData) -> dict[int, dict[str, object]]:
    return {
        int(row["node_id"]): row
        for row in problem.service_nodes.to_dict(orient="records")
    }
