# -*- coding: utf-8 -*-
"""Tests for Problem 3 dynamic event state handling."""

from __future__ import annotations

import pytest

from green_logistics.dynamic import (
    DynamicEvent,
    apply_dynamic_event,
    build_dynamic_snapshot,
)
from green_logistics.solution import evaluate_route, evaluate_solution
from tests.test_solution import _small_problem_data


def _two_trip_solution():
    problem = _small_problem_data()
    first = evaluate_route(
        problem,
        "F1",
        [10],
        depart_min=480.0,
        fixed_cost=400.0,
        physical_vehicle_id="F1-001",
        trip_id="T0001",
    )
    second = evaluate_route(
        problem,
        "F1",
        [20],
        depart_min=700.0,
        fixed_cost=0.0,
        physical_vehicle_id="F1-001",
        trip_id="T0002",
    )
    return problem, evaluate_solution([first, second], required_node_ids={10, 20})


def test_build_dynamic_snapshot_classifies_locked_and_unstarted_routes() -> None:
    _problem, solution = _two_trip_solution()
    snapshot = build_dynamic_snapshot(solution, event_time_min=650.0)

    by_trip = {route.trip_id: route for route in snapshot.routes}
    assert by_trip["T0001"].status == "locked_completed"
    assert by_trip["T0002"].status == "unstarted_adjustable"
    assert snapshot.locked_route_ids == ("T0001",)
    assert snapshot.adjustable_route_ids == ("T0002",)
    assert snapshot.completed_node_ids == (10,)
    assert snapshot.adjustable_node_ids == (20,)


def test_cancel_event_removes_only_adjustable_service_node() -> None:
    problem, solution = _two_trip_solution()
    snapshot = build_dynamic_snapshot(solution, event_time_min=650.0)
    event = DynamicEvent(
        event_type="cancel",
        event_time_min=650.0,
        service_node_id=20,
        description="cancel future node 20",
    )

    update = apply_dynamic_event(problem, snapshot, event)

    assert update.cancelled_node_ids == (20,)
    assert update.required_node_ids == (10,)
    assert update.residual_node_ids == ()
    assert 20 not in set(update.problem.service_nodes["node_id"].astype(int))


def test_cancel_event_refuses_to_remove_locked_completed_node() -> None:
    problem, solution = _two_trip_solution()
    snapshot = build_dynamic_snapshot(solution, event_time_min=650.0)
    event = DynamicEvent(event_type="cancel", event_time_min=650.0, service_node_id=10)

    with pytest.raises(ValueError, match="locked"):
        apply_dynamic_event(problem, snapshot, event)


def test_new_order_event_adds_proxy_service_node_without_new_distances() -> None:
    problem, solution = _two_trip_solution()
    snapshot = build_dynamic_snapshot(solution, event_time_min=650.0)
    event = DynamicEvent(
        event_type="new_order",
        event_time_min=650.0,
        new_service_node_id=30,
        proxy_customer_id=2,
        demand_weight_kg=100.0,
        demand_volume_m3=0.5,
        earliest_min=720.0,
        latest_min=820.0,
        description="proxy new order at existing customer 2",
    )

    update = apply_dynamic_event(problem, snapshot, event)

    row = update.problem.service_nodes.set_index("node_id").loc[30]
    assert int(row["customer_id"]) == 2
    assert row["demand_weight"] == pytest.approx(100.0)
    assert update.added_node_ids == (30,)
    assert set(update.residual_node_ids) == {20, 30}
    assert update.problem.node_to_customer[30] == 2


def test_time_window_event_updates_only_adjustable_node() -> None:
    problem, solution = _two_trip_solution()
    snapshot = build_dynamic_snapshot(solution, event_time_min=650.0)
    event = DynamicEvent(
        event_type="time_window_change",
        event_time_min=650.0,
        service_node_id=20,
        earliest_min=650.0,
        latest_min=700.0,
    )

    update = apply_dynamic_event(problem, snapshot, event)
    row = update.problem.service_nodes.set_index("node_id").loc[20]

    assert row["earliest_min"] == pytest.approx(650.0)
    assert row["latest_min"] == pytest.approx(700.0)
    assert update.changed_node_ids == (20,)
