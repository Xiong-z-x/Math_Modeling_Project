# -*- coding: utf-8 -*-
"""Smoke tests for ALNS operators and short optimization runs."""

from __future__ import annotations

from random import Random

from dataclasses import replace

from green_logistics.alns import ALNSConfig, _is_better_formal_solution, run_alns
from green_logistics.data_processing import load_problem_data
from green_logistics.initial_solution import RouteSpec, construct_initial_route_specs, schedule_route_specs
from green_logistics.metrics import score_solution
from green_logistics.operators import (
    actual_late_remove,
    greedy_insert,
    late_route_split,
    late_suffix_remove,
    midnight_route_remove,
    random_remove,
    regret2_insert,
    time_oriented_insert,
)
from green_logistics.policies import GreenZonePolicyEvaluator
from green_logistics.solution import evaluate_route, evaluate_solution
from tests.test_solution import _small_problem_data


def test_remove_and_insert_operators_preserve_service_node_set() -> None:
    problem = _small_problem_data()
    specs = (
        RouteSpec("F1", (10, 20)),
    )

    partial_specs, removed = random_remove(specs, Random(7), remove_count=1)

    assert len(removed) == 1
    for repair in (greedy_insert, regret2_insert, time_oriented_insert):
        repaired = repair(problem, partial_specs, removed)
        served = sorted(node_id for spec in repaired for node_id in spec.service_node_ids)
        assert served == [10, 20]


def test_true_lateness_destroy_operators_use_current_scheduled_solution() -> None:
    problem = _small_problem_data()
    specs = (
        RouteSpec("F1", (10,)),
        RouteSpec("F1", (20,)),
    )
    on_time = evaluate_route(problem, "F1", [10], depart_min=480.0)
    late = evaluate_route(problem, "F1", [20], depart_min=650.0)
    solution = evaluate_solution([on_time, late])

    partial_specs, removed = actual_late_remove(problem, specs, solution, Random(3), remove_count=1)

    assert removed == (20,)
    served = sorted(node_id for spec in partial_specs for node_id in spec.service_node_ids)
    assert served == [10]


def test_late_suffix_midnight_and_split_operators_target_bad_routes() -> None:
    problem = _small_problem_data()
    specs = (RouteSpec("F1", (10, 20)),)
    late_route = evaluate_route(problem, "F1", [10, 20], depart_min=650.0)
    midnight_route = evaluate_route(problem, "F1", [10], depart_min=1430.0)
    late_solution = evaluate_solution([late_route])
    midnight_solution = evaluate_solution([midnight_route])

    _partial, suffix_removed = late_suffix_remove(problem, specs, late_solution, Random(5), remove_count=2)
    assert suffix_removed == (10, 20)

    _partial, midnight_removed = midnight_route_remove(problem, specs, midnight_solution, Random(5), remove_count=2)
    assert midnight_removed == (10,)

    split_specs, split_removed = late_route_split(problem, specs, late_solution, Random(5), remove_count=2)
    assert split_removed == ()
    assert [spec.service_node_ids for spec in split_specs] == [(10,), (20,)]


def test_short_alns_run_on_real_data_keeps_solution_feasible_and_no_worse() -> None:
    problem = load_problem_data(".")
    initial_specs = construct_initial_route_specs(problem)
    initial_solution = schedule_route_specs(problem, initial_specs)

    result = run_alns(
        problem,
        initial_specs=initial_specs,
        config=ALNSConfig(iterations=8, remove_count=4, seed=11),
    )

    assert result.initial_solution.total_cost == initial_solution.total_cost
    assert result.best_solution.is_complete
    assert result.best_solution.is_capacity_feasible
    assert result.best_solution.total_cost <= initial_solution.total_cost
    assert len(result.history) == 9
    assert result.history[0].current_score == score_solution(initial_solution)
    assert result.history[-1].candidate_late_stop_count >= 0
    assert result.history[-1].candidate_max_late_min >= 0.0


def test_formal_best_selection_prioritizes_official_total_cost() -> None:
    problem = _small_problem_data()
    cheaper_late = evaluate_route(problem, "F1", [10], depart_min=650.0, fixed_cost=0.0)
    expensive_on_time = evaluate_route(problem, "F1", [10], depart_min=480.0, fixed_cost=400.0)
    cheaper_solution = evaluate_solution([cheaper_late], required_node_ids={10})
    expensive_solution = evaluate_solution([expensive_on_time], required_node_ids={10})

    assert cheaper_solution.total_cost < expensive_solution.total_cost
    assert _is_better_formal_solution(cheaper_solution, expensive_solution)
    assert not _is_better_formal_solution(expensive_solution, cheaper_solution)


def test_problem2_best_selection_rejects_lower_cost_policy_violation() -> None:
    problem = load_problem_data(".")
    green_node_id = int(
        problem.service_nodes[
            problem.service_nodes["is_green_zone"] & (problem.service_nodes["latest_min"] < 960)
        ].iloc[0]["node_id"]
    )
    policy = GreenZonePolicyEvaluator()

    illegal_route = evaluate_route(problem, "F1", (green_node_id,), depart_min=480.0, fixed_cost=0.0)
    illegal_solution = evaluate_solution((illegal_route,), required_node_ids=[green_node_id])
    legal_route = evaluate_route(problem, "E1", (green_node_id,), depart_min=480.0, fixed_cost=400.0)
    legal_solution = evaluate_solution((legal_route,), required_node_ids=[green_node_id])

    cheap_illegal = replace(illegal_solution, total_cost=1.0)
    expensive_legal = replace(legal_solution, total_cost=9999.0)

    assert policy.solution_violation_count(problem, cheap_illegal) > 0
    assert policy.solution_violation_count(problem, expensive_legal) == 0
    assert not _is_better_formal_solution(
        cheap_illegal,
        expensive_legal,
        problem=problem,
        policy_evaluator=policy,
    )
