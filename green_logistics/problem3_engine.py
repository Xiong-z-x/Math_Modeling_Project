# -*- coding: utf-8 -*-
"""Problem 3 dynamic-response engine."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from .alns import ALNSConfig, ALNSResult, run_alns
from .constants import FIXED_COST_PER_VEHICLE, VEHICLE_TYPES
from .data_processing.loader import ProblemData
from .diagnostics import diagnose_problem2_policy_conflicts, write_problem_diagnostics
from .dynamic import (
    DynamicEvent,
    DynamicProblemUpdate,
    DynamicSnapshot,
    apply_dynamic_event,
    build_dynamic_snapshot,
)
from .initial_solution import RouteSpec
from .metrics import solution_quality_metrics
from .operators import ev_priority_insert, regret2_insert
from .output import minutes_to_hhmm, write_solution_outputs
from .policies import GreenZonePolicyEvaluator, NoPolicyEvaluator
from .scheduler import SchedulingConfig, VehicleState, schedule_route_specs
from .solution import Route, Solution, evaluate_route, evaluate_solution


@dataclass(frozen=True)
class Problem3Scenario:
    """One explicit scenario assumption for a Problem 3 dynamic event."""

    name: str
    description: str
    event: DynamicEvent
    inherit_green_policy: bool = True


@dataclass(frozen=True)
class Problem3ScenarioResult:
    """Full result bundle for one dynamic scenario."""

    scenario: Problem3Scenario
    problem: ProblemData
    baseline_solution: Solution
    solution: Solution
    snapshot: DynamicSnapshot
    update: DynamicProblemUpdate
    initial_residual_solution: Solution
    alns_result: ALNSResult | None
    selection_strategy: str
    policy_conflict_count: int
    quality_metrics: dict[str, float | int]
    validation: dict[str, bool | int | float]
    route_changes: pd.DataFrame
    frozen_segments: pd.DataFrame
    dynamic_diagnosis: pd.DataFrame
    event_log: pd.DataFrame


@dataclass(frozen=True)
class Problem3Engine:
    """Run event-driven rolling-horizon responses for Problem 3."""

    iterations: int = 8
    remove_count: int = 4
    seed: int = 20260426
    initial_temperature: float = 1500.0
    cooling_rate: float = 0.99
    optimize_departure_grid_min: int | None = None
    max_departure_delay_min: float = 720.0
    use_ev_reservation: bool = True
    ev_reservation_penalty: float = 250.0
    stability_change_penalty: float = 25.0
    stability_vehicle_reassignment_penalty: float = 75.0

    def run_scenario(
        self,
        problem: ProblemData,
        baseline_solution: Solution,
        scenario: Problem3Scenario,
    ) -> Problem3ScenarioResult:
        """Apply one event and reoptimize the future residual route pool."""

        snapshot = build_dynamic_snapshot(baseline_solution, scenario.event.event_time_min)
        update = apply_dynamic_event(problem, snapshot, scenario.event)
        policy = GreenZonePolicyEvaluator() if scenario.inherit_green_policy else NoPolicyEvaluator()
        locked_routes = _locked_routes(baseline_solution, snapshot)
        stable_solution = _stable_repair_solution(
            update.problem,
            baseline_solution,
            snapshot,
            update,
            scenario,
            policy,
        )
        residual_specs = _residual_specs_from_baseline(baseline_solution, snapshot, update)
        residual_specs = _prepare_event_repair_specs(update.problem, residual_specs, update)
        residual_problem = _residual_problem(update.problem, _nodes_in_specs(residual_specs))
        vehicle_states = _vehicle_states_for_event(baseline_solution, snapshot, scenario.event.event_time_min)
        scheduling_config = SchedulingConfig(
            policy_evaluator=policy,
            optimize_departure_grid_min=self.optimize_departure_grid_min,
            max_departure_delay_min=self.max_departure_delay_min,
            new_vehicle_available_min=float(scenario.event.event_time_min),
            initial_vehicle_states=vehicle_states,
            ev_reservation_enabled=self.use_ev_reservation,
            ev_reservation_penalty=self.ev_reservation_penalty,
        )

        if residual_specs:
            initial_residual_solution = schedule_route_specs(
                residual_problem,
                residual_specs,
                config=scheduling_config,
            )
            alns_result = run_alns(
                residual_problem,
                initial_specs=residual_specs,
                config=ALNSConfig(
                    iterations=self.iterations,
                    remove_count=self.remove_count,
                    seed=self.seed,
                    initial_temperature=self.initial_temperature,
                    cooling_rate=self.cooling_rate,
                    scheduling_config=scheduling_config,
                    policy_evaluator=policy,
                    postprocess_late_routes=True,
                ),
            )
            residual_solution = alns_result.best_solution
        else:
            initial_residual_solution = evaluate_solution((), required_node_ids=())
            alns_result = None
            residual_solution = initial_residual_solution

        residual_routes = _renumber_residual_routes(residual_solution.routes)
        combined_routes = tuple(sorted((*locked_routes, *residual_routes), key=lambda route: route.depart_min))
        alns_solution = evaluate_solution(combined_routes, required_node_ids=update.required_node_ids)
        solution, selection_strategy = _choose_dynamic_solution(
            update.problem,
            baseline_solution,
            stable_solution,
            alns_solution,
            update,
            snapshot,
            policy,
            change_penalty=self.stability_change_penalty,
            vehicle_penalty=self.stability_vehicle_reassignment_penalty,
        )
        conflict_count = policy.solution_violation_count(update.problem, solution)
        quality = solution_quality_metrics(solution).to_dict()
        validation = _validate_dynamic_solution(update.problem, solution, conflict_count)
        route_changes = _route_changes(baseline_solution, solution, update, snapshot)
        frozen_segments = _frozen_segments(locked_routes)
        dynamic_diagnosis = _dynamic_diagnosis(
            scenario,
            baseline_solution,
            solution,
            update,
            conflict_count,
            validation,
            selection_strategy,
        )
        event_log = _event_log(scenario, update)
        return Problem3ScenarioResult(
            scenario=scenario,
            problem=update.problem,
            baseline_solution=baseline_solution,
            solution=solution,
            snapshot=snapshot,
            update=update,
            initial_residual_solution=initial_residual_solution,
            alns_result=alns_result,
            selection_strategy=selection_strategy,
            policy_conflict_count=conflict_count,
            quality_metrics=quality,
            validation=validation,
            route_changes=route_changes,
            frozen_segments=frozen_segments,
            dynamic_diagnosis=dynamic_diagnosis,
            event_log=event_log,
        )


def load_baseline_solution_from_outputs(problem: ProblemData, baseline_dir: str | Path) -> Solution:
    """Reconstruct an evaluated solution from a saved `route_summary.csv`."""

    route_summary = Path(baseline_dir) / "route_summary.csv"
    if not route_summary.exists():
        raise FileNotFoundError(f"missing baseline route summary: {route_summary}")

    frame = pd.read_csv(route_summary)
    routes: list[Route] = []
    for row in frame.sort_values("route_index").to_dict(orient="records"):
        node_ids = _parse_node_sequence(row.get("service_node_sequence", ""))
        route = evaluate_route(
            problem,
            str(row["vehicle_type"]),
            node_ids,
            depart_min=float(row["depart_min"]),
            fixed_cost=float(row.get("fixed_cost", 0.0)),
            physical_vehicle_id=str(row.get("physical_vehicle_id", "")) or None,
            trip_id=str(row.get("trip_id", "")) or None,
        )
        routes.append(route)
    required = problem.service_nodes["node_id"].astype(int).tolist()
    return evaluate_solution(routes, required_node_ids=required)


def build_default_problem3_scenarios(
    problem: ProblemData,
    baseline_solution: Solution,
) -> tuple[Problem3Scenario, ...]:
    """Build representative scenario assumptions because the statement gives no event data."""

    cancel_node = _select_cancel_node(baseline_solution, event_time_min=630.0)
    new_proxy = _select_green_proxy_customer(problem)
    new_node_id = int(problem.service_nodes["node_id"].max()) + 1
    time_node, new_earliest, new_latest = _select_time_window_node(problem, baseline_solution, event_time_min=900.0)
    address_node, proxy_customer = _select_address_change(problem, baseline_solution, event_time_min=720.0)

    return (
        Problem3Scenario(
            name="cancel_future_order_1030",
            description="10:30 cancellation of a not-yet-departed service node.",
            event=DynamicEvent(
                event_type="cancel",
                event_time_min=630.0,
                service_node_id=cancel_node,
                description="订单取消：取消一个尚未发车趟次中的服务节点。",
            ),
        ),
        Problem3Scenario(
            name="new_green_order_1330",
            description="13:30 new order represented by an existing green-zone customer proxy.",
            event=DynamicEvent(
                event_type="new_order",
                event_time_min=810.0,
                new_service_node_id=new_node_id,
                proxy_customer_id=new_proxy,
                demand_weight_kg=300.0,
                demand_volume_m3=1.0,
                earliest_min=840.0,
                latest_min=1020.0,
                description="新增订单：以既有绿区客户作为代理点，需求 300 kg / 1.0 m3。",
            ),
        ),
        Problem3Scenario(
            name="time_window_pull_forward_1500",
            description="15:00 pull one future time window forward.",
            event=DynamicEvent(
                event_type="time_window_change",
                event_time_min=900.0,
                service_node_id=time_node,
                earliest_min=new_earliest,
                latest_min=new_latest,
                description="时间窗调整：将一个尚未服务节点的时间窗提前压缩。",
            ),
        ),
        Problem3Scenario(
            name="address_change_proxy_1200",
            description="12:00 address change represented by another existing customer.",
            event=DynamicEvent(
                event_type="address_change",
                event_time_min=720.0,
                service_node_id=address_node,
                proxy_customer_id=proxy_customer,
                description="地址变更：使用既有客户点作为代理地址，避免虚构新距离矩阵。",
            ),
        ),
    )


def write_problem3_scenario_outputs(
    result: Problem3ScenarioResult,
    output_dir: str | Path,
    *,
    create_plots: bool = True,
) -> dict[str, Path]:
    """Write all artifacts for one dynamic scenario."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    written = write_solution_outputs(
        result.solution,
        output_path,
        problem=result.problem,
        create_plots=create_plots,
    )
    written.update(write_problem_diagnostics(result.problem, result.solution, output_path))

    tables = {
        "event_log_csv": (result.event_log, output_path / "event_log.csv"),
        "route_changes_csv": (result.route_changes, output_path / "route_changes.csv"),
        "frozen_segments_csv": (result.frozen_segments, output_path / "frozen_segments.csv"),
        "dynamic_diagnosis_csv": (result.dynamic_diagnosis, output_path / "dynamic_diagnosis.csv"),
    }
    for key, (frame, path) in tables.items():
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        written[key] = path

    summary_path = output_path / "problem3_scenario_summary.md"
    summary_path.write_text(_scenario_markdown(result, written), encoding="utf-8")
    written["problem3_scenario_summary_md"] = summary_path
    return written


def write_problem3_comparison_outputs(
    results: Sequence[Problem3ScenarioResult],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write root-level Problem 3 scenario comparison and recommendation JSON."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    rows = [_comparison_row(result) for result in results]
    comparison = pd.DataFrame(rows)
    comparison_path = output_path / "scenario_comparison.csv"
    comparison.to_csv(comparison_path, index=False, encoding="utf-8-sig")

    feasible = comparison[
        (comparison["is_complete"] == True)  # noqa: E712
        & (comparison["is_capacity_feasible"] == True)  # noqa: E712
        & (comparison["policy_conflict_count"] == 0)
        & (comparison["physical_time_chain_feasible"] == True)  # noqa: E712
    ]
    recommendation = {
        "scenario_count": int(len(comparison)),
        "feasible_scenario_count": int(len(feasible)),
        "all_scenarios_feasible": bool(len(feasible) == len(comparison)),
        "baseline_total_cost": float(results[0].baseline_solution.total_cost) if results else 0.0,
        "scenario_comparison_csv": str(comparison_path),
        "scenario_rows": rows,
        "modeling_note": "Problem 3 has no official event data; these rows are representative scenario assumptions.",
    }
    recommendation_path = output_path / "recommendation.json"
    recommendation_path.write_text(json.dumps(recommendation, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path = output_path / "problem3_dynamic_response_summary.md"
    summary_path.write_text(_root_markdown(results, comparison), encoding="utf-8")
    return {
        "scenario_comparison_csv": comparison_path,
        "recommendation_json": recommendation_path,
        "problem3_dynamic_response_summary_md": summary_path,
    }


def _parse_node_sequence(value: object) -> tuple[int, ...]:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ()
    return tuple(int(part) for part in text.split("->") if part)


def _locked_routes(solution: Solution, snapshot: DynamicSnapshot) -> tuple[Route, ...]:
    locked = set(snapshot.locked_route_ids)
    return tuple(route for route in solution.routes if (route.trip_id or "") in locked)


def _residual_specs_from_baseline(
    solution: Solution,
    snapshot: DynamicSnapshot,
    update: DynamicProblemUpdate,
) -> tuple[RouteSpec, ...]:
    adjustable_route_ids = set(snapshot.adjustable_route_ids)
    residual_nodes = set(update.residual_node_ids)
    specs: list[RouteSpec] = []
    for route in solution.routes:
        if (route.trip_id or "") not in adjustable_route_ids:
            continue
        nodes = tuple(int(node_id) for node_id in route.service_node_ids if int(node_id) in residual_nodes)
        if nodes:
            specs.append(RouteSpec(route.vehicle_type_id, nodes))
    return tuple(specs)


def _prepare_event_repair_specs(
    problem: ProblemData,
    specs: Sequence[RouteSpec],
    update: DynamicProblemUpdate,
) -> tuple[RouteSpec, ...]:
    nodes_to_reinsert = tuple(dict.fromkeys((*update.added_node_ids, *update.changed_node_ids)))
    if not nodes_to_reinsert:
        return tuple(specs)
    stripped = _remove_nodes_from_specs(specs, nodes_to_reinsert)
    if any(_is_green_node(problem, node_id) for node_id in nodes_to_reinsert):
        return ev_priority_insert(problem, stripped, nodes_to_reinsert)
    return regret2_insert(problem, stripped, nodes_to_reinsert)


def _remove_nodes_from_specs(specs: Sequence[RouteSpec], node_ids: Iterable[int]) -> tuple[RouteSpec, ...]:
    remove = set(int(node_id) for node_id in node_ids)
    remaining: list[RouteSpec] = []
    for spec in specs:
        nodes = tuple(node_id for node_id in spec.service_node_ids if node_id not in remove)
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


def _nodes_in_specs(specs: Sequence[RouteSpec]) -> tuple[int, ...]:
    return tuple(sorted({int(node_id) for spec in specs for node_id in spec.service_node_ids}))


def _residual_problem(problem: ProblemData, residual_node_ids: Sequence[int]) -> ProblemData:
    residual = set(int(node_id) for node_id in residual_node_ids)
    service_nodes = problem.service_nodes[
        problem.service_nodes["node_id"].astype(int).isin(residual)
    ].copy().reset_index(drop=True)
    return replace(
        problem,
        service_nodes=service_nodes,
        node_to_customer={
            int(row["node_id"]): int(row["customer_id"])
            for row in service_nodes.to_dict(orient="records")
        },
    )


def _vehicle_states_for_event(
    solution: Solution,
    snapshot: DynamicSnapshot,
    event_time_min: float,
) -> tuple[VehicleState, ...]:
    locked_ids = set(snapshot.locked_route_ids)
    by_vehicle: dict[str, list[Route]] = {}
    for route in solution.routes:
        if not route.physical_vehicle_id:
            continue
        by_vehicle.setdefault(route.physical_vehicle_id, []).append(route)

    states: list[VehicleState] = []
    for vehicle_id, routes in sorted(by_vehicle.items()):
        ordered = sorted(routes, key=lambda route: route.depart_min)
        locked = [route for route in ordered if (route.trip_id or "") in locked_ids]
        available = max(float(event_time_min), max((route.return_min for route in locked), default=float(event_time_min)))
        fixed_paid = bool(locked)
        states.append(
            VehicleState(
                vehicle_type_id=ordered[0].vehicle_type_id,
                vehicle_id=vehicle_id,
                available_min=available,
                fixed_cost_if_used=0.0 if fixed_paid else FIXED_COST_PER_VEHICLE,
            )
        )
    return tuple(states)


def _renumber_residual_routes(routes: Sequence[Route]) -> tuple[Route, ...]:
    return tuple(
        replace(route, trip_id=f"D{index:04d}")
        for index, route in enumerate(sorted(routes, key=lambda item: item.depart_min), start=1)
    )


def _validate_dynamic_solution(
    problem: ProblemData,
    solution: Solution,
    policy_conflict_count: int,
) -> dict[str, bool | int | float]:
    return {
        "is_complete": solution.is_complete,
        "is_capacity_feasible": solution.is_capacity_feasible,
        "policy_conflict_count": int(policy_conflict_count),
        "physical_time_chain_feasible": _physical_time_chain_feasible(solution),
        "missing_node_count": len(solution.missing_node_ids),
        "duplicate_node_count": len(solution.duplicate_node_ids),
        "cost_components_sum": solution.fixed_cost + solution.energy_cost + solution.carbon_cost + solution.penalty_cost,
        "total_cost": solution.total_cost,
        "audited_stop_count": int(len(diagnose_problem2_policy_conflicts(problem, solution))),
    }


def _stable_repair_solution(
    problem: ProblemData,
    baseline: Solution,
    snapshot: DynamicSnapshot,
    update: DynamicProblemUpdate,
    scenario: Problem3Scenario,
    policy,
) -> Solution:
    """Keep baseline future routes unless the event forces a small local repair."""

    adjustable_route_ids = set(snapshot.adjustable_route_ids)
    residual_nodes = set(update.residual_node_ids)
    candidate_routes: list[Route] = []
    for route in baseline.routes:
        trip_id = route.trip_id or ""
        if trip_id in adjustable_route_ids:
            nodes = tuple(int(node_id) for node_id in route.service_node_ids if int(node_id) in residual_nodes)
            if nodes:
                candidate_routes.append(
                    evaluate_route(
                        problem,
                        route.vehicle_type_id,
                        nodes,
                        depart_min=route.depart_min,
                        fixed_cost=0.0,
                        physical_vehicle_id=route.physical_vehicle_id,
                        trip_id=route.trip_id,
                    )
                )
        else:
            candidate_routes.append(
                evaluate_route(
                    problem,
                    route.vehicle_type_id,
                    route.service_node_ids,
                    depart_min=route.depart_min,
                    fixed_cost=0.0,
                    physical_vehicle_id=route.physical_vehicle_id,
                    trip_id=route.trip_id,
                )
            )

    solution = _normalize_fixed_costs(problem, candidate_routes, required_node_ids=update.required_node_ids)
    for node_id in update.added_node_ids:
        solution = _insert_new_node_stably(problem, solution, int(node_id), scenario, policy)
    return solution


def _insert_new_node_stably(
    problem: ProblemData,
    solution: Solution,
    node_id: int,
    scenario: Problem3Scenario,
    policy,
) -> Solution:
    candidates: list[Solution] = []
    for route_index, route in enumerate(solution.routes):
        if route.depart_min <= scenario.event.event_time_min:
            continue
        for position in range(len(route.service_node_ids) + 1):
            nodes = route.service_node_ids[:position] + (node_id,) + route.service_node_ids[position:]
            if not _route_capacity_feasible(problem, route.vehicle_type_id, nodes):
                continue
            replacement = evaluate_route(
                problem,
                route.vehicle_type_id,
                nodes,
                depart_min=route.depart_min,
                fixed_cost=0.0,
                physical_vehicle_id=route.physical_vehicle_id,
                trip_id=route.trip_id,
            )
            routes = list(solution.routes)
            routes[route_index] = replacement
            candidate = _normalize_fixed_costs(problem, routes, required_node_ids=problem.service_nodes["node_id"].astype(int).tolist())
            if _candidate_dynamic_feasible(problem, candidate, policy):
                candidates.append(candidate)

    candidates.extend(_new_route_candidates(problem, solution, node_id, scenario, policy))
    if not candidates:
        raise ValueError(f"could not insert new dynamic service node {node_id}")
    return min(candidates, key=lambda candidate: candidate.total_cost)


def _new_route_candidates(
    problem: ProblemData,
    solution: Solution,
    node_id: int,
    scenario: Problem3Scenario,
    policy,
) -> list[Solution]:
    candidates: list[Solution] = []
    used_by_type = solution.vehicle_physical_usage_by_type
    for vehicle_type_id in ("E1", "E2", "F1", "F2", "F3"):
        vehicle = VEHICLE_TYPES[vehicle_type_id]
        if used_by_type.get(vehicle_type_id, 0) >= vehicle.count:
            continue
        if not _route_capacity_feasible(problem, vehicle_type_id, (node_id,)):
            continue
        depart_min = float(scenario.event.event_time_min)
        if vehicle.energy_type == "fuel" and _is_green_node(problem, node_id):
            depart_min = max(depart_min, GreenZonePolicyEvaluator().end_min)
        vehicle_id = _next_unused_vehicle_id(solution, vehicle_type_id)
        route = evaluate_route(
            problem,
            vehicle_type_id,
            (node_id,),
            depart_min=depart_min,
            fixed_cost=0.0,
            physical_vehicle_id=vehicle_id,
            trip_id=f"N{node_id:04d}",
        )
        candidate = _normalize_fixed_costs(
            problem,
            (*solution.routes, route),
            required_node_ids=problem.service_nodes["node_id"].astype(int).tolist(),
        )
        if _candidate_dynamic_feasible(problem, candidate, policy):
            candidates.append(candidate)
    return candidates


def _normalize_fixed_costs(
    problem: ProblemData,
    routes: Sequence[Route],
    *,
    required_node_ids: Iterable[int],
) -> Solution:
    normalized: list[Route] = []
    by_vehicle: dict[str, list[Route]] = {}
    for route in routes:
        key = route.physical_vehicle_id or f"route-{id(route)}"
        by_vehicle.setdefault(key, []).append(route)
    for vehicle_routes in by_vehicle.values():
        for index, route in enumerate(sorted(vehicle_routes, key=lambda item: item.depart_min)):
            normalized.append(
                evaluate_route(
                    problem,
                    route.vehicle_type_id,
                    route.service_node_ids,
                    depart_min=route.depart_min,
                    fixed_cost=FIXED_COST_PER_VEHICLE if index == 0 else 0.0,
                    physical_vehicle_id=route.physical_vehicle_id,
                    trip_id=route.trip_id,
                )
            )
    return evaluate_solution(sorted(normalized, key=lambda route: route.depart_min), required_node_ids=required_node_ids)


def _route_capacity_feasible(problem: ProblemData, vehicle_type_id: str, node_ids: Sequence[int]) -> bool:
    lookup = problem.service_nodes.set_index("node_id")
    weight = sum(float(lookup.loc[int(node_id)]["demand_weight"]) for node_id in node_ids)
    volume = sum(float(lookup.loc[int(node_id)]["demand_volume"]) for node_id in node_ids)
    vehicle = VEHICLE_TYPES[vehicle_type_id]
    return weight <= vehicle.max_weight_kg + 1e-9 and volume <= vehicle.max_volume_m3 + 1e-9


def _candidate_dynamic_feasible(problem: ProblemData, solution: Solution, policy) -> bool:
    return (
        solution.is_complete
        and solution.is_capacity_feasible
        and _physical_time_chain_feasible(solution)
        and policy.solution_violation_count(problem, solution) == 0
    )


def _choose_dynamic_solution(
    problem: ProblemData,
    baseline: Solution,
    stable_solution: Solution,
    alns_solution: Solution,
    update: DynamicProblemUpdate,
    snapshot: DynamicSnapshot,
    policy,
    *,
    change_penalty: float,
    vehicle_penalty: float,
) -> tuple[Solution, str]:
    candidates: list[tuple[float, str, Solution]] = []
    for name, solution in (("stable_repair", stable_solution), ("light_alns", alns_solution)):
        if not _candidate_dynamic_feasible(problem, solution, policy):
            continue
        changes = _route_changes(baseline, solution, update, snapshot)
        changed_count = int((~changes["change_type"].isin(["unchanged", "locked_unchanged"])).sum())
        reassigned_count = int((changes["change_type"] == "vehicle_reassigned").sum())
        score = solution.total_cost + change_penalty * changed_count + vehicle_penalty * reassigned_count
        candidates.append((score, name, solution))
    if not candidates:
        return alns_solution, "light_alns_infeasible_fallback"
    _score, name, solution = min(candidates, key=lambda item: item[0])
    return solution, name


def _next_unused_vehicle_id(solution: Solution, vehicle_type_id: str) -> str:
    used = {
        route.physical_vehicle_id
        for route in solution.routes
        if route.physical_vehicle_id and route.physical_vehicle_id.startswith(f"{vehicle_type_id}-")
    }
    index = 1
    while True:
        candidate = f"{vehicle_type_id}-{index:03d}"
        if candidate not in used:
            return candidate
        index += 1


def _physical_time_chain_feasible(solution: Solution) -> bool:
    by_vehicle: dict[str, list[Route]] = {}
    for route in solution.routes:
        key = route.physical_vehicle_id or f"route-{id(route)}"
        by_vehicle.setdefault(key, []).append(route)
    for routes in by_vehicle.values():
        previous_return: float | None = None
        for route in sorted(routes, key=lambda item: item.depart_min):
            if previous_return is not None and route.depart_min + 1e-9 < previous_return:
                return False
            previous_return = route.return_min
    return True


def _route_changes(
    baseline: Solution,
    solution: Solution,
    update: DynamicProblemUpdate,
    snapshot: DynamicSnapshot,
) -> pd.DataFrame:
    old = _node_occurrences(baseline)
    new = _node_occurrences(solution)
    nodes = sorted(set(old) | set(new) | set(update.cancelled_node_ids) | set(update.added_node_ids))
    locked = set(snapshot.locked_node_ids)
    rows: list[dict[str, object]] = []
    for node_id in nodes:
        before = old.get(node_id, {})
        after = new.get(node_id, {})
        if node_id in set(update.cancelled_node_ids):
            change_type = "cancelled"
        elif node_id in set(update.added_node_ids):
            change_type = "new"
        elif not before:
            change_type = "new"
        elif not after:
            change_type = "removed"
        elif node_id in locked:
            change_type = "locked_unchanged"
        elif before.get("physical_vehicle_id") != after.get("physical_vehicle_id"):
            change_type = "vehicle_reassigned"
        elif before.get("predecessor_node_id") != after.get("predecessor_node_id") or before.get("successor_node_id") != after.get("successor_node_id"):
            change_type = "sequence_changed"
        elif abs(float(before.get("arrival_min", 0.0)) - float(after.get("arrival_min", 0.0))) > 1e-6:
            change_type = "retimed"
        elif node_id in set(update.changed_node_ids):
            change_type = "event_modified"
        else:
            change_type = "unchanged"
        rows.append(
            {
                "service_node_id": node_id,
                "change_type": change_type,
                "old_trip_id": before.get("trip_id", ""),
                "new_trip_id": after.get("trip_id", ""),
                "old_physical_vehicle_id": before.get("physical_vehicle_id", ""),
                "new_physical_vehicle_id": after.get("physical_vehicle_id", ""),
                "old_stop_index": before.get("stop_index", ""),
                "new_stop_index": after.get("stop_index", ""),
                "old_predecessor_node_id": before.get("predecessor_node_id", ""),
                "new_predecessor_node_id": after.get("predecessor_node_id", ""),
                "old_successor_node_id": before.get("successor_node_id", ""),
                "new_successor_node_id": after.get("successor_node_id", ""),
                "old_arrival_min": before.get("arrival_min", ""),
                "new_arrival_min": after.get("arrival_min", ""),
            }
        )
    return pd.DataFrame(rows)


def _node_occurrences(solution: Solution) -> dict[int, dict[str, object]]:
    occurrences: dict[int, dict[str, object]] = {}
    for route_index, route in enumerate(solution.routes, start=1):
        nodes = tuple(int(node_id) for node_id in route.service_node_ids)
        for stop_index, stop in enumerate(route.stops, start=1):
            node_id = int(stop.service_node_id)
            occurrences[node_id] = {
                "route_index": route_index,
                "trip_id": route.trip_id or f"R{route_index:04d}",
                "physical_vehicle_id": route.physical_vehicle_id or "",
                "vehicle_type": route.vehicle_type_id,
                "stop_index": stop_index,
                "predecessor_node_id": 0 if stop_index == 1 else nodes[stop_index - 2],
                "successor_node_id": 0 if stop_index == len(nodes) else nodes[stop_index],
                "arrival_min": float(stop.arrival_min),
            }
    return occurrences


def _frozen_segments(routes: Sequence[Route]) -> pd.DataFrame:
    rows = []
    for route in sorted(routes, key=lambda item: item.depart_min):
        rows.append(
            {
                "trip_id": route.trip_id or "",
                "physical_vehicle_id": route.physical_vehicle_id or "",
                "vehicle_type": route.vehicle_type_id,
                "service_node_sequence": "->".join(str(node_id) for node_id in route.service_node_ids),
                "depart_min": route.depart_min,
                "return_min": route.return_min,
                "fixed_cost": route.fixed_cost,
                "total_cost": route.total_cost,
            }
        )
    return pd.DataFrame(rows)


def _dynamic_diagnosis(
    scenario: Problem3Scenario,
    baseline: Solution,
    solution: Solution,
    update: DynamicProblemUpdate,
    policy_conflict_count: int,
    validation: dict[str, bool | int | float],
    selection_strategy: str,
) -> pd.DataFrame:
    quality = solution_quality_metrics(solution)
    baseline_quality = solution_quality_metrics(baseline)
    return pd.DataFrame(
        [
            {
                "scenario": scenario.name,
                "event_type": scenario.event.event_type,
                "event_time_min": scenario.event.event_time_min,
                "event_time": minutes_to_hhmm(scenario.event.event_time_min),
                "selection_strategy": selection_strategy,
                "baseline_total_cost": baseline.total_cost,
                "dynamic_total_cost": solution.total_cost,
                "delta_total_cost": solution.total_cost - baseline.total_cost,
                "cancelled_node_count": len(update.cancelled_node_ids),
                "added_node_count": len(update.added_node_ids),
                "changed_node_count": len(update.changed_node_ids),
                "late_stop_count": quality.late_stop_count,
                "baseline_late_stop_count": baseline_quality.late_stop_count,
                "max_late_min": quality.max_late_min,
                "baseline_max_late_min": baseline_quality.max_late_min,
                "policy_conflict_count": policy_conflict_count,
                "physical_time_chain_feasible": validation["physical_time_chain_feasible"],
                "is_complete": solution.is_complete,
                "is_capacity_feasible": solution.is_capacity_feasible,
            }
        ]
    )


def _event_log(scenario: Problem3Scenario, update: DynamicProblemUpdate) -> pd.DataFrame:
    event = scenario.event
    return pd.DataFrame(
        [
            {
                "scenario": scenario.name,
                "description": scenario.description,
                "event_type": event.event_type,
                "event_time_min": event.event_time_min,
                "event_time": minutes_to_hhmm(event.event_time_min),
                "service_node_id": event.service_node_id or "",
                "new_service_node_id": event.new_service_node_id or "",
                "proxy_customer_id": event.proxy_customer_id or "",
                "demand_weight_kg": event.demand_weight_kg or "",
                "demand_volume_m3": event.demand_volume_m3 or "",
                "earliest_min": event.earliest_min or "",
                "latest_min": event.latest_min or "",
                "event_note": event.description,
                "applied_note": update.note,
            }
        ]
    )


def _comparison_row(result: Problem3ScenarioResult) -> dict[str, object]:
    diagnosis = result.dynamic_diagnosis.iloc[0].to_dict()
    return {
        "scenario": result.scenario.name,
        "event_type": result.scenario.event.event_type,
        "event_time_min": result.scenario.event.event_time_min,
        "selection_strategy": result.selection_strategy,
        "baseline_total_cost": diagnosis["baseline_total_cost"],
        "dynamic_total_cost": diagnosis["dynamic_total_cost"],
        "delta_total_cost": diagnosis["delta_total_cost"],
        "policy_conflict_count": result.policy_conflict_count,
        "is_complete": result.solution.is_complete,
        "is_capacity_feasible": result.solution.is_capacity_feasible,
        "physical_time_chain_feasible": result.validation["physical_time_chain_feasible"],
        "late_stop_count": result.quality_metrics["late_stop_count"],
        "max_late_min": result.quality_metrics["max_late_min"],
        "changed_stop_count": int((~result.route_changes["change_type"].isin(["unchanged", "locked_unchanged"])).sum()),
        "vehicle_reassignment_count": int((result.route_changes["change_type"] == "vehicle_reassigned").sum()),
    }


def _scenario_markdown(result: Problem3ScenarioResult, written: dict[str, Path]) -> str:
    diagnosis = result.dynamic_diagnosis.iloc[0]
    lines = [
        "# Problem 3 Dynamic Scenario Summary",
        "",
        f"- Scenario: `{result.scenario.name}`",
        f"- Event type: `{result.scenario.event.event_type}`",
        f"- Event time: `{minutes_to_hhmm(result.scenario.event.event_time_min)}`",
        f"- Baseline total cost: `{diagnosis['baseline_total_cost']:.2f}`",
        f"- Dynamic total cost: `{diagnosis['dynamic_total_cost']:.2f}`",
        f"- Delta total cost: `{diagnosis['delta_total_cost']:.2f}`",
        f"- Policy conflicts: `{result.policy_conflict_count}`",
        f"- Complete/capacity feasible: `{result.solution.is_complete}` / `{result.solution.is_capacity_feasible}`",
        f"- Physical time chain feasible: `{result.validation['physical_time_chain_feasible']}`",
        "",
        "## Files",
        "",
    ]
    lines.extend(f"- `{key}`: `{path}`" for key, path in sorted(written.items()))
    lines.append("")
    return "\n".join(lines)


def _root_markdown(results: Sequence[Problem3ScenarioResult], comparison: pd.DataFrame) -> str:
    lines = [
        "# 第三问动态事件响应结果摘要",
        "",
        "题面没有提供具体动态事件数据，因此以下结果均为代表性情景假设。",
        "正式成本仍为固定成本、能源成本、碳排成本和软时间窗罚金；路线稳定性只作辅助分析。",
        "",
        "## 情景对比",
        "",
    ]
    for row in comparison.to_dict(orient="records"):
        lines.append(
            f"- `{row['scenario']}`: cost `{row['dynamic_total_cost']:.2f}`, "
            f"delta `{row['delta_total_cost']:.2f}`, policy conflicts `{row['policy_conflict_count']}`, "
            f"late stops `{row['late_stop_count']}`."
        )
    lines.extend(
        [
            "",
            "## 建模纪律",
            "",
            "- 已执行和在途锁定趟次不被重排。",
            "- 新增订单使用既有客户点代理，不虚构道路距离矩阵。",
            "- 继承第二问绿色限行政策时，燃油车在 `[480,960)` 服务绿色客户为硬冲突。",
            "",
        ]
    )
    return "\n".join(lines)


def _select_cancel_node(solution: Solution, *, event_time_min: float) -> int:
    by_vehicle: dict[str, list[Route]] = {}
    for route in solution.routes:
        by_vehicle.setdefault(route.physical_vehicle_id or "", []).append(route)
    candidates: list[tuple[float, Route]] = []
    for route in solution.routes:
        if route.depart_min <= event_time_min or len(route.service_node_ids) != 1:
            continue
        vehicle_routes = by_vehicle.get(route.physical_vehicle_id or "", [])
        all_future = all(item.depart_min > event_time_min for item in vehicle_routes)
        score = route.total_cost + (1000.0 if all_future else 0.0) + route.fixed_cost
        candidates.append((score, route))
    if not candidates:
        for route in solution.routes:
            if route.depart_min > event_time_min and route.service_node_ids:
                return int(route.service_node_ids[0])
        raise ValueError("cannot build cancellation scenario; no future service node")
    return int(max(candidates, key=lambda item: item[0])[1].service_node_ids[0])


def _select_green_proxy_customer(problem: ProblemData) -> int:
    green = problem.service_nodes[problem.service_nodes["is_green_zone"].astype(bool)]
    if green.empty:
        return int(problem.service_nodes.iloc[0]["customer_id"])
    return int(green.sort_values(["latest_min", "node_id"]).iloc[0]["customer_id"])


def _select_time_window_node(
    problem: ProblemData,
    solution: Solution,
    *,
    event_time_min: float,
) -> tuple[int, float, float]:
    lookup = problem.service_nodes.set_index("node_id")
    candidates: list[tuple[float, int, float, float]] = []
    for route in sorted(solution.routes, key=lambda item: item.depart_min):
        if route.depart_min <= event_time_min:
            continue
        for stop in route.stops:
            node_id = int(stop.service_node_id)
            row = lookup.loc[node_id]
            earliest = float(row["earliest_min"])
            latest = float(row["latest_min"])
            if latest - earliest < 45.0:
                continue
            if float(stop.arrival_min) <= earliest + 20.0:
                continue
            new_latest = max(earliest + 20.0, min(latest - 30.0, float(stop.arrival_min) - 5.0))
            induced_late = max(0.0, float(stop.arrival_min) - new_latest)
            candidates.append((induced_late, node_id, earliest, new_latest))
    if candidates:
        _late, node_id, earliest, new_latest = max(candidates, key=lambda item: (item[0], item[1]))
        return node_id, earliest, new_latest
    for route in sorted(solution.routes, key=lambda item: item.depart_min):
        if route.depart_min > event_time_min and route.service_node_ids:
            node_id = int(route.service_node_ids[0])
            row = lookup.loc[node_id]
            earliest = float(row["earliest_min"])
            latest = float(row["latest_min"])
            return node_id, earliest, max(earliest + 20.0, latest - 60.0)
    raise ValueError("cannot build time-window scenario; no future service node")


def _select_address_change(
    problem: ProblemData,
    solution: Solution,
    *,
    event_time_min: float,
) -> tuple[int, int]:
    lookup = problem.service_nodes.set_index("node_id")
    for route in sorted(solution.routes, key=lambda item: item.depart_min):
        if route.depart_min <= event_time_min:
            continue
        node_id = int(route.service_node_ids[0])
        old_customer = int(lookup.loc[node_id]["customer_id"])
        proxy = _nearest_different_customer(problem, old_customer)
        return node_id, proxy
    raise ValueError("cannot build address-change scenario; no future service node")


def _nearest_different_customer(problem: ProblemData, customer_id: int) -> int:
    distances = problem.distance_matrix.loc[int(customer_id)].sort_values()
    for candidate, _distance in distances.items():
        candidate_id = int(candidate)
        if candidate_id not in {0, int(customer_id)}:
            return candidate_id
    raise ValueError(f"no proxy customer available for customer {customer_id}")


def _is_green_node(problem: ProblemData, node_id: int) -> bool:
    rows = problem.service_nodes[problem.service_nodes["node_id"].astype(int) == int(node_id)]
    if rows.empty:
        return False
    return bool(rows.iloc[0]["is_green_zone"])
