# -*- coding: utf-8 -*-
"""Second-stage physical vehicle scheduling for depot-to-depot trip specs."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import inf
from typing import Iterable, Mapping, Protocol, Sequence

from .constants import DAY_START_MIN, FIXED_COST_PER_VEHICLE, VEHICLE_TYPES
from .data_processing.loader import ProblemData
from .metrics import SearchScoreWeights, route_quality_score
from .policies import NoPolicyEvaluator, PolicyEvaluator
from .solution import Route, Solution, evaluate_route, evaluate_solution
from .travel_time import calculate_arrival_time


_SERVICE_NODE_LOOKUP_CACHE: dict[int, dict[int, dict[str, object]]] = {}


@dataclass(frozen=True)
class VehicleState:
    """Availability of one physical vehicle at the start of a scheduling pass."""

    vehicle_type_id: str
    vehicle_id: str
    available_min: float
    fixed_cost_if_used: float = 0.0


@dataclass(frozen=True)
class SchedulingConfig:
    """Configuration for physical-vehicle trip scheduling.

    These settings are scenario knobs for the scheduler. The defaults preserve
    the Problem 1 mother model: no hard 22:00 return limit and no reload time.
    """

    score_weights: SearchScoreWeights = field(default_factory=SearchScoreWeights)
    forbid_midnight: bool = False
    midnight_penalty: float = 1_000_000.0
    scenario_return_limit_min: float | None = None
    reload_time_min: float = 0.0
    prefer_on_time: bool = True
    optimize_departure_grid_min: int | None = None
    max_departure_delay_min: float = 180.0
    policy_evaluator: PolicyEvaluator = field(default_factory=NoPolicyEvaluator)
    ev_reservation_enabled: bool = False
    ev_reservation_penalty: float = 0.0
    green_critical_latest_min: float = 960.0
    new_vehicle_available_min: float = DAY_START_MIN
    initial_vehicle_states: tuple[VehicleState, ...] = ()


def schedule_route_specs(
    problem: ProblemData,
    specs: Sequence[RouteSpecLike],
    *,
    vehicle_counts: Mapping[str, int] | None = None,
    required_node_ids: Iterable[int] | None = None,
    config: SchedulingConfig | None = None,
    initial_vehicle_states: Sequence[VehicleState] | None = None,
) -> Solution:
    """Assign trip specs to physical vehicles and evaluate actual timings."""

    cfg = config or SchedulingConfig()
    counts = dict(vehicle_counts or {key: vehicle.count for key, vehicle in VEHICLE_TYPES.items()})
    required = set(
        int(node_id)
        for node_id in (
            required_node_ids
            if required_node_ids is not None
            else problem.service_nodes["node_id"].astype(int).tolist()
        )
    )
    ordered_specs = sorted(specs, key=lambda spec: spec_time_key(problem, spec))
    vehicles_by_type = _initial_vehicle_pools(
        initial_vehicle_states if initial_vehicle_states is not None else cfg.initial_vehicle_states
    )
    scheduled_routes: list[Route] = []

    for spec_index, spec in enumerate(ordered_specs, start=1):
        candidate_type_ids = candidate_vehicle_type_ids(problem, spec, counts)
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
                fixed_cost_if_used = float(vehicle.get("fixed_cost_if_used", 0.0))
                depart_min = choose_departure_min(
                    problem,
                    spec,
                    vehicle_type_id,
                    available_min=float(vehicle["available_min"]),
                    fixed_cost=fixed_cost_if_used,
                    config=cfg,
                )
                candidate = evaluate_route(
                    problem,
                    vehicle_type_id,
                    spec.service_node_ids,
                    depart_min=depart_min,
                    fixed_cost=fixed_cost_if_used,
                    physical_vehicle_id=str(vehicle["vehicle_id"]),
                    trip_id=f"T{spec_index:04d}",
                )
                candidate_score = scheduling_selection_score(problem, candidate, cfg)
                if candidate_score < best_score:
                    best_route = candidate
                    best_vehicle = vehicle
                    best_vehicle_pool = existing
                    best_is_new = False
                    best_score = candidate_score

            if len(existing) < counts[vehicle_type_id]:
                vehicle_id = _next_vehicle_id(vehicle_type_id, existing)
                depart_min = choose_departure_min(
                    problem,
                    spec,
                    vehicle_type_id,
                    available_min=float(cfg.new_vehicle_available_min),
                    fixed_cost=FIXED_COST_PER_VEHICLE,
                    config=cfg,
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
                candidate_score = scheduling_selection_score(problem, candidate, cfg)
                if candidate_score < best_score:
                    best_route = candidate
                    best_vehicle = {
                        "vehicle_id": vehicle_id,
                        "available_min": cfg.new_vehicle_available_min,
                        "fixed_cost_if_used": 0.0,
                    }
                    best_vehicle_pool = existing
                    best_is_new = True
                    best_score = candidate_score

        if best_route is None or best_vehicle is None or best_vehicle_pool is None:
            raise ValueError(f"no physical vehicle available for trip {spec_index}")

        best_vehicle["available_min"] = best_route.return_min + cfg.reload_time_min
        best_vehicle["fixed_cost_if_used"] = 0.0
        if best_is_new:
            best_vehicle_pool.append(best_vehicle)
        scheduled_routes.append(best_route)

    return evaluate_solution(scheduled_routes, required_node_ids=required)


def _initial_vehicle_pools(states: Sequence[VehicleState]) -> dict[str, list[dict[str, object]]]:
    vehicles_by_type: dict[str, list[dict[str, object]]] = {}
    for state in states:
        if state.vehicle_type_id not in VEHICLE_TYPES:
            raise ValueError(f"unknown vehicle type in initial state: {state.vehicle_type_id!r}")
        vehicles_by_type.setdefault(state.vehicle_type_id, []).append(
            {
                "vehicle_id": state.vehicle_id,
                "available_min": float(state.available_min),
                "fixed_cost_if_used": float(state.fixed_cost_if_used),
            }
        )
    for vehicles in vehicles_by_type.values():
        vehicles.sort(key=lambda vehicle: (float(vehicle["available_min"]), str(vehicle["vehicle_id"])))
    return vehicles_by_type


def _next_vehicle_id(vehicle_type_id: str, existing: Sequence[dict[str, object]]) -> str:
    used = {str(vehicle["vehicle_id"]) for vehicle in existing}
    index = 1
    while True:
        candidate = f"{vehicle_type_id}-{index:03d}"
        if candidate not in used:
            return candidate
        index += 1


def choose_departure_min(
    problem: ProblemData,
    spec: RouteSpecLike,
    vehicle_type_id: str,
    *,
    available_min: float,
    fixed_cost: float,
    config: SchedulingConfig,
) -> float:
    """Choose a departure time for a spec and vehicle candidate."""

    base_departure = preferred_departure_min(problem, spec, available_min=available_min)
    candidates = {float(available_min), base_departure}
    safe_departure = policy_safe_departure_min(
        problem,
        spec,
        vehicle_type_id,
        available_min=available_min,
        fixed_cost=fixed_cost,
        config=config,
    )
    if safe_departure is not None:
        candidates.add(safe_departure)

    grid = config.optimize_departure_grid_min
    if grid is None or grid <= 0:
        return _best_departure_from_candidates(
            problem,
            spec,
            vehicle_type_id,
            candidates,
            fixed_cost=fixed_cost,
            config=config,
        )

    _, tight_latest, _ = spec_time_key(problem, spec)
    upper = min(float(available_min) + config.max_departure_delay_min, tight_latest)
    if upper < available_min:
        upper = float(available_min)

    step = float(grid)
    current = float(available_min)
    while current <= upper + 1e-9:
        candidates.add(current)
        current += step

    return _best_departure_from_candidates(
        problem,
        spec,
        vehicle_type_id,
        candidates,
        fixed_cost=fixed_cost,
        config=config,
    )


def _best_departure_from_candidates(
    problem: ProblemData,
    spec: RouteSpecLike,
    vehicle_type_id: str,
    candidates: Iterable[float],
    *,
    fixed_cost: float,
    config: SchedulingConfig,
) -> float:
    ordered_candidates = sorted(float(candidate) for candidate in candidates)
    best_departure = ordered_candidates[0]
    best_score = inf
    for depart_min in ordered_candidates:
        route = evaluate_route(
            problem,
            vehicle_type_id,
            spec.service_node_ids,
            depart_min=depart_min,
            fixed_cost=fixed_cost,
        )
        score = scheduling_selection_score(problem, route, config)
        if score < best_score:
            best_departure = depart_min
            best_score = score
    return best_departure


def policy_safe_departure_min(
    problem: ProblemData,
    spec: RouteSpecLike,
    vehicle_type_id: str,
    *,
    available_min: float,
    fixed_cost: float,
    config: SchedulingConfig,
) -> float | None:
    """Find a delayed departure that makes the route policy-feasible, if needed."""

    base_departure = preferred_departure_min(problem, spec, available_min=available_min)
    if not _spec_may_have_policy_conflict(problem, spec, vehicle_type_id, config):
        return base_departure

    route = evaluate_route(
        problem,
        vehicle_type_id,
        spec.service_node_ids,
        depart_min=base_departure,
        fixed_cost=fixed_cost,
    )
    if config.policy_evaluator.is_route_allowed(problem, route):
        return base_departure

    max_departure = max(base_departure, float(available_min)) + config.max_departure_delay_min
    low = base_departure
    high = base_departure
    while high <= max_departure + 1e-9:
        high += 30.0
        route = evaluate_route(
            problem,
            vehicle_type_id,
            spec.service_node_ids,
            depart_min=high,
            fixed_cost=fixed_cost,
        )
        if config.policy_evaluator.is_route_allowed(problem, route):
            for _ in range(30):
                mid = (low + high) / 2.0
                mid_route = evaluate_route(
                    problem,
                    vehicle_type_id,
                    spec.service_node_ids,
                    depart_min=mid,
                    fixed_cost=fixed_cost,
                )
                if config.policy_evaluator.is_route_allowed(problem, mid_route):
                    high = mid
                else:
                    low = mid
            return high
    return None


def _spec_may_have_policy_conflict(
    problem: ProblemData,
    spec: RouteSpecLike,
    vehicle_type_id: str,
    config: SchedulingConfig,
) -> bool:
    if isinstance(config.policy_evaluator, NoPolicyEvaluator):
        return False
    if VEHICLE_TYPES[vehicle_type_id].energy_type != "fuel":
        return False
    lookup = service_node_lookup(problem)
    return any(bool(lookup[int(node_id)]["is_green_zone"]) for node_id in spec.service_node_ids)


def preferred_departure_min(problem: ProblemData, spec: RouteSpecLike, *, available_min: float) -> float:
    """Delay departure so the first stop arrives near its earliest time."""

    first_node_id = int(spec.service_node_ids[0])
    lookup = service_node_lookup(problem)
    first_node = lookup[first_node_id]
    first_customer_id = int(first_node["customer_id"])
    earliest_min = float(first_node["earliest_min"])
    distance = float(problem.distance_matrix.loc[0, first_customer_id])

    if calculate_arrival_time(distance, available_min) >= earliest_min:
        return float(available_min)

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


def scheduling_selection_score(problem: ProblemData, route: Route, config: SchedulingConfig) -> float:
    """Score one route candidate for physical scheduling."""

    if config.forbid_midnight and route.return_min >= 24 * 60:
        return inf

    score = route_quality_score(route, config.score_weights)
    score += config.policy_evaluator.route_penalty(problem, route)
    score += ev_reservation_candidate_penalty(problem, route, config)
    if config.scenario_return_limit_min is not None and route.return_min > config.scenario_return_limit_min:
        score += config.midnight_penalty + (route.return_min - config.scenario_return_limit_min)
    return score


def ev_reservation_candidate_penalty(problem: ProblemData, route: Route, config: SchedulingConfig) -> float:
    """Heuristic opportunity cost for spending scarce EV capacity on flexible work."""

    if not config.ev_reservation_enabled or config.ev_reservation_penalty <= 0.0:
        return 0.0
    if route.vehicle_type.energy_type != "ev":
        return 0.0
    if not _problem_has_green_critical_node(problem, config):
        return 0.0
    if _route_green_stop_count(problem, route) > 0:
        return 0.0
    if not _route_can_fit_any_fuel_vehicle(route):
        return 0.0
    return float(config.ev_reservation_penalty)


def candidate_vehicle_type_ids(
    problem: ProblemData,
    spec: RouteSpecLike,
    vehicle_counts: Mapping[str, int],
) -> tuple[str, ...]:
    """Return feasible vehicle types for this trip under available counts."""

    weight, volume = route_demand(problem, spec.service_node_ids)
    allowed = set(spec.allowed_vehicle_type_ids) if spec.allowed_vehicle_type_ids is not None else None
    feasible: list[str] = []
    for vehicle_type_id, count in vehicle_counts.items():
        if count <= 0 or vehicle_type_id not in VEHICLE_TYPES:
            continue
        if allowed is not None and vehicle_type_id not in allowed:
            continue
        vehicle = VEHICLE_TYPES[vehicle_type_id]
        if weight <= vehicle.max_weight_kg + 1e-9 and volume <= vehicle.max_volume_m3 + 1e-9:
            feasible.append(vehicle_type_id)
    return tuple(feasible)


def route_demand(problem: ProblemData, service_node_ids: Sequence[int]) -> tuple[float, float]:
    """Return total weight and volume for service-node IDs."""

    lookup = service_node_lookup(problem)
    weight = sum(float(lookup[int(node_id)]["demand_weight"]) for node_id in service_node_ids)
    volume = sum(float(lookup[int(node_id)]["demand_volume"]) for node_id in service_node_ids)
    return weight, volume


def _problem_has_green_critical_node(problem: ProblemData, config: SchedulingConfig) -> bool:
    service_nodes = problem.service_nodes
    return bool(
        (
            service_nodes["is_green_zone"].astype(bool)
            & (service_nodes["latest_min"].astype(float) < float(config.green_critical_latest_min))
        ).any()
    )


def _route_green_stop_count(problem: ProblemData, route: Route) -> int:
    lookup = service_node_lookup(problem)
    return sum(1 for node_id in route.service_node_ids if bool(lookup[int(node_id)]["is_green_zone"]))


def _route_can_fit_any_fuel_vehicle(route: Route) -> bool:
    for vehicle in VEHICLE_TYPES.values():
        if vehicle.energy_type != "fuel":
            continue
        if route.total_weight_kg <= vehicle.max_weight_kg + 1e-9 and route.total_volume_m3 <= vehicle.max_volume_m3 + 1e-9:
            return True
    return False


def spec_time_key(problem: ProblemData, spec: RouteSpecLike) -> tuple[float, float, int]:
    """Sort key that prioritizes earlier/tighter time windows."""

    lookup = service_node_lookup(problem)
    earliest_values = [float(lookup[node_id]["earliest_min"]) for node_id in spec.service_node_ids]
    latest_values = [float(lookup[node_id]["latest_min"]) for node_id in spec.service_node_ids]
    return (min(earliest_values), min(latest_values), min(spec.service_node_ids))


def service_node_lookup(problem: ProblemData) -> dict[int, dict[str, object]]:
    """Return service-node records keyed by virtual service-node ID."""

    cache_key = id(problem.service_nodes)
    cached = _SERVICE_NODE_LOOKUP_CACHE.get(cache_key)
    if cached is not None:
        return cached
    lookup = {
        int(row["node_id"]): row
        for row in problem.service_nodes.to_dict(orient="records")
    }
    _SERVICE_NODE_LOOKUP_CACHE[cache_key] = lookup
    return lookup
class RouteSpecLike(Protocol):
    """Minimal trip-spec interface consumed by the scheduler."""

    vehicle_type_id: str
    service_node_ids: tuple[int, ...]
    allowed_vehicle_type_ids: tuple[str, ...] | None
    policy_service_mode: str
