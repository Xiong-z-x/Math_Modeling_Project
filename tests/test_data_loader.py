# -*- coding: utf-8 -*-
"""Tests for the project data-loading and preprocessing layer.

These tests pin the known facts from the official attachments. They should fail
before `green_logistics.data_loader` exists and pass once the data layer is
implemented.
"""

from __future__ import annotations

import math

from green_logistics.data_processing import load_problem_data, parse_hhmm_to_minutes
from green_logistics.data_loader import load_problem_data as legacy_load_problem_data


EXPECTED_NO_ORDER = [1, 14, 15, 17, 18, 20, 21, 22, 23, 96]
EXPECTED_GREEN_ALL = list(range(1, 16))
EXPECTED_GREEN_ACTIVE = list(range(2, 14))
EXPECTED_SPLIT_CUSTOMERS = [
    6,
    7,
    8,
    10,
    27,
    28,
    31,
    36,
    39,
    42,
    43,
    44,
    45,
    46,
    48,
    49,
    50,
    51,
    52,
    53,
    54,
    55,
    56,
    57,
    59,
    60,
    61,
    62,
    63,
    64,
    65,
    68,
    70,
    71,
    74,
    75,
]


def test_parse_hhmm_to_absolute_minutes() -> None:
    assert parse_hhmm_to_minutes("08:00") == 480
    assert parse_hhmm_to_minutes("09:09") == 549
    assert parse_hhmm_to_minutes("20:58") == 1258


def test_load_problem_data_core_counts() -> None:
    data = load_problem_data(".")

    assert data.orders.shape == (2169, 4)
    assert data.coordinates.shape[0] == 99
    assert data.distance_matrix.shape == (99, 99)
    assert data.customer_demands.shape[0] == 88
    assert data.service_nodes.shape[0] == 148

    assert data.no_order_customer_ids == EXPECTED_NO_ORDER
    assert data.green_customer_ids == EXPECTED_GREEN_ALL
    assert data.active_green_customer_ids == EXPECTED_GREEN_ACTIVE


def test_legacy_data_loader_import_still_works() -> None:
    data = legacy_load_problem_data(".")
    assert data.customer_demands.shape[0] == 88


def test_split_customer_list_and_capacity_bounds() -> None:
    data = load_problem_data(".")

    split_customers = (
        data.customer_demands.loc[data.customer_demands["split_count"] > 1, "customer_id"]
        .astype(int)
        .tolist()
    )
    assert split_customers == EXPECTED_SPLIT_CUSTOMERS

    assert data.service_nodes["demand_weight"].max() <= 3000.0 + 1e-9
    assert data.service_nodes["demand_volume"].max() <= 15.0 + 1e-9

    split_55 = data.customer_demands.loc[
        data.customer_demands["customer_id"] == 55, "split_count"
    ].item()
    split_8 = data.customer_demands.loc[
        data.customer_demands["customer_id"] == 8, "split_count"
    ].item()
    assert split_55 == 5
    assert split_8 == 4


def test_virtual_nodes_preserve_customer_totals() -> None:
    data = load_problem_data(".")

    node_totals = data.service_nodes.groupby("customer_id").agg(
        weight=("demand_weight", "sum"),
        volume=("demand_volume", "sum"),
    )
    demand_totals = data.customer_demands.set_index("customer_id")[
        ["total_weight", "total_volume"]
    ]

    for customer_id, expected in demand_totals.iterrows():
        actual = node_totals.loc[customer_id]
        assert math.isclose(actual["weight"], expected["total_weight"], rel_tol=1e-10)
        assert math.isclose(actual["volume"], expected["total_volume"], rel_tol=1e-10)


def test_distance_matrix_and_time_window_validation() -> None:
    data = load_problem_data(".")

    assert data.distance_matrix.index.tolist() == list(range(99))
    assert data.distance_matrix.columns.tolist() == list(range(99))
    assert (data.distance_matrix.values.diagonal() == 0).all()

    assert data.time_windows["earliest_min"].min() == 549
    assert data.time_windows["latest_min"].max() == 1258
    assert data.time_windows["window_width_min"].min() == 48
    assert data.time_windows["window_width_min"].max() == 90
