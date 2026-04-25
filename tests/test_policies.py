# -*- coding: utf-8 -*-
"""Tests for policy hooks reserved for Problem 2."""

from __future__ import annotations

from green_logistics.policies import GreenZonePolicyEvaluator, NoPolicyEvaluator
from green_logistics.solution import evaluate_route
from tests.test_solution import _small_problem_data


def test_no_policy_evaluator_leaves_problem1_routes_allowed() -> None:
    problem = _small_problem_data()
    route = evaluate_route(problem, "F1", [10], depart_min=480.0)
    evaluator = NoPolicyEvaluator()

    assert evaluator.route_penalty(problem, route) == 0.0
    assert evaluator.is_route_allowed(problem, route)


def test_green_zone_policy_flags_fuel_stops_during_restricted_window() -> None:
    problem = _small_problem_data()
    problem.service_nodes.loc[problem.service_nodes["node_id"] == 10, "is_green_zone"] = True
    fuel_route = evaluate_route(problem, "F1", [10], depart_min=480.0)
    ev_route = evaluate_route(problem, "E1", [10], depart_min=480.0)
    evaluator = GreenZonePolicyEvaluator()

    assert not evaluator.is_route_allowed(problem, fuel_route)
    assert evaluator.route_penalty(problem, fuel_route) > 0.0
    assert evaluator.is_route_allowed(problem, ev_route)
    assert evaluator.route_penalty(problem, ev_route) == 0.0
