# -*- coding: utf-8 -*-
"""Tests for Problem 1 diagnostics used before round-2 optimization."""

from __future__ import annotations

import pandas as pd

from green_logistics.data_processing.loader import ProblemData
from green_logistics.diagnostics import (
    diagnose_green_zone_capacity,
    diagnose_late_stops,
    diagnose_problem2_policy_conflicts,
)
from green_logistics.solution import evaluate_route, evaluate_solution


def _diagnostic_problem() -> ProblemData:
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
                "latest_min": 500.0,
                "is_green_zone": True,
            },
            {
                "node_id": 20,
                "customer_id": 2,
                "split_index": 1,
                "split_count": 1,
                "demand_weight": 700.0,
                "demand_volume": 3.0,
                "earliest_min": 480.0,
                "latest_min": 650.0,
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
    return ProblemData(
        orders=pd.DataFrame(),
        coordinates=pd.DataFrame(),
        distance_matrix=distance_matrix,
        time_windows=pd.DataFrame(),
        customer_demands=pd.DataFrame(),
        service_nodes=service_nodes,
        node_to_customer={10: 1, 20: 2},
        no_order_customer_ids=[],
        green_customer_ids=[1],
        active_green_customer_ids=[1],
    )


def test_diagnose_late_stops_classifies_direct_and_cascade_lateness() -> None:
    problem = _diagnostic_problem()
    direct_late = evaluate_route(
        problem,
        "F1",
        [10],
        depart_min=480.0,
        physical_vehicle_id="F1-001",
        trip_id="T0001",
    )
    cascade_late = evaluate_route(
        problem,
        "F1",
        [20],
        depart_min=650.0,
        physical_vehicle_id="F1-001",
        trip_id="T0002",
    )
    solution = evaluate_solution([direct_late, cascade_late], required_node_ids={10, 20})

    diagnostics = diagnose_late_stops(problem, solution)

    assert diagnostics["service_node_id"].tolist() == [10, 20]
    assert diagnostics["trip_position_on_vehicle"].tolist() == [1, 2]
    assert diagnostics.loc[0, "classification"].startswith("Type A")
    assert diagnostics.loc[1, "classification"].startswith("Type B")
    assert diagnostics.loc[0, "direct_late_min"] > 0.0
    assert diagnostics.loc[1, "direct_late_min"] == 0.0


def test_diagnose_green_zone_capacity_reports_ev_and_green_demand() -> None:
    problem = _diagnostic_problem()

    diagnostics = diagnose_green_zone_capacity(problem)

    row = diagnostics.iloc[0]
    assert row["green_service_node_count"] == 1
    assert row["green_total_weight_kg"] == 500.0
    assert row["green_total_volume_m3"] == 2.0
    assert row["ev_total_weight_capacity_once_kg"] > row["green_total_weight_kg"]
    assert row["green_nodes_feasible_by_E2_count"] == 1


def test_diagnose_problem2_policy_conflicts_flags_fuel_green_stops_only() -> None:
    problem = _diagnostic_problem()
    fuel_green = evaluate_route(
        problem,
        "F1",
        [10],
        depart_min=480.0,
        physical_vehicle_id="F1-001",
        trip_id="T0001",
    )
    fuel_non_green = evaluate_route(
        problem,
        "F1",
        [20],
        depart_min=480.0,
        physical_vehicle_id="F1-002",
        trip_id="T0002",
    )
    solution = evaluate_solution([fuel_green, fuel_non_green], required_node_ids={10, 20})

    diagnostics = diagnose_problem2_policy_conflicts(problem, solution)

    flags = {
        int(row.service_node_id): bool(row.would_violate_problem2_policy)
        for row in diagnostics.itertuples()
    }
    assert flags == {10: True, 20: False}
