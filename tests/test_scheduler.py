# -*- coding: utf-8 -*-
"""Tests for the second-stage physical vehicle scheduler."""

from __future__ import annotations

from green_logistics.initial_solution import RouteSpec
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
