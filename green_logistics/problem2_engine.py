# -*- coding: utf-8 -*-
"""Problem 2 orchestration for green-zone fuel restrictions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

from .alns import ALNSConfig, ALNSResult, run_alns
from .constants import VEHICLE_TYPES
from .initial_solution import RouteSpec, construct_initial_route_specs
from .metrics import solution_quality_metrics
from .policies import GreenZonePolicyEvaluator
from .problem_variants import ProblemVariant
from .scheduler import SchedulingConfig, schedule_route_specs
from .solution import Solution


@dataclass(frozen=True)
class Problem2RunResult:
    """Structured result for one Problem 2 candidate variant."""

    variant_name: str
    service_node_count: int
    green_service_node_count: int
    initial_solution: Solution
    solution: Solution
    alns_result: ALNSResult
    policy_conflict_count: int
    total_cost: float
    is_complete: bool
    is_capacity_feasible: bool
    quality_metrics: dict[str, float | int]


@dataclass(frozen=True)
class Problem2Engine:
    """Run one or more Problem 2 candidate variants with a hard policy gate."""

    iterations: int = 40
    remove_count: int = 8
    seed: int = 20260424
    initial_temperature: float = 5000.0
    cooling_rate: float = 0.995
    optimize_departure_grid_min: int | None = None
    max_departure_delay_min: float = 720.0

    def run_variant(self, variant: ProblemVariant) -> Problem2RunResult:
        policy = GreenZonePolicyEvaluator()
        scheduling_config = SchedulingConfig(
            policy_evaluator=policy,
            optimize_departure_grid_min=self.optimize_departure_grid_min,
            max_departure_delay_min=self.max_departure_delay_min,
        )
        initial_specs = construct_problem2_initial_route_specs(variant)
        initial_solution = schedule_route_specs(variant.data, initial_specs, config=scheduling_config)
        alns_result = run_alns(
            variant.data,
            initial_specs=initial_specs,
            config=ALNSConfig(
                iterations=self.iterations,
                remove_count=self.remove_count,
                seed=self.seed,
                initial_temperature=self.initial_temperature,
                cooling_rate=self.cooling_rate,
                scheduling_config=scheduling_config,
                policy_evaluator=policy,
            ),
        )
        solution = alns_result.best_solution
        conflict_count = policy.solution_violation_count(variant.data, solution)
        quality = solution_quality_metrics(solution).to_dict()
        return Problem2RunResult(
            variant_name=variant.name,
            service_node_count=variant.service_node_count,
            green_service_node_count=variant.green_service_node_count,
            initial_solution=initial_solution,
            solution=solution,
            alns_result=alns_result,
            policy_conflict_count=conflict_count,
            total_cost=solution.total_cost,
            is_complete=solution.is_complete,
            is_capacity_feasible=solution.is_capacity_feasible,
            quality_metrics=quality,
        )


def choose_recommended_result(results: Sequence[Problem2RunResult]) -> Problem2RunResult:
    """Choose the feasible variant with minimum official total cost."""

    feasible = [
        result for result in results
        if result.is_complete and result.is_capacity_feasible and result.policy_conflict_count == 0
    ]
    if not feasible:
        raise ValueError("no policy-feasible Problem 2 result")
    return min(feasible, key=lambda result: result.total_cost)


def construct_problem2_initial_route_specs(variant: ProblemVariant) -> tuple[RouteSpec, ...]:
    """Construct a policy-aware seed while preserving official customer data."""

    problem = variant.data
    if variant.name == "default_split":
        return construct_initial_route_specs(problem)

    green_node_ids = set(
        problem.service_nodes.loc[
            problem.service_nodes["is_green_zone"], "node_id"
        ].astype(int).tolist()
    )
    non_green_nodes = problem.service_nodes[
        ~problem.service_nodes["node_id"].astype(int).isin(green_node_ids)
    ].reset_index(drop=True)

    specs: list[RouteSpec] = []
    if not non_green_nodes.empty:
        non_green_problem = replace(
            problem,
            service_nodes=non_green_nodes,
            node_to_customer={
                int(row["node_id"]): int(row["customer_id"])
                for row in non_green_nodes.to_dict(orient="records")
            },
        )
        specs.extend(construct_initial_route_specs(non_green_problem))

    green_rows = [
        row for row in problem.service_nodes.to_dict(orient="records")
        if int(row["node_id"]) in green_node_ids
    ]
    specs.extend(_pack_green_ev_specs(green_rows, force_e2=variant.name == "green_e2_adaptive"))
    return tuple(specs)


def _pack_green_ev_specs(green_rows: list[dict[str, object]], *, force_e2: bool) -> tuple[RouteSpec, ...]:
    if not green_rows:
        return ()

    e2 = VEHICLE_TYPES["E2"]
    e1 = VEHICLE_TYPES["E1"]
    sorted_rows = sorted(
        green_rows,
        key=lambda row: (
            float(row["earliest_min"]),
            float(row["latest_min"]),
            -float(row["demand_weight"]),
            int(row["node_id"]),
        ),
    )
    routes: list[dict[str, object]] = []

    for row in sorted_rows:
        best_route: dict[str, object] | None = None
        best_extra_gap = float("inf")
        max_weight = e2.max_weight_kg if force_e2 else e1.max_weight_kg
        max_volume = e2.max_volume_m3 if force_e2 else e1.max_volume_m3
        for route in routes:
            if len(route["rows"]) >= 3:  # type: ignore[arg-type]
                continue
            new_weight = float(route["weight"]) + float(row["demand_weight"])
            new_volume = float(route["volume"]) + float(row["demand_volume"])
            if new_weight > max_weight + 1e-9 or new_volume > max_volume + 1e-9:
                continue
            gap = abs(float(route["earliest"]) - float(row["earliest_min"]))
            if gap < best_extra_gap:
                best_route = route
                best_extra_gap = gap

        if best_route is None:
            routes.append(
                {
                    "rows": [row],
                    "weight": float(row["demand_weight"]),
                    "volume": float(row["demand_volume"]),
                    "earliest": float(row["earliest_min"]),
                }
            )
        else:
            best_route["rows"].append(row)  # type: ignore[index, union-attr]
            best_route["weight"] = float(best_route["weight"]) + float(row["demand_weight"])
            best_route["volume"] = float(best_route["volume"]) + float(row["demand_volume"])

    specs: list[RouteSpec] = []
    for route in routes:
        rows = route["rows"]  # type: ignore[assignment]
        weight = float(route["weight"])
        volume = float(route["volume"])
        vehicle_type_id = "E2" if weight <= e2.max_weight_kg + 1e-9 and volume <= e2.max_volume_m3 + 1e-9 else "E1"
        specs.append(RouteSpec(vehicle_type_id, tuple(int(row["node_id"]) for row in rows)))
    return tuple(specs)
