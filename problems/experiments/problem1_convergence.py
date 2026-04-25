# -*- coding: utf-8 -*-
"""Run multi-seed convergence experiments for Problem 1."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from green_logistics.alns import ALNSConfig, run_alns
from green_logistics.data_processing import load_problem_data
from green_logistics.initial_solution import construct_initial_route_specs
from green_logistics.metrics import score_solution, solution_quality_metrics
from green_logistics.scheduler import SchedulingConfig


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    iterations = _parse_int_list(args.iterations)
    seeds = _parse_int_list(args.seeds)
    problem = load_problem_data(data_dir)
    initial_specs = construct_initial_route_specs(problem)
    scheduling_config = SchedulingConfig(
        forbid_midnight=args.forbid_midnight,
        scenario_return_limit_min=args.scenario_return_limit_min,
        reload_time_min=args.reload_time_min,
        optimize_departure_grid_min=args.optimize_departure_grid_min,
        max_departure_delay_min=args.max_departure_delay_min,
    )

    rows: list[dict[str, object]] = []
    for iteration_count in iterations:
        for seed in seeds:
            start = time.perf_counter()
            result = run_alns(
                problem,
                initial_specs=initial_specs,
                config=ALNSConfig(
                    iterations=iteration_count,
                    remove_count=args.remove_count,
                    seed=seed,
                    initial_temperature=args.initial_temperature,
                    cooling_rate=args.cooling_rate,
                    scheduling_config=scheduling_config,
                ),
            )
            runtime = time.perf_counter() - start
            solution = result.best_solution
            quality = solution_quality_metrics(solution)
            rows.append(
                {
                    "iterations": iteration_count,
                    "seed": seed,
                    "runtime_seconds": runtime,
                    "total_cost": solution.total_cost,
                    "search_score": score_solution(solution),
                    "late_stop_count": quality.late_stop_count,
                    "total_late_min": quality.total_late_min,
                    "max_late_min": quality.max_late_min,
                    "return_after_midnight_count": quality.return_after_midnight_count,
                    "return_after_17_count": quality.return_after_17_count,
                    "fixed_cost": solution.fixed_cost,
                    "energy_cost": solution.energy_cost,
                    "carbon_cost": solution.carbon_cost,
                    "penalty_cost": solution.penalty_cost,
                    "route_count": len(solution.routes),
                    "physical_vehicle_count": sum(solution.vehicle_physical_usage_by_type.values()),
                    "vehicle_physical_usage": solution.vehicle_physical_usage_by_type,
                    "complete": solution.is_complete,
                    "capacity_feasible": solution.is_capacity_feasible,
                }
            )
            print(
                f"iterations={iteration_count} seed={seed} "
                f"cost={solution.total_cost:.2f} late={quality.late_stop_count} "
                f"max_late={quality.max_late_min:.2f} runtime={runtime:.1f}s"
            )

    summary = pd.DataFrame(rows)
    summary_path = output_dir / "summary.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    if not summary.empty:
        summary.sort_values(
            ["search_score", "late_stop_count", "max_late_min", "total_cost"],
            ascending=[True, True, True, True],
        ).head(20).to_csv(output_dir / "best_by_score.csv", index=False, encoding="utf-8-sig")
        summary.sort_values(
            ["total_cost", "late_stop_count", "max_late_min"],
            ascending=[True, True, True],
        ).head(20).to_csv(output_dir / "best_by_true_cost.csv", index=False, encoding="utf-8-sig")

    print(f"wrote {summary_path}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=".")
    parser.add_argument("--output-dir", default="outputs/experiments/problem1_convergence")
    parser.add_argument("--iterations", default="40,100,200,500")
    parser.add_argument("--seeds", default="20260424,20260425,20260426,20260427,20260428")
    parser.add_argument("--remove-count", type=int, default=8)
    parser.add_argument("--initial-temperature", type=float, default=5000.0)
    parser.add_argument("--cooling-rate", type=float, default=0.995)
    parser.add_argument("--forbid-midnight", action="store_true")
    parser.add_argument("--scenario-return-limit-min", type=float, default=None)
    parser.add_argument("--reload-time-min", type=float, default=0.0)
    parser.add_argument("--optimize-departure-grid-min", type=int, default=None)
    parser.add_argument("--max-departure-delay-min", type=float, default=180.0)
    return parser.parse_args(argv)


def _parse_int_list(value: str) -> list[int]:
    result = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not result:
        raise ValueError("expected at least one integer")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
