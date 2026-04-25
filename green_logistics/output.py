# -*- coding: utf-8 -*-
"""Structured output and visualizations for Problem 1 solutions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import pandas as pd

from .data_processing.loader import ProblemData
from .metrics import solution_quality_metrics
from .solution import Route, Solution


def minutes_to_hhmm(minutes: float) -> str:
    """Format absolute minutes from 00:00 as HH:MM, with day offset if needed."""

    total = int(round(minutes))
    day, minute_of_day = divmod(total, 24 * 60)
    hour, minute = divmod(minute_of_day, 60)
    text = f"{hour:02d}:{minute:02d}"
    if day:
        return f"D+{day} {text}"
    return text


def solution_to_tables(solution: Solution) -> dict[str, pd.DataFrame]:
    """Convert a solution into paper-friendly DataFrames."""

    route_rows = [_route_row(index, route) for index, route in enumerate(solution.routes, start=1)]
    stop_rows = [
        _stop_row(route_index, route, stop_index, stop)
        for route_index, route in enumerate(solution.routes, start=1)
        for stop_index, stop in enumerate(route.stops, start=1)
    ]
    vehicle_types = sorted(
        set(solution.vehicle_trip_usage_by_type) | set(solution.vehicle_physical_usage_by_type)
    )
    vehicle_rows = [
        {
            "vehicle_type": vehicle_type_id,
            "physical_vehicle_count": solution.vehicle_physical_usage_by_type.get(vehicle_type_id, 0),
            "trip_count": solution.vehicle_trip_usage_by_type.get(vehicle_type_id, 0),
        }
        for vehicle_type_id in vehicle_types
    ]
    cost_rows = [
        {"component": "fixed_cost", "cost": solution.fixed_cost},
        {"component": "energy_cost", "cost": solution.energy_cost},
        {"component": "carbon_cost", "cost": solution.carbon_cost},
        {"component": "penalty_cost", "cost": solution.penalty_cost},
        {"component": "total_cost", "cost": solution.total_cost},
    ]
    quality = solution_quality_metrics(solution)
    quality_rows = [
        {"metric": key, "value": value}
        for key, value in quality.to_dict().items()
    ]
    return {
        "route_summary": pd.DataFrame(route_rows),
        "stop_schedule": pd.DataFrame(stop_rows),
        "vehicle_usage": pd.DataFrame(vehicle_rows),
        "cost_summary": pd.DataFrame(cost_rows),
        "quality_summary": pd.DataFrame(quality_rows),
    }


def write_solution_outputs(
    solution: Solution,
    output_dir: str | Path,
    *,
    problem: ProblemData | None = None,
    create_plots: bool = True,
) -> dict[str, Path]:
    """Write CSV/JSON summaries and optional PNG charts."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    tables = solution_to_tables(solution)
    written: dict[str, Path] = {}

    for table_name, table in tables.items():
        path = output_path / f"{table_name}.csv"
        table.to_csv(path, index=False, encoding="utf-8-sig")
        written[f"{table_name}_csv"] = path

    summary = {
        "route_count": len(solution.routes),
        "is_complete": solution.is_complete,
        "is_capacity_feasible": solution.is_capacity_feasible,
        "missing_node_ids": list(solution.missing_node_ids),
        "duplicate_node_ids": list(solution.duplicate_node_ids),
        "vehicle_trip_usage_by_type": solution.vehicle_trip_usage_by_type,
        "vehicle_physical_usage_by_type": solution.vehicle_physical_usage_by_type,
        "total_distance_km": solution.total_distance_km,
        "carbon_kg": solution.carbon_kg,
        "quality_metrics": solution_quality_metrics(solution).to_dict(),
        "cost_breakdown": {
            "fixed_cost": solution.fixed_cost,
            "energy_cost": solution.energy_cost,
            "carbon_cost": solution.carbon_cost,
            "penalty_cost": solution.penalty_cost,
            "total_cost": solution.total_cost,
        },
    }
    summary_path = output_path / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    written["summary_json"] = summary_path

    if create_plots:
        written.update(_write_plots(solution, tables, output_path, problem))

    return written


def write_problem2_comparison_outputs(rows: list[dict[str, object]], output_dir: str | Path) -> dict[str, Path]:
    """Write variant comparison artifacts for Problem 2."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    comparison = pd.DataFrame(rows)
    comparison_path = output_path / "variant_comparison.csv"
    comparison.to_csv(comparison_path, index=False, encoding="utf-8-sig")

    feasible = comparison[
        (comparison["policy_conflict_count"] == 0)
        & (comparison["is_complete"] == True)  # noqa: E712
        & (comparison["is_capacity_feasible"] == True)  # noqa: E712
    ]
    recommended = feasible.sort_values("total_cost").iloc[0].to_dict() if not feasible.empty else {}
    summary_lines = [
        "# Problem 2 Green-Zone Policy Summary",
        "",
        f"- Candidate variants: `{len(comparison)}`",
        f"- Feasible variants: `{len(feasible)}`",
        f"- Recommended variant: `{recommended.get('variant', 'none')}`",
        f"- Recommended total cost: `{recommended.get('total_cost', '')}`",
        "",
    ]
    summary_path = output_path / "policy_effect_summary.md"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    return {
        "variant_comparison_csv": comparison_path,
        "policy_effect_summary_md": summary_path,
    }


def _route_row(route_index: int, route: Route) -> dict[str, object]:
    return {
        "route_index": route_index,
        "trip_id": route.trip_id or f"T{route_index:04d}",
        "physical_vehicle_id": route.physical_vehicle_id or "",
        "vehicle_type": route.vehicle_type_id,
        "service_node_sequence": "->".join(str(node_id) for node_id in route.service_node_ids),
        "customer_sequence": "->".join(str(customer_id) for customer_id in route.customer_ids),
        "depart_min": route.depart_min,
        "depart_time": minutes_to_hhmm(route.depart_min),
        "return_min": route.return_min,
        "return_time": minutes_to_hhmm(route.return_min),
        "total_weight_kg": route.total_weight_kg,
        "total_volume_m3": route.total_volume_m3,
        "total_distance_km": route.total_distance_km,
        "fixed_cost": route.fixed_cost,
        "energy_cost": route.energy_cost,
        "carbon_cost": route.carbon_cost,
        "penalty_cost": route.penalty_cost,
        "total_cost": route.total_cost,
    }


def _stop_row(route_index: int, route: Route, stop_index: int, stop) -> dict[str, object]:
    return {
        "route_index": route_index,
        "trip_id": route.trip_id or f"T{route_index:04d}",
        "physical_vehicle_id": route.physical_vehicle_id or "",
        "vehicle_type": route.vehicle_type_id,
        "stop_index": stop_index,
        "service_node_id": stop.service_node_id,
        "customer_id": stop.customer_id,
        "earliest_min": stop.earliest_min,
        "latest_min": stop.latest_min,
        "arrival_min": stop.arrival_min,
        "arrival_time": minutes_to_hhmm(stop.arrival_min),
        "wait_min": stop.wait_min,
        "late_min": stop.late_min,
        "service_start_min": stop.service_start_min,
        "departure_min": stop.departure_min,
        "departure_time": minutes_to_hhmm(stop.departure_min),
        "load_before_service_kg": stop.load_before_service_kg,
        "load_after_service_kg": stop.load_after_service_kg,
        "penalty_cost": stop.penalty_cost,
    }


def _write_plots(
    solution: Solution,
    tables: Mapping[str, pd.DataFrame],
    output_path: Path,
    problem: ProblemData | None,
) -> dict[str, Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    written: dict[str, Path] = {}

    cost_path = output_path / "cost_breakdown.png"
    cost_df = tables["cost_summary"]
    cost_plot_df = cost_df[cost_df["component"] != "total_cost"]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(cost_plot_df["component"], cost_plot_df["cost"], color=["#4C78A8", "#F58518", "#54A24B", "#E45756"])
    ax.set_ylabel("Cost")
    ax.set_title("Problem 1 Cost Breakdown")
    fig.tight_layout()
    fig.savefig(cost_path, dpi=180)
    plt.close(fig)
    written["cost_breakdown_png"] = cost_path

    usage_path = output_path / "vehicle_usage.png"
    usage_df = tables["vehicle_usage"]
    fig, ax = plt.subplots(figsize=(7, 4))
    x = range(len(usage_df))
    ax.bar([value - 0.18 for value in x], usage_df["physical_vehicle_count"], width=0.36, label="vehicles")
    ax.bar([value + 0.18 for value in x], usage_df["trip_count"], width=0.36, label="trips")
    ax.set_xticks(list(x), usage_df["vehicle_type"])
    ax.set_ylabel("Count")
    ax.set_title("Vehicle Use by Type")
    ax.legend()
    fig.tight_layout()
    fig.savefig(usage_path, dpi=180)
    plt.close(fig)
    written["vehicle_usage_png"] = usage_path

    time_path = output_path / "time_windows.png"
    stop_df = tables["stop_schedule"].copy()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if not stop_df.empty:
        stop_df = stop_df.sort_values("arrival_min").reset_index(drop=True)
        x_values = range(1, len(stop_df) + 1)
        ax.scatter(x_values, stop_df["arrival_min"], s=12, label="arrival", color="#4C78A8")
        ax.scatter(x_values, stop_df["earliest_min"], s=8, label="earliest", color="#54A24B")
        ax.scatter(x_values, stop_df["latest_min"], s=8, label="latest", color="#E45756")
    ax.set_xlabel("Served stop ordered by arrival")
    ax.set_ylabel("Absolute minute")
    ax.set_title("Arrival Times vs Soft Time Windows")
    ax.legend()
    fig.tight_layout()
    fig.savefig(time_path, dpi=180)
    plt.close(fig)
    written["time_windows_png"] = time_path

    route_map_path = _write_route_map_if_possible(solution, problem, output_path, plt)
    if route_map_path is not None:
        written["route_map_png"] = route_map_path

    return written


def _write_route_map_if_possible(solution: Solution, problem: ProblemData | None, output_path: Path, plt) -> Path | None:
    if problem is None or problem.coordinates.empty:
        return None
    required_columns = {"node_id", "x_km", "y_km"}
    if not required_columns.issubset(problem.coordinates.columns):
        return None

    coords = problem.coordinates.set_index("node_id")
    route_map_path = output_path / "route_map.png"
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(coords["x_km"], coords["y_km"], s=12, color="#555555", alpha=0.6)
    depot = coords.loc[0]
    ax.scatter([depot["x_km"]], [depot["y_km"]], s=60, color="#E45756", label="depot")

    for route in solution.routes:
        path_customer_ids = [0, *route.customer_ids, 0]
        x_values = [float(coords.loc[customer_id, "x_km"]) for customer_id in path_customer_ids]
        y_values = [float(coords.loc[customer_id, "y_km"]) for customer_id in path_customer_ids]
        ax.plot(x_values, y_values, linewidth=0.7, alpha=0.35)

    ax.set_xlabel("x km")
    ax.set_ylabel("y km")
    ax.set_title("Route Map")
    ax.legend()
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    fig.savefig(route_map_path, dpi=180)
    plt.close(fig)
    return route_map_path
