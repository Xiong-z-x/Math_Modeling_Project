# -*- coding: utf-8 -*-
"""Tests for scheduler-level rescue of residual late trips."""

from __future__ import annotations

import pandas as pd

from green_logistics.data_processing.loader import ProblemData
from green_logistics.initial_solution import RouteSpec
from green_logistics.metrics import solution_quality_metrics
from green_logistics.scheduler import schedule_route_specs
from green_logistics.scheduler_local_search import rescue_late_routes


def test_rescue_late_routes_splits_composite_late_route_when_quality_improves() -> None:
    service_nodes = pd.DataFrame(
        [
            {
                "node_id": 10,
                "customer_id": 1,
                "split_index": 1,
                "split_count": 1,
                "demand_weight": 500.0,
                "demand_volume": 2.0,
                "earliest_min": 549.0,
                "latest_min": 650.0,
                "is_green_zone": False,
            },
            {
                "node_id": 20,
                "customer_id": 2,
                "split_index": 1,
                "split_count": 1,
                "demand_weight": 800.0,
                "demand_volume": 3.0,
                "earliest_min": 570.0,
                "latest_min": 575.0,
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
    specs = (RouteSpec("F1", (10, 20)),)
    baseline = schedule_route_specs(problem, specs, vehicle_counts={"F1": 2})

    improved_specs, improved = rescue_late_routes(
        problem,
        specs,
        baseline,
        vehicle_counts={"F1": 2},
    )

    assert len(improved_specs) == 2
    assert solution_quality_metrics(improved).late_stop_count <= solution_quality_metrics(baseline).late_stop_count
    assert improved.is_complete
    assert improved.is_capacity_feasible
