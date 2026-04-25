# -*- coding: utf-8 -*-
"""Tests for structured solution exports."""

from __future__ import annotations

import json

from green_logistics.initial_solution import RouteSpec, schedule_route_specs
from green_logistics.output import write_problem2_comparison_outputs, write_solution_outputs
from tests.test_solution import _small_problem_data


def test_write_solution_outputs_creates_tables_and_plots(tmp_path) -> None:
    problem = _small_problem_data()
    solution = schedule_route_specs(problem, (RouteSpec("F1", (10, 20)),), vehicle_counts={"F1": 1})

    written = write_solution_outputs(solution, tmp_path, problem=problem)

    expected = {
        "route_summary_csv",
        "stop_schedule_csv",
        "cost_summary_csv",
        "quality_summary_csv",
        "vehicle_usage_csv",
        "summary_json",
        "cost_breakdown_png",
        "vehicle_usage_png",
        "time_windows_png",
    }
    assert expected.issubset(written.keys())
    for key in expected:
        assert written[key].exists()
        assert written[key].stat().st_size > 0

    summary = json.loads(written["summary_json"].read_text(encoding="utf-8"))
    assert "quality_metrics" in summary
    assert "late_stop_count" in summary["quality_metrics"]
    assert "max_late_min" in summary["quality_metrics"]
    assert "return_after_midnight_count" in summary["quality_metrics"]


def test_write_problem2_comparison_outputs(tmp_path) -> None:
    rows = [
        {
            "variant": "default_split",
            "total_cost": 10.0,
            "policy_conflict_count": 0,
            "is_complete": True,
            "is_capacity_feasible": True,
        },
        {
            "variant": "green_e2_adaptive",
            "total_cost": 9.0,
            "policy_conflict_count": 0,
            "is_complete": True,
            "is_capacity_feasible": True,
        },
    ]

    written = write_problem2_comparison_outputs(rows, tmp_path)

    assert written["variant_comparison_csv"].exists()
    assert written["policy_effect_summary_md"].exists()
    summary_text = written["policy_effect_summary_md"].read_text(encoding="utf-8")
    assert summary_text.startswith("# Problem 2")
    assert "green_e2_adaptive" in summary_text
