# -*- coding: utf-8 -*-
"""Run Problem 1: static green logistics vehicle scheduling."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from green_logistics.alns import ALNSConfig, run_alns
from green_logistics.data_processing import load_problem_data
from green_logistics.initial_solution import construct_initial_route_specs, schedule_route_specs
from green_logistics.metrics import solution_quality_metrics
from green_logistics.output import write_solution_outputs


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    problem = load_problem_data(data_dir)
    initial_specs = construct_initial_route_specs(problem)
    initial_solution = schedule_route_specs(problem, initial_specs)
    result = run_alns(
        problem,
        initial_specs=initial_specs,
        config=ALNSConfig(
            iterations=args.iterations,
            remove_count=args.remove_count,
            seed=args.seed,
            initial_temperature=args.initial_temperature,
            cooling_rate=args.cooling_rate,
        ),
    )
    solution = result.best_solution

    written = write_solution_outputs(solution, output_dir, problem=problem)
    history_path = output_dir / "alns_history.csv"
    pd.DataFrame(
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
            for item in result.history
        ]
    ).to_csv(history_path, index=False, encoding="utf-8-sig")
    written["alns_history_csv"] = history_path

    summary_path = output_dir / "problem1_summary.md"
    summary_path.write_text(_summary_markdown(initial_solution, solution, written), encoding="utf-8")

    print(_console_summary(initial_solution, solution, output_dir))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=".", help="Directory containing the official xlsx files.")
    parser.add_argument("--output-dir", default="outputs/problem1", help="Directory for Problem 1 outputs.")
    parser.add_argument("--iterations", type=int, default=40, help="ALNS iterations.")
    parser.add_argument("--remove-count", type=int, default=8, help="Nodes removed per ALNS iteration.")
    parser.add_argument("--seed", type=int, default=20260424, help="Random seed.")
    parser.add_argument("--initial-temperature", type=float, default=5000.0)
    parser.add_argument("--cooling-rate", type=float, default=0.995)
    return parser.parse_args(argv)


def _console_summary(initial_solution, solution, output_dir: Path) -> str:
    improvement = initial_solution.total_cost - solution.total_cost
    quality = solution_quality_metrics(solution)
    return "\n".join(
        [
            "Problem 1 completed",
            f"output_dir={output_dir}",
            f"initial_cost={initial_solution.total_cost:.2f}",
            f"best_cost={solution.total_cost:.2f}",
            f"improvement={improvement:.2f}",
            f"late_stop_count={quality.late_stop_count}",
            f"max_late_min={quality.max_late_min:.2f}",
            f"return_after_midnight_count={quality.return_after_midnight_count}",
            f"trips={len(solution.routes)}",
            f"physical_vehicle_usage={solution.vehicle_physical_usage_by_type}",
            f"distance_km={solution.total_distance_km:.2f}",
            f"carbon_kg={solution.carbon_kg:.2f}",
            f"complete={solution.is_complete}",
            f"capacity_feasible={solution.is_capacity_feasible}",
        ]
    )


def _summary_markdown(initial_solution, solution, written: dict[str, Path]) -> str:
    improvement = initial_solution.total_cost - solution.total_cost
    quality = solution_quality_metrics(solution)
    lines = [
        "# Problem 1 Static Scheduling Summary",
        "",
        "## Cost",
        "",
        f"- Initial total cost: `{initial_solution.total_cost:.2f}`",
        f"- Best total cost: `{solution.total_cost:.2f}`",
        f"- Improvement: `{improvement:.2f}`",
        f"- Fixed cost: `{solution.fixed_cost:.2f}`",
        f"- Energy cost: `{solution.energy_cost:.2f}`",
        f"- Carbon cost: `{solution.carbon_cost:.2f}`",
        f"- Time-window penalty: `{solution.penalty_cost:.2f}`",
        "",
        "## Service Quality",
        "",
        f"- Late stops: `{quality.late_stop_count}`",
        f"- Total late minutes: `{quality.total_late_min:.2f}`",
        f"- Max late minutes: `{quality.max_late_min:.2f}`",
        f"- Routes returning after midnight: `{quality.return_after_midnight_count}`",
        f"- Max return minute: `{quality.max_return_min:.2f}`",
        f"- Max trips per physical vehicle: `{quality.max_trips_per_physical_vehicle}`",
        "",
        "## Feasibility",
        "",
        f"- Complete service-node coverage: `{solution.is_complete}`",
        f"- Capacity feasible trips: `{solution.is_capacity_feasible}`",
        f"- Missing service nodes: `{list(solution.missing_node_ids)}`",
        f"- Duplicate service nodes: `{list(solution.duplicate_node_ids)}`",
        "",
        "## Operations",
        "",
        f"- Depot-to-depot trips: `{len(solution.routes)}`",
        f"- Physical vehicle usage: `{solution.vehicle_physical_usage_by_type}`",
        f"- Trip usage by type: `{solution.vehicle_trip_usage_by_type}`",
        f"- Total distance km: `{solution.total_distance_km:.2f}`",
        f"- Carbon kg: `{solution.carbon_kg:.2f}`",
        "",
        "## Modeling Note",
        "",
        "Routes in the code are depot-to-depot trips. Trips are assigned to physical vehicles sequentially, so fleet limits are checked against physical vehicles, not trip count. This is necessary because the current 148 virtual service nodes include more heavy nodes than the one-trip large-vehicle fleet can cover.",
        "",
        "## Files",
        "",
    ]
    lines.extend(f"- `{key}`: `{path}`" for key, path in sorted(written.items()))
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
