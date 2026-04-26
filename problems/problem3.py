# -*- coding: utf-8 -*-
"""Run Problem 3: dynamic event response and rolling-horizon repair."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from green_logistics.problem3_engine import (
    Problem3Engine,
    Problem3Scenario,
    build_default_problem3_scenarios,
    load_baseline_solution_from_outputs,
    write_problem3_comparison_outputs,
    write_problem3_scenario_outputs,
)
from green_logistics.problem_variants import SplitMode, load_problem_variant


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    variant = load_problem_variant(args.data_dir, SplitMode.DEFAULT)
    baseline = load_baseline_solution_from_outputs(variant.data, args.baseline_dir)
    scenarios = build_default_problem3_scenarios(variant.data, baseline)
    if args.no_green_policy:
        scenarios = tuple(_without_policy(scenario) for scenario in scenarios)
    if args.scenario:
        selected = set(args.scenario)
        scenarios = tuple(scenario for scenario in scenarios if scenario.name in selected)
        missing = sorted(selected - {scenario.name for scenario in scenarios})
        if missing:
            raise ValueError(f"unknown Problem 3 scenario(s): {missing}")

    engine = Problem3Engine(
        iterations=args.iterations,
        remove_count=args.remove_count,
        seed=args.seed,
        initial_temperature=args.initial_temperature,
        cooling_rate=args.cooling_rate,
        optimize_departure_grid_min=args.optimize_departure_grid_min,
        max_departure_delay_min=args.max_departure_delay_min,
        use_ev_reservation=args.use_ev_reservation,
        ev_reservation_penalty=args.ev_reservation_penalty,
    )

    results = []
    for scenario in scenarios:
        result = engine.run_scenario(variant.data, baseline, scenario)
        scenario_dir = output_root / scenario.name
        write_problem3_scenario_outputs(result, scenario_dir, create_plots=not args.no_plots)
        results.append(result)

    written = write_problem3_comparison_outputs(tuple(results), output_root)
    recommendation = json.loads(written["recommendation_json"].read_text(encoding="utf-8"))
    print(json.dumps(recommendation, ensure_ascii=False, indent=2))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=".", help="Directory containing official xlsx files.")
    parser.add_argument(
        "--baseline-dir",
        default="outputs/problem2/default_split",
        help="Directory containing route_summary.csv for the dynamic baseline.",
    )
    parser.add_argument("--output-dir", default="outputs/problem3", help="Directory for Problem 3 outputs.")
    parser.add_argument("--iterations", type=int, default=8, help="Light ALNS iterations per dynamic scenario.")
    parser.add_argument("--remove-count", type=int, default=4, help="Nodes removed per light ALNS iteration.")
    parser.add_argument("--seed", type=int, default=20260426)
    parser.add_argument("--initial-temperature", type=float, default=1500.0)
    parser.add_argument("--cooling-rate", type=float, default=0.99)
    parser.add_argument("--optimize-departure-grid-min", type=int, default=None)
    parser.add_argument("--max-departure-delay-min", type=float, default=720.0)
    parser.add_argument("--use-ev-reservation", action="store_true", default=True)
    parser.add_argument("--no-ev-reservation", dest="use_ev_reservation", action="store_false")
    parser.add_argument("--ev-reservation-penalty", type=float, default=250.0)
    parser.add_argument("--no-green-policy", action="store_true", help="Run scenarios without inheriting Problem 2 policy.")
    parser.add_argument("--no-plots", action="store_true", help="Skip PNG plots for faster smoke runs.")
    parser.add_argument(
        "--scenario",
        action="append",
        help="Scenario name to run. Repeat to select multiple. Defaults to all representative scenarios.",
    )
    return parser.parse_args(argv)


def _without_policy(scenario: Problem3Scenario) -> Problem3Scenario:
    return replace(scenario, inherit_green_policy=False)


if __name__ == "__main__":
    raise SystemExit(main())
