# -*- coding: utf-8 -*-

from collections import Counter

import pytest

from green_logistics.constants import VEHICLE_TYPES
from green_logistics.data_processing import load_problem_data
from green_logistics.problem_variants import SplitMode, load_problem_variant


def _split_counts(problem):
    rows = problem.customer_demands[["customer_id", "split_count"]].itertuples(index=False)
    return {int(row.customer_id): int(row.split_count) for row in rows}


def test_default_variant_matches_current_loader():
    direct = load_problem_data(".")
    variant = load_problem_variant(".", SplitMode.DEFAULT)

    assert variant.name == "default_split"
    assert len(variant.data.service_nodes) == 148
    assert variant.data.service_nodes.equals(direct.service_nodes)
    assert variant.data.node_to_customer == direct.node_to_customer


def test_green_e2_adaptive_preserves_total_demand_and_non_green_splits():
    default = load_problem_variant(".", SplitMode.DEFAULT)
    adaptive = load_problem_variant(".", SplitMode.GREEN_E2_ADAPTIVE)

    assert adaptive.name == "green_e2_adaptive"
    assert len(adaptive.data.service_nodes) == 166
    assert int(adaptive.data.service_nodes["is_green_zone"].sum()) == 37
    assert adaptive.data.service_nodes["demand_weight"].sum() == pytest.approx(
        default.data.service_nodes["demand_weight"].sum()
    )
    assert adaptive.data.service_nodes["demand_volume"].sum() == pytest.approx(
        default.data.service_nodes["demand_volume"].sum()
    )
    assert adaptive.data.active_green_customer_ids == default.data.active_green_customer_ids
    assert adaptive.data.green_customer_ids == default.data.green_customer_ids

    default_counts = _split_counts(default.data)
    adaptive_counts = _split_counts(adaptive.data)
    green_customers = set(default.data.active_green_customer_ids)
    for customer_id, split_count in default_counts.items():
        if customer_id not in green_customers:
            assert adaptive_counts[customer_id] == split_count


def test_green_e2_adaptive_green_nodes_fit_e2_capacity():
    adaptive = load_problem_variant(".", SplitMode.GREEN_E2_ADAPTIVE)
    e2 = VEHICLE_TYPES["E2"]
    green_nodes = adaptive.data.service_nodes[adaptive.data.service_nodes["is_green_zone"]]

    assert not green_nodes.empty
    assert (green_nodes["demand_weight"] <= e2.max_weight_kg + 1e-9).all()
    assert (green_nodes["demand_volume"] <= e2.max_volume_m3 + 1e-9).all()


def test_green_e2_adaptive_node_mapping_is_complete_and_unique():
    adaptive = load_problem_variant(".", SplitMode.GREEN_E2_ADAPTIVE)
    node_ids = adaptive.data.service_nodes["node_id"].astype(int).tolist()

    assert node_ids == list(range(1, len(node_ids) + 1))
    assert set(adaptive.data.node_to_customer) == set(node_ids)
    mapped_customers = Counter(adaptive.data.node_to_customer.values())
    demand_counts = _split_counts(adaptive.data)
    assert mapped_customers == Counter(demand_counts)


def test_green_hotspot_partial_is_bounded_and_preserves_demand():
    default = load_problem_variant(".", SplitMode.DEFAULT)
    hotspot = load_problem_variant(".", SplitMode.GREEN_HOTSPOT_PARTIAL)

    assert hotspot.name == "green_hotspot_partial"
    assert 148 < len(hotspot.data.service_nodes) < 166
    assert 19 < int(hotspot.data.service_nodes["is_green_zone"].sum()) < 37
    assert hotspot.data.service_nodes["demand_weight"].sum() == pytest.approx(
        default.data.service_nodes["demand_weight"].sum()
    )
    assert hotspot.data.service_nodes["demand_volume"].sum() == pytest.approx(
        default.data.service_nodes["demand_volume"].sum()
    )

    default_counts = _split_counts(default.data)
    hotspot_counts = _split_counts(hotspot.data)
    hotspot_customers = {6, 7, 8, 11}
    for customer_id, split_count in default_counts.items():
        if customer_id not in hotspot_customers:
            assert hotspot_counts[customer_id] == split_count

    e2 = VEHICLE_TYPES["E2"]
    hotspot_nodes = hotspot.data.service_nodes[
        hotspot.data.service_nodes["customer_id"].isin(hotspot_customers)
    ]
    e2_fit_count = int(
        (
            (hotspot_nodes["demand_weight"] <= e2.max_weight_kg + 1e-9)
            & (hotspot_nodes["demand_volume"] <= e2.max_volume_m3 + 1e-9)
        ).sum()
    )
    assert e2_fit_count >= len(hotspot_customers)
