# -*- coding: utf-8 -*-
"""Tests for route and solution evaluation."""

from __future__ import annotations

import pandas as pd
import pytest

from green_logistics.data_processing.loader import ProblemData
from green_logistics.solution import evaluate_route, evaluate_solution


def _small_problem_data() -> ProblemData:
    service_nodes = pd.DataFrame(
        [
            {
                "node_id": 10,
                "customer_id": 1,
                "split_index": 1,
                "split_count": 1,
                "demand_weight": 500.0,
                "demand_volume": 2.0,
                "earliest_min": 549,
                "latest_min": 600,
                "is_green_zone": False,
            },
            {
                "node_id": 20,
                "customer_id": 2,
                "split_index": 1,
                "split_count": 1,
                "demand_weight": 800.0,
                "demand_volume": 3.0,
                "earliest_min": 570,
                "latest_min": 650,
                "is_green_zone": False,
            },
        ]
    )
    distance_matrix = pd.DataFrame(
        [
            [0.0, 9.8, 4.9],
            [9.8, 0.0, 9.8],
            [4.9, 9.8, 0.0],
        ],
        index=[0, 1, 2],
        columns=[0, 1, 2],
    )
    time_windows = pd.DataFrame(
        [
            {"customer_id": 1, "earliest_min": 549, "latest_min": 600},
            {"customer_id": 2, "earliest_min": 570, "latest_min": 650},
        ]
    )
    return ProblemData(
        orders=pd.DataFrame(),
        coordinates=pd.DataFrame(),
        distance_matrix=distance_matrix,
        time_windows=time_windows,
        customer_demands=pd.DataFrame(),
        service_nodes=service_nodes,
        node_to_customer={10: 1, 20: 2},
        no_order_customer_ids=[],
        green_customer_ids=[],
        active_green_customer_ids=[],
    )


def test_evaluate_route_uses_customer_ids_for_distances_and_recurses_times() -> None:
    problem = _small_problem_data()

    route = evaluate_route(problem, "F1", [10, 20], depart_min=480.0)

    assert route.vehicle_type_id == "F1"
    assert route.service_node_ids == (10, 20)
    assert route.customer_ids == (1, 2)
    assert route.total_weight_kg == pytest.approx(1300.0)
    assert route.total_volume_m3 == pytest.approx(5.0)
    assert route.is_capacity_feasible
    assert route.total_distance_km == pytest.approx(24.5)

    first, second = route.stops
    assert first.arrival_min == pytest.approx(540.0)
    assert first.wait_min == pytest.approx(9.0)
    assert first.departure_min == pytest.approx(569.0)
    assert second.arrival_min == pytest.approx(569.0 + 9.8 / 55.3 * 60.0)
    assert second.wait_min == pytest.approx(0.0)
    assert second.departure_min == pytest.approx(second.arrival_min + 20.0)

    assert route.arcs[0].from_customer_id == 0
    assert route.arcs[0].to_customer_id == 1
    assert route.arcs[0].load_weight_kg == pytest.approx(1300.0)
    assert route.arcs[1].load_weight_kg == pytest.approx(800.0)
    assert route.arcs[2].to_customer_id == 0
    assert route.arcs[2].load_weight_kg == pytest.approx(0.0)
    assert route.energy_cost > 0
    assert route.carbon_cost > 0
    assert route.total_cost == pytest.approx(
        route.energy_cost + route.carbon_cost + route.penalty_cost
    )


def test_evaluate_route_flags_capacity_violation() -> None:
    problem = _small_problem_data()

    route = evaluate_route(problem, "F3", [10, 20], depart_min=480.0)

    assert not route.is_capacity_feasible
    assert route.total_weight_kg > route.vehicle_type.max_weight_kg


def test_evaluate_solution_checks_node_coverage_once() -> None:
    problem = _small_problem_data()
    route_a = evaluate_route(problem, "F1", [10], depart_min=480.0)
    route_b = evaluate_route(problem, "F1", [20], depart_min=480.0)

    solution = evaluate_solution([route_a, route_b], required_node_ids={10, 20})

    assert solution.is_complete
    assert solution.duplicate_node_ids == ()
    assert solution.missing_node_ids == ()
    assert solution.total_cost == pytest.approx(route_a.total_cost + route_b.total_cost)
    assert solution.vehicle_trip_usage_by_type == {"F1": 2}


def test_evaluate_solution_reports_duplicates_and_missing_nodes() -> None:
    problem = _small_problem_data()
    route_a = evaluate_route(problem, "F1", [10], depart_min=480.0)
    route_b = evaluate_route(problem, "F1", [10], depart_min=480.0)

    solution = evaluate_solution([route_a, route_b], required_node_ids={10, 20})

    assert not solution.is_complete
    assert solution.duplicate_node_ids == (10,)
    assert solution.missing_node_ids == (20,)
