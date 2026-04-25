# -*- coding: utf-8 -*-
"""Service-quality metrics and search scoring for scheduled solutions."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass

from .solution import Route, Solution


@dataclass(frozen=True)
class SolutionQualityMetrics:
    """Aggregated service-quality diagnostics for one scheduled solution."""

    late_stop_count: int
    total_late_min: float
    max_late_min: float
    wait_stop_count: int
    total_wait_min: float
    max_wait_min: float
    return_after_17_count: int
    return_after_midnight_count: int
    max_return_min: float
    max_trips_per_physical_vehicle: int
    mean_trips_per_physical_vehicle: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True)
class SearchScoreWeights:
    """Weights used by the heuristic search score, not the official cost."""

    late_stop: float = 500.0
    total_late_min: float = 1.0
    max_late_min: float = 8.0
    midnight_route: float = 1_000_000.0
    after_17_route: float = 0.0


def solution_quality_metrics(solution: Solution) -> SolutionQualityMetrics:
    """Compute late/wait/return diagnostics from evaluated routes."""

    stops = [stop for route in solution.routes for stop in route.stops]
    late_values = [float(stop.late_min) for stop in stops]
    wait_values = [float(stop.wait_min) for stop in stops]
    return_values = [float(route.return_min) for route in solution.routes]
    trips_by_vehicle = Counter(
        route.physical_vehicle_id
        for route in solution.routes
        if route.physical_vehicle_id
    )

    return SolutionQualityMetrics(
        late_stop_count=sum(1 for value in late_values if value > 1e-9),
        total_late_min=sum(late_values),
        max_late_min=max(late_values, default=0.0),
        wait_stop_count=sum(1 for value in wait_values if value > 1e-9),
        total_wait_min=sum(wait_values),
        max_wait_min=max(wait_values, default=0.0),
        return_after_17_count=sum(1 for value in return_values if value > 17 * 60),
        return_after_midnight_count=sum(1 for value in return_values if value >= 24 * 60),
        max_return_min=max(return_values, default=0.0),
        max_trips_per_physical_vehicle=max(trips_by_vehicle.values(), default=0),
        mean_trips_per_physical_vehicle=(
            sum(trips_by_vehicle.values()) / len(trips_by_vehicle)
            if trips_by_vehicle
            else 0.0
        ),
    )


def route_quality_score(route: Route, weights: SearchScoreWeights | None = None) -> float:
    """Return service-quality search score for one evaluated route."""

    score_weights = weights or SearchScoreWeights()
    late_values = [float(stop.late_min) for stop in route.stops]
    late_stop_count = sum(1 for value in late_values if value > 1e-9)
    total_late = sum(late_values)
    max_late = max(late_values, default=0.0)
    return_after_midnight = 1 if route.return_min >= 24 * 60 else 0
    return_after_17 = 1 if route.return_min > 17 * 60 else 0
    return (
        route.total_cost
        + score_weights.late_stop * late_stop_count
        + score_weights.total_late_min * total_late
        + score_weights.max_late_min * max_late
        + score_weights.midnight_route * return_after_midnight
        + score_weights.after_17_route * return_after_17
    )


def score_solution(solution: Solution, weights: SearchScoreWeights | None = None) -> float:
    """Return heuristic search score while preserving official solution cost."""

    score_weights = weights or SearchScoreWeights()
    metrics = solution_quality_metrics(solution)
    return (
        solution.total_cost
        + score_weights.late_stop * metrics.late_stop_count
        + score_weights.total_late_min * metrics.total_late_min
        + score_weights.max_late_min * metrics.max_late_min
        + score_weights.midnight_route * metrics.return_after_midnight_count
        + score_weights.after_17_route * metrics.return_after_17_count
    )
