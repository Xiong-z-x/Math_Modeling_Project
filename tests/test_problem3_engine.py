# -*- coding: utf-8 -*-
"""Smoke tests for the Problem 3 dynamic-response engine."""

from __future__ import annotations

from pathlib import Path

from green_logistics.problem3_engine import (
    Problem3Engine,
    build_default_problem3_scenarios,
    load_baseline_solution_from_outputs,
)
from green_logistics.problem_variants import SplitMode, load_problem_variant


def test_problem3_engine_runs_cancel_scenario_from_problem2_baseline() -> None:
    variant = load_problem_variant(".", SplitMode.DEFAULT)
    baseline = load_baseline_solution_from_outputs(
        variant.data,
        Path("outputs/problem2/default_split"),
    )
    scenario = next(
        item for item in build_default_problem3_scenarios(variant.data, baseline)
        if item.event.event_type == "cancel"
    )
    engine = Problem3Engine(iterations=0, remove_count=2, seed=20260426)

    result = engine.run_scenario(variant.data, baseline, scenario)

    assert result.scenario.name == scenario.name
    assert result.solution.is_complete
    assert result.solution.is_capacity_feasible
    assert result.policy_conflict_count == 0
    assert result.validation["physical_time_chain_feasible"]
    assert not result.route_changes.empty
    assert "cancelled" in set(result.route_changes["change_type"])


def test_default_problem3_scenarios_cover_required_event_types() -> None:
    variant = load_problem_variant(".", SplitMode.DEFAULT)
    baseline = load_baseline_solution_from_outputs(
        variant.data,
        Path("outputs/problem2/default_split"),
    )

    scenarios = build_default_problem3_scenarios(variant.data, baseline)
    event_types = {scenario.event.event_type for scenario in scenarios}

    assert {"cancel", "new_order", "time_window_change", "address_change"}.issubset(event_types)
    assert len({scenario.name for scenario in scenarios}) == len(scenarios)
