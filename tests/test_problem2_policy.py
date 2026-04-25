# -*- coding: utf-8 -*-

from dataclasses import replace

from green_logistics.data_processing import load_problem_data
from green_logistics.policies import GreenZonePolicyEvaluator
from green_logistics.solution import StopRecord, evaluate_route, evaluate_solution


def _stop(node_id: int, customer_id: int, arrival_min: float) -> StopRecord:
    return StopRecord(
        service_node_id=node_id,
        customer_id=customer_id,
        earliest_min=0.0,
        latest_min=2000.0,
        arrival_min=arrival_min,
        wait_min=0.0,
        late_min=0.0,
        service_start_min=arrival_min,
        departure_min=arrival_min + 20.0,
        demand_weight_kg=1.0,
        demand_volume_m3=1.0,
        load_before_service_kg=1.0,
        load_before_service_m3=1.0,
        load_after_service_kg=0.0,
        load_after_service_m3=0.0,
        penalty_cost=0.0,
    )


def _green_node(problem):
    row = problem.service_nodes[problem.service_nodes["is_green_zone"]].iloc[0]
    return int(row["node_id"]), int(row["customer_id"])


def _non_green_node(problem):
    row = problem.service_nodes[~problem.service_nodes["is_green_zone"]].iloc[0]
    return int(row["node_id"]), int(row["customer_id"])


def test_fuel_green_stop_restricted_window_is_violation():
    problem = load_problem_data(".")
    node_id, customer_id = _green_node(problem)
    policy = GreenZonePolicyEvaluator()

    assert policy.stop_violation(problem, _stop(node_id, customer_id, 480.0), "F1")
    assert policy.stop_violation(problem, _stop(node_id, customer_id, 959.9), "F1")
    assert not policy.stop_violation(problem, _stop(node_id, customer_id, 960.0), "F1")


def test_ev_and_non_green_stops_are_allowed():
    problem = load_problem_data(".")
    green_node_id, green_customer_id = _green_node(problem)
    non_green_node_id, non_green_customer_id = _non_green_node(problem)
    policy = GreenZonePolicyEvaluator()

    assert not policy.stop_violation(problem, _stop(green_node_id, green_customer_id, 600.0), "E1")
    assert not policy.stop_violation(problem, _stop(green_node_id, green_customer_id, 600.0), "E2")
    assert not policy.stop_violation(problem, _stop(non_green_node_id, non_green_customer_id, 600.0), "F1")


def test_route_and_solution_violation_counts_use_actual_arrival_times():
    problem = load_problem_data(".")
    green_node_id, green_customer_id = _green_node(problem)
    route = evaluate_route(problem, "F1", (green_node_id,), depart_min=480.0)
    violating_stop = replace(route.stops[0], arrival_min=600.0, customer_id=green_customer_id)
    legal_stop = replace(route.stops[0], arrival_min=960.0, customer_id=green_customer_id)
    policy = GreenZonePolicyEvaluator()

    violating_route = replace(route, stops=(violating_stop,))
    legal_route = replace(route, stops=(legal_stop,))
    solution = evaluate_solution(
        (violating_route, legal_route),
        required_node_ids=[green_node_id],
    )

    assert policy.route_violation_count(problem, violating_route) == 1
    assert policy.route_violation_count(problem, legal_route) == 0
    assert policy.solution_violation_count(problem, solution) == 1
