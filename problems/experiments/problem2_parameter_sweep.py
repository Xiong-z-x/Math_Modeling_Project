# -*- coding: utf-8 -*-
"""Run incremental Problem 2 parameter sweeps without overwriting formal output."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from green_logistics.problem2_engine import Problem2Engine
from green_logistics.problem_variants import SplitMode, load_problem_variant


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    iterations_values = _parse_int_list(args.iterations)
    remove_counts = _parse_int_list(args.remove_counts)
    seeds = _parse_int_list(args.seeds)
    variants = tuple(SplitMode(value) for value in args.variants.split(",") if value.strip())
    loaded_variants = {mode: load_problem_variant(args.data_dir, mode) for mode in variants}

    rows: list[dict[str, object]] = []
    summary_path = output_dir / "summary.csv"
    for iterations in iterations_values:
        for remove_count in remove_counts:
            for seed in seeds:
                engine = Problem2Engine(
                    iterations=iterations,
                    remove_count=remove_count,
                    seed=seed,
                    initial_temperature=args.initial_temperature,
                    cooling_rate=args.cooling_rate,
                    optimize_departure_grid_min=args.optimize_departure_grid_min,
                    max_departure_delay_min=args.max_departure_delay_min,
                    use_policy_operators=args.use_policy_operators,
                    use_ev_reservation=args.use_ev_reservation,
                    ev_reservation_penalty=args.ev_reservation_penalty,
                    scenario_return_limit_min=args.scenario_return_limit_min,
                )
                for mode, variant in loaded_variants.items():
                    row: dict[str, object] = {
                        "status": "started",
                        "variant": mode.value,
                        "iterations": iterations,
                        "remove_count": remove_count,
                        "seed": seed,
                        "use_policy_operators": args.use_policy_operators,
                        "use_ev_reservation": args.use_ev_reservation,
                        "ev_reservation_penalty": args.ev_reservation_penalty,
                    }
                    rows.append(row)
                    pd.DataFrame(rows).to_csv(summary_path, index=False, encoding="utf-8-sig")
                    start = time.perf_counter()
                    result = engine.run_variant(variant)
                    runtime = time.perf_counter() - start
                    rows[-1] = {
                        "status": "completed",
                        "variant": mode.value,
                        "iterations": iterations,
                        "remove_count": remove_count,
                        "seed": seed,
                        "use_policy_operators": args.use_policy_operators,
                        "use_ev_reservation": args.use_ev_reservation,
                        "ev_reservation_penalty": args.ev_reservation_penalty,
                        "runtime_seconds": runtime,
                        "total_cost": result.total_cost,
                        "fixed_cost": result.solution.fixed_cost,
                        "energy_cost": result.solution.energy_cost,
                        "carbon_cost": result.solution.carbon_cost,
                        "penalty_cost": result.solution.penalty_cost,
                        "policy_conflict_count": result.policy_conflict_count,
                        "is_complete": result.is_complete,
                        "is_capacity_feasible": result.is_capacity_feasible,
                        "late_stop_count": result.quality_metrics["late_stop_count"],
                        "total_late_min": result.quality_metrics["total_late_min"],
                        "max_late_min": result.quality_metrics["max_late_min"],
                        "return_after_midnight_count": result.quality_metrics["return_after_midnight_count"],
                        "physical_vehicle_usage": result.solution.vehicle_physical_usage_by_type,
                        "trip_usage": result.solution.vehicle_trip_usage_by_type,
                    }
                    pd.DataFrame(rows).to_csv(summary_path, index=False, encoding="utf-8-sig")
                    print(
                        f"variant={mode.value} iter={iterations} remove={remove_count} seed={seed} "
                        f"cost={result.total_cost:.2f} conflicts={result.policy_conflict_count} "
                        f"late={result.quality_metrics['late_stop_count']} "
                        f"max_late={result.quality_metrics['max_late_min']:.2f} "
                        f"runtime={runtime:.1f}s",
                        flush=True,
                    )

    if rows:
        frame = pd.DataFrame(rows)
        feasible = frame[
            (frame["policy_conflict_count"] == 0)
            & (frame["is_complete"] == True)  # noqa: E712
            & (frame["is_capacity_feasible"] == True)  # noqa: E712
        ]
        if not feasible.empty:
            feasible.sort_values(
                ["total_cost", "late_stop_count", "max_late_min"],
                ascending=[True, True, True],
            ).head(20).to_csv(output_dir / "best_feasible_by_cost.csv", index=False, encoding="utf-8-sig")
    print(f"wrote {summary_path}", flush=True)
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=".")
    parser.add_argument("--output-dir", default="outputs/problem2_experiments/parameter_sweep")
    parser.add_argument("--variants", default=SplitMode.DEFAULT.value)
    parser.add_argument("--iterations", default="40")
    parser.add_argument("--remove-counts", default="8,12,16,20")
    parser.add_argument("--seeds", default="20260427,20260430,20260431,20260432")
    parser.add_argument("--initial-temperature", type=float, default=5000.0)
    parser.add_argument("--cooling-rate", type=float, default=0.995)
    parser.add_argument("--optimize-departure-grid-min", type=int, default=None)
    parser.add_argument("--max-departure-delay-min", type=float, default=720.0)
    parser.add_argument("--scenario-return-limit-min", type=float, default=None)
    parser.add_argument("--use-policy-operators", action="store_true")
    parser.add_argument("--use-ev-reservation", action="store_true")
    parser.add_argument("--ev-reservation-penalty", type=float, default=0.0)
    return parser.parse_args(argv)


def _parse_int_list(value: str) -> list[int]:
    result = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not result:
        raise ValueError("expected at least one integer")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
