# -*- coding: utf-8 -*-
"""Tests for the second-stage physical vehicle scheduler."""

from __future__ import annotations

from green_logistics.data_processing import load_problem_data
from green_logistics.initial_solution import RouteSpec
from green_logistics.policies import GreenZonePolicyEvaluator
from green_logistics.scheduler import SchedulingConfig, schedule_route_specs
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
