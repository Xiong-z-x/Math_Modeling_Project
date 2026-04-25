# -*- coding: utf-8 -*-
"""Run Problem 2: green-zone fuel restriction vehicle scheduling."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from green_logistics.diagnostics import write_problem_diagnostics
from green_logistics.output import write_problem2_comparison_outputs, write_solution_outputs
from green_logistics.problem2_engine import Problem2Engine, Problem2RunResult, choose_recommended_result
from green_logistics.problem_variants import SplitMode, load_problem_variant


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    engine = Problem2Engine(
        iterations=args.iterations,
        remove_count=args.remove_count,
        seed=args.seed,
        initial_temperature=args.initial_temperature,
        cooling_rate=args.cooling_rate,
        optimize_departure_grid_min=args.optimize_departure_grid_min,
        max_departure_delay_min=args.max_departure_delay_min,
        use_policy_operators=args.use_policy_operators,
        scenario_return_limit_min=args.scenario_return_limit_min,
    )
    variants = tuple(
        load_problem_variant(args.data_dir, mode)
        for mode in (SplitMode.DEFAULT, SplitMode.GREEN_E2_ADAPTIVE)
    )
    pairs = tuple((variant, engine.run_variant(variant)) for variant in variants)
    results = tuple(result for _variant, result in pairs)

    rows = []
    for variant, result in pairs:
        variant_dir = output_root / result.variant_name
        written = write_solution_outputs(result.solution, variant_dir, problem=variant.data)
        written.update(write_problem_diagnostics(variant.data, result.solution, variant_dir))
        history_path = variant_dir / "alns_history.csv"
        _history_frame(result).to_csv(history_path, index=False, encoding="utf-8-sig")
        written["alns_history_csv"] = history_path
        (variant_dir / "problem2_summary.md").write_text(
            _summary_markdown(result, written),
            encoding="utf-8",
        )
        rows.append(_result_row(result))

    comparison_written = write_problem2_comparison_outputs(rows, output_root)
    recommended = choose_recommended_result(results)
    recommendation = _recommendation_dict(recommended, comparison_written)
    recommendation_path = output_root / "recommendation.json"
    recommendation_path.write_text(json.dumps(recommendation, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(recommendation, ensure_ascii=False, indent=2))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=".", help="Directory containing official xlsx files.")
    parser.add_argument("--output-dir", default="outputs/problem2", help="Directory for Problem 2 outputs.")
    parser.add_argument("--iterations", type=int, default=40, help="ALNS iterations per variant.")
    parser.add_argument("--remove-count", type=int, default=8, help="Nodes removed per ALNS iteration.")
    parser.add_argument("--seed", type=int, default=20260424, help="Random seed.")
    parser.add_argument("--initial-temperature", type=float, default=5000.0)
    parser.add_argument("--cooling-rate", type=float, default=0.995)
    parser.add_argument("--optimize-departure-grid-min", type=int, default=None)
    parser.add_argument("--max-departure-delay-min", type=float, default=720.0)
    parser.add_argument("--scenario-return-limit-min", type=float, default=None)
    parser.add_argument("--use-policy-operators", action="store_true", help="Enable experimental Problem 2 destroy/repair operators.")
    return parser.parse_args(argv)


def _result_row(result: Problem2RunResult) -> dict[str, object]:
    return {
        "variant": result.variant_name,
        "service_node_count": result.service_node_count,
        "green_service_node_count": result.green_service_node_count,
        "total_cost": result.total_cost,
        "fixed_cost": result.solution.fixed_cost,
        "energy_cost": result.solution.energy_cost,
        "carbon_cost": result.solution.carbon_cost,
        "penalty_cost": result.solution.penalty_cost,
        "total_distance_km": result.solution.total_distance_km,
        "carbon_kg": result.solution.carbon_kg,
        "trip_count": len(result.solution.routes),
        "physical_vehicle_usage": json.dumps(result.solution.vehicle_physical_usage_by_type, ensure_ascii=False),
        "trip_usage": json.dumps(result.solution.vehicle_trip_usage_by_type, ensure_ascii=False),
        "policy_conflict_count": result.policy_conflict_count,
        "is_complete": result.is_complete,
        "is_capacity_feasible": result.is_capacity_feasible,
        "late_stop_count": result.quality_metrics["late_stop_count"],
        "max_late_min": result.quality_metrics["max_late_min"],
        "return_after_midnight_count": result.quality_metrics["return_after_midnight_count"],
    }


def _recommendation_dict(result: Problem2RunResult, comparison_written: dict[str, Path]) -> dict[str, object]:
    return {
        "recommended_variant": result.variant_name,
        "total_cost": result.total_cost,
        "policy_conflict_count": result.policy_conflict_count,
        "is_complete": result.is_complete,
        "is_capacity_feasible": result.is_capacity_feasible,
        "service_node_count": result.service_node_count,
        "green_service_node_count": result.green_service_node_count,
        "cost_breakdown": {
            "fixed_cost": result.solution.fixed_cost,
            "energy_cost": result.solution.energy_cost,
            "carbon_cost": result.solution.carbon_cost,
            "penalty_cost": result.solution.penalty_cost,
            "total_cost": result.solution.total_cost,
        },
        "quality_metrics": result.quality_metrics,
        "vehicle_physical_usage_by_type": result.solution.vehicle_physical_usage_by_type,
        "variant_comparison_csv": str(comparison_written["variant_comparison_csv"]),
        "policy_effect_summary_md": str(comparison_written["policy_effect_summary_md"]),
    }


def _history_frame(result: Problem2RunResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "iteration": item.iteration,
                "current_cost": item.current_cost,
                "current_score": item.current_score,
                "best_cost": item.best_cost,
                "best_score": item.best_score,
                "candidate_cost": item.candidate_cost,
                "candidate_score": item.candidate_score,
                "candidate_late_stop_count": item.candidate_late_stop_count,
                "candidate_max_late_min": item.candidate_max_late_min,
                "candidate_return_after_midnight_count": item.candidate_return_after_midnight_count,
                "accepted": item.accepted,
                "destroy_operator": item.destroy_operator,
                "repair_operator": item.repair_operator,
            }
            for item in result.alns_result.history
        ]
    )


def _summary_markdown(result: Problem2RunResult, written: dict[str, Path]) -> str:
    lines = [
        "# Problem 2 Variant Summary",
        "",
        f"- Variant: `{result.variant_name}`",
        f"- Service nodes: `{result.service_node_count}`",
        f"- Green service nodes: `{result.green_service_node_count}`",
        f"- Policy conflict count: `{result.policy_conflict_count}`",
        f"- Complete coverage: `{result.is_complete}`",
        f"- Capacity feasible: `{result.is_capacity_feasible}`",
        f"- Total cost: `{result.total_cost:.2f}`",
        f"- Fixed cost: `{result.solution.fixed_cost:.2f}`",
        f"- Energy cost: `{result.solution.energy_cost:.2f}`",
        f"- Carbon cost: `{result.solution.carbon_cost:.2f}`",
        f"- Time-window penalty: `{result.solution.penalty_cost:.2f}`",
        f"- Carbon kg: `{result.solution.carbon_kg:.2f}`",
        f"- Physical vehicle usage: `{result.solution.vehicle_physical_usage_by_type}`",
        f"- Quality metrics: `{result.quality_metrics}`",
        "",
        "## Files",
        "",
    ]
    lines.extend(f"- `{key}`: `{path}`" for key, path in sorted(written.items()))
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
