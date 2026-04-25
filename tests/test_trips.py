# -*- coding: utf-8 -*-
"""Tests for lightweight trip descriptors."""

from __future__ import annotations

from green_logistics.initial_solution import RouteSpec
from green_logistics.trips import describe_route_spec
from tests.test_solution import _small_problem_data


def test_describe_route_spec_uses_service_nodes_but_reports_customer_ids() -> None:
    problem = _small_problem_data()
    problem.service_nodes.loc[problem.service_nodes["node_id"] == 10, "is_green_zone"] = True
    spec = RouteSpec("F1", (10, 20))

    descriptor = describe_route_spec(problem, spec)

    assert descriptor.service_node_ids == (10, 20)
    assert descriptor.customer_ids == (1, 2)
    assert descriptor.total_weight_kg == 1300.0
    assert descriptor.total_volume_m3 == 5.0
    assert descriptor.earliest_window_min == 549.0
    assert descriptor.latest_window_min == 600.0
    assert descriptor.estimated_duration_min > 0.0
    assert descriptor.is_green_zone_touched
    assert descriptor.green_stop_count == 1
