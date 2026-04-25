# -*- coding: utf-8 -*-

from green_logistics.problem2_engine import (
    Problem2Engine,
    choose_recommended_result,
    construct_problem2_initial_route_specs,
)
from green_logistics.problem_variants import SplitMode, load_problem_variant


def test_problem2_engine_smoke_default_variant_zero_policy_conflicts():
    variant = load_problem_variant(".", SplitMode.DEFAULT)
    engine = Problem2Engine(
        iterations=1,
        remove_count=4,
        seed=20260424,
        optimize_departure_grid_min=None,
    )

    result = engine.run_variant(variant)

    assert result.variant_name == "default_split"
    assert result.solution.is_complete
    assert result.solution.is_capacity_feasible
    assert result.policy_conflict_count == 0


def test_problem2_recommendation_ignores_infeasible_result():
    class Result:
        def __init__(self, name, cost, conflicts):
            self.variant_name = name
            self.total_cost = cost
            self.policy_conflict_count = conflicts
            self.is_complete = True
            self.is_capacity_feasible = True

    recommended = choose_recommended_result(
        (
            Result("cheap_bad", 1.0, 2),
            Result("expensive_good", 100.0, 0),
        )
    )

    assert recommended.variant_name == "expensive_good"


def test_green_e2_adaptive_seed_keeps_green_specs_e2_feasible_and_unmixed():
    variant = load_problem_variant(".", SplitMode.GREEN_E2_ADAPTIVE)
    specs = construct_problem2_initial_route_specs(variant)
    lookup = {
        int(row["node_id"]): row
        for row in variant.data.service_nodes.to_dict(orient="records")
    }
    green_specs = [
        spec for spec in specs
        if any(bool(lookup[int(node_id)]["is_green_zone"]) for node_id in spec.service_node_ids)
    ]

    assert green_specs
    for spec in green_specs:
        rows = [lookup[int(node_id)] for node_id in spec.service_node_ids]
        assert all(bool(row["is_green_zone"]) for row in rows)
        assert spec.vehicle_type_id == "E2"
        assert sum(float(row["demand_weight"]) for row in rows) <= 1250.0 + 1e-9
        assert sum(float(row["demand_volume"]) for row in rows) <= 8.5 + 1e-9
