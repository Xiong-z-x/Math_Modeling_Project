# -*- coding: utf-8 -*-
"""Tests for feasible initial-solution construction."""

from __future__ import annotations

import pandas as pd
import pytest

from green_logistics.constants import FIXED_COST_PER_VEHICLE, VEHICLE_TYPES
from green_logistics.data_processing import load_problem_data
from green_logistics.data_processing.loader import ProblemData
from green_logistics.initial_solution import RouteSpec, construct_initial_solution, schedule_route_specs
from green_logistics.metrics import solution_quality_metrics
from tests.test_solution import _small_problem_data


def test_schedule_route_specs_reuses_physical_vehicle_for_multiple_trips() -> None:
    problem = _small_problem_data()
    specs = (
        RouteSpec(vehicle_type_id="F1", service_node_ids=(10,)),
        RouteSpec(vehicle_type_id="F1", service_node_ids=(20,)),
    )

    solution = schedule_route_specs(problem, specs, vehicle_counts={"F1": 1})

    assert solution.is_complete
    assert solution.vehicle_trip_usage_by_type == {"F1": 2}
    assert solution.vehicle_physical_usage_by_type == {"F1": 1}
    assert solution.fixed_cost == pytest.approx(FIXED_COST_PER_VEHICLE)
    assert solution.routes[0].physical_vehicle_id == "F1-001"
    assert solution.routes[1].physical_vehicle_id == "F1-001"
    assert solution.routes[1].depart_min >= solution.routes[0].return_min


def test_schedule_route_specs_delays_departure_to_reduce_first_stop_wait() -> None:
    problem = _small_problem_data()
    specs = (RouteSpec(vehicle_type_id="F1", service_node_ids=(10,)),)

    solution = schedule_route_specs(problem, specs, vehicle_counts={"F1": 1})

    route = solution.routes[0]
    assert route.depart_min > 480.0
    assert route.stops[0].arrival_min == pytest.approx(route.stops[0].earliest_min, abs=1e-4)
    assert route.stops[0].wait_min == pytest.approx(0.0, abs=1e-4)


def test_schedule_route_specs_can_choose_lower_cost_ev_when_available() -> None:
    problem = _small_problem_data()
    specs = (RouteSpec(vehicle_type_id="F1", service_node_ids=(10,)),)

    solution = schedule_route_specs(problem, specs, vehicle_counts={"F1": 1, "E1": 1})

    assert solution.routes[0].vehicle_type_id == "E1"
    assert solution.vehicle_physical_usage_by_type == {"E1": 1}


def test_schedule_route_specs_prefers_new_vehicle_to_avoid_late_stop() -> None:
    service_nodes = pd.DataFrame(
        [
            {
                "node_id": 10,
                "customer_id": 1,
                "split_index": 1,
                "split_count": 1,
                "demand_weight": 500.0,
                "demand_volume": 2.0,
                "earliest_min": 480.0,
                "latest_min": 1000.0,
                "is_green_zone": False,
            },
            {
                "node_id": 20,
                "customer_id": 2,
                "split_index": 1,
                "split_count": 1,
                "demand_weight": 500.0,
                "demand_volume": 2.0,
                "earliest_min": 600.0,
                "latest_min": 630.0,
                "is_green_zone": False,
            },
        ]
    )
    distance_matrix = pd.DataFrame(
        [
            [0.0, 39.2, 9.8],
            [39.2, 0.0, 9.8],
            [9.8, 9.8, 0.0],
        ],
        index=[0, 1, 2],
        columns=[0, 1, 2],
    )
    problem = ProblemData(
        orders=pd.DataFrame(),
        coordinates=pd.DataFrame(),
        distance_matrix=distance_matrix,
        time_windows=pd.DataFrame(),
        customer_demands=pd.DataFrame(),
        service_nodes=service_nodes,
        node_to_customer={10: 1, 20: 2},
        no_order_customer_ids=[],
        green_customer_ids=[],
        active_green_customer_ids=[],
    )
    specs = (
        RouteSpec("F1", (10,)),
        RouteSpec("F1", (20,)),
    )

    solution = schedule_route_specs(problem, specs, vehicle_counts={"F1": 2})

    assert solution.vehicle_physical_usage_by_type == {"F1": 2}
    assert solution.fixed_cost == pytest.approx(2 * FIXED_COST_PER_VEHICLE)
    assert solution_quality_metrics(solution).late_stop_count == 0


def test_construct_initial_solution_on_real_data_is_complete_and_capacity_feasible() -> None:
    problem = load_problem_data(".")

    solution = construct_initial_solution(problem)

    required_nodes = set(problem.service_nodes["node_id"].astype(int).tolist())
    served_nodes = [node_id for route in solution.routes for node_id in route.service_node_ids]
    served_weight = sum(route.total_weight_kg for route in solution.routes)
    served_volume = sum(route.total_volume_m3 for route in solution.routes)

    assert solution.is_complete
    assert solution.is_capacity_feasible
    assert set(served_nodes) == required_nodes
    assert len(served_nodes) == len(required_nodes)
    assert served_weight == pytest.approx(problem.service_nodes["demand_weight"].sum())
    assert served_volume == pytest.approx(problem.service_nodes["demand_volume"].sum())

    for vehicle_type_id, used_count in solution.vehicle_physical_usage_by_type.items():
        assert used_count <= VEHICLE_TYPES[vehicle_type_id].count

    assert solution.total_cost > 0
    assert solution.total_distance_km > 0
