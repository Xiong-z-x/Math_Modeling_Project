# -*- coding: utf-8 -*-
"""Smoke tests for ALNS operators and short optimization runs."""

from __future__ import annotations

from random import Random

from green_logistics.alns import ALNSConfig, run_alns
from green_logistics.data_processing import load_problem_data
from green_logistics.initial_solution import RouteSpec, construct_initial_route_specs, schedule_route_specs
from green_logistics.operators import (
    greedy_insert,
    random_remove,
    regret2_insert,
    time_oriented_insert,
)
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
