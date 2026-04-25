# -*- coding: utf-8 -*-
"""Tests for solution service-quality metrics and search scores."""

from __future__ import annotations

import pytest

from green_logistics.metrics import (
    SearchScoreWeights,
    route_quality_score,
    score_solution,
    solution_quality_metrics,
)
from green_logistics.solution import evaluate_route, evaluate_solution
from tests.test_solution import _small_problem_data


def test_default_route_quality_score_prefers_expensive_on_time_over_large_lateness() -> None:
    problem = _small_problem_data()
    late_route = evaluate_route(problem, "F1", [20], depart_min=720.0)
    on_time_route = evaluate_route(
        problem,
        "F1",
        [20],
        depart_min=480.0,
        fixed_cost=1_000.0,
    )

    assert late_route.stops[0].late_min > 60.0
    assert on_time_route.stops[0].late_min == pytest.approx(0.0)
    assert route_quality_score(on_time_route) < route_quality_score(late_route)


def test_solution_quality_metrics_count_late_wait_return_and_vehicle_reuse() -> None:
    problem = _small_problem_data()
    early_route = evaluate_route(
        problem,
        "F1",
        [10],
        depart_min=480.0,
        physical_vehicle_id="F1-001",
    )
    late_route = evaluate_route(
        problem,
        "F1",
        [20],
        depart_min=650.0,
        physical_vehicle_id="F1-001",
    )
    midnight_route = evaluate_route(
        problem,
        "F1",
        [10],
        depart_min=1430.0,
        physical_vehicle_id="F1-002",
    )
    solution = evaluate_solution([early_route, late_route, midnight_route])

    metrics = solution_quality_metrics(solution)

    late_values = [stop.late_min for route in solution.routes for stop in route.stops]
    wait_values = [stop.wait_min for route in solution.routes for stop in route.stops]
    assert metrics.late_stop_count == sum(1 for value in late_values if value > 1e-9)
    assert metrics.total_late_min == pytest.approx(sum(late_values))
    assert metrics.max_late_min == pytest.approx(max(late_values))
    assert metrics.wait_stop_count == sum(1 for value in wait_values if value > 1e-9)
    assert metrics.total_wait_min == pytest.approx(sum(wait_values))
    assert metrics.return_after_midnight_count == 1
    assert metrics.max_return_min == pytest.approx(max(route.return_min for route in solution.routes))
    assert metrics.max_trips_per_physical_vehicle == 2
    assert metrics.mean_trips_per_physical_vehicle == pytest.approx(1.5)


def test_score_solution_keeps_true_cost_separate_from_search_penalty() -> None:
    problem = _small_problem_data()
    route = evaluate_route(problem, "F1", [20], depart_min=650.0)
    solution = evaluate_solution([route])
    weights = SearchScoreWeights(late_stop=300.0, total_late_min=1.0, max_late_min=5.0)

    metrics = solution_quality_metrics(solution)
    expected_penalty = (
        300.0 * metrics.late_stop_count
        + metrics.total_late_min
        + 5.0 * metrics.max_late_min
    )

    assert score_solution(solution, weights) == pytest.approx(solution.total_cost + expected_penalty)
    assert route_quality_score(route, weights) == pytest.approx(route.total_cost + expected_penalty)
