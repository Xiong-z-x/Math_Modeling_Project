# -*- coding: utf-8 -*-
"""Tests for the Problem 3 command-line entry point."""

from __future__ import annotations

import json

from problems.problem3 import main


def test_problem3_cli_writes_single_scenario_outputs(tmp_path) -> None:
    exit_code = main(
        [
            "--iterations",
            "0",
            "--remove-count",
            "2",
            "--scenario",
            "cancel_future_order_1030",
            "--output-dir",
            str(tmp_path),
            "--no-plots",
        ]
    )

    assert exit_code == 0
    recommendation_path = tmp_path / "recommendation.json"
    comparison_path = tmp_path / "scenario_comparison.csv"
    scenario_summary = tmp_path / "cancel_future_order_1030" / "summary.json"
    route_changes = tmp_path / "cancel_future_order_1030" / "route_changes.csv"

    assert recommendation_path.exists()
    assert comparison_path.exists()
    assert scenario_summary.exists()
    assert route_changes.exists()
    recommendation = json.loads(recommendation_path.read_text(encoding="utf-8"))
    assert recommendation["scenario_count"] == 1
    assert recommendation["feasible_scenario_count"] == 1
