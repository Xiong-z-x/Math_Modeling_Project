# -*- coding: utf-8 -*-
"""Tests for the second-stage physical vehicle scheduler."""

from __future__ import annotations

from green_logistics.data_processing import load_problem_data
from green_logistics.data_processing.loader import ProblemData
from green_logistics.initial_solution import RouteSpec
from green_logistics.policies import GreenZonePolicyEvaluator
from green_logistics.scheduler import SchedulingConfig, schedule_route_specs
import pandas as pd
from tests.test_solution import _small_problem_data


def test_scheduler_config_reload_time_delays_vehicle_reuse() -> None:
    problem = _small_problem_data()
    specs = (
        RouteSpec("F1", (10,)),
        RouteSpec("F1", (20,)),
    )

    solution = schedule_route_specs(
        problem,
        specs,
        vehicle_counts={"F1": 1},
        config=SchedulingConfig(reload_time_min=15.0),
    )

    assert len(solution.routes) == 2
    assert solution.routes[1].depart_min >= solution.routes[0].return_min + 15.0


def test_initial_solution_keeps_legacy_scheduler_import() -> None:
    from green_logistics.initial_solution import schedule_route_specs as legacy_schedule

    assert legacy_schedule is schedule_route_specs


def test_route_spec_allowed_vehicle_types_are_respected() -> None:
    problem = _small_problem_data()
    specs = (
        RouteSpec("F1", (10,), allowed_vehicle_type_ids=("F1",)),
    )

    solution = schedule_route_specs(problem, specs, vehicle_counts={"F1": 1, "E1": 1})

    assert solution.routes[0].vehicle_type_id == "F1"


def test_policy_scheduler_can_delay_fuel_green_trip_until_restriction_end() -> None:
    problem = load_problem_data(".")
    green_nodes = problem.service_nodes[
        problem.service_nodes["is_green_zone"] & (problem.service_nodes["latest_min"] < 960)
    ]
    green_node_id = int(green_nodes.iloc[0]["node_id"])
    spec = RouteSpec(vehicle_type_id="F1", service_node_ids=(green_node_id,))
    policy = GreenZonePolicyEvaluator()

    solution = schedule_route_specs(
        problem,
        (spec,),
        vehicle_counts={"F1": 1, "F2": 0, "F3": 0, "E1": 0, "E2": 0},
        config=SchedulingConfig(
            policy_evaluator=policy,
            optimize_departure_grid_min=15,
            max_departure_delay_min=720.0,
        ),
    )

    assert policy.solution_violation_count(problem, solution) == 0
    assert solution.routes[0].stops[0].arrival_min >= 960.0


def test_ev_reservation_keeps_ev_for_critical_green_trip() -> None:
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
                "latest_min": 650.0,
                "is_green_zone": False,
            },
            {
                "node_id": 20,
                "customer_id": 2,
                "split_index": 1,
                "split_count": 1,
                "demand_weight": 600.0,
                "demand_volume": 2.5,
                "earliest_min": 500.0,
                "latest_min": 700.0,
                "is_green_zone": True,
            },
        ]
    )
    problem = ProblemData(
        orders=pd.DataFrame(),
        coordinates=pd.DataFrame(),
        distance_matrix=pd.DataFrame(
            [
                [0.0, 4.9, 4.9],
                [4.9, 0.0, 9.8],
                [4.9, 9.8, 0.0],
            ],
            index=[0, 1, 2],
            columns=[0, 1, 2],
        ),
        time_windows=pd.DataFrame(),
        customer_demands=pd.DataFrame(),
        service_nodes=service_nodes,
        node_to_customer={10: 1, 20: 2},
        no_order_customer_ids=[],
        green_customer_ids=[2],
        active_green_customer_ids=[2],
    )
    specs = (
        RouteSpec("E1", (10,)),
        RouteSpec("E1", (20,), allowed_vehicle_type_ids=("E1", "E2"), policy_service_mode="ev_green"),
    )

    solution = schedule_route_specs(
        problem,
        specs,
        vehicle_counts={"E1": 1, "F1": 1},
        config=SchedulingConfig(ev_reservation_enabled=True, ev_reservation_penalty=100_000.0),
    )

    by_node = {route.service_node_ids[0]: route.vehicle_type_id for route in solution.routes}
    assert by_node[10] == "F1"
    assert by_node[20] == "E1"
