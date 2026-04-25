# -*- coding: utf-8 -*-
"""Policy hooks for Problem 1/2 routing evaluations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .constants import DAY_START_MIN, VEHICLE_TYPES
from .data_processing.loader import ProblemData
from .solution import Route, Solution, StopRecord


_GREEN_NODE_CACHE: dict[int, set[int]] = {}


class PolicyEvaluator(Protocol):
    """Interface for optional policy penalties and feasibility checks."""

    def route_penalty(self, problem: ProblemData, route: Route) -> float:
        """Return a policy penalty for an evaluated route."""

    def is_route_allowed(self, problem: ProblemData, route: Route) -> bool:
        """Return whether a route satisfies this policy."""

    def stop_penalty(self, problem: ProblemData, stop: StopRecord, vehicle_type_id: str) -> float:
        """Return a policy penalty for a stop and vehicle type."""

    def solution_penalty(self, problem: ProblemData, solution: Solution) -> float:
        """Return a policy penalty for a whole solution."""

    def solution_violation_count(self, problem: ProblemData, solution: Solution) -> int:
        """Return the number of hard policy violations in a solution."""


@dataclass(frozen=True)
class NoPolicyEvaluator:
    """Problem 1 policy: no green-zone restriction."""

    def route_penalty(self, _problem: ProblemData, _route: Route) -> float:
        return 0.0

    def is_route_allowed(self, _problem: ProblemData, _route: Route) -> bool:
        return True

    def stop_penalty(self, _problem: ProblemData, _stop: StopRecord, _vehicle_type_id: str) -> float:
        return 0.0

    def solution_penalty(self, _problem: ProblemData, _solution: Solution) -> float:
        return 0.0

    def solution_violation_count(self, _problem: ProblemData, _solution: Solution) -> int:
        return 0


@dataclass(frozen=True)
class GreenZonePolicyEvaluator:
    """Problem 2 skeleton: fuel vehicles may not serve green-zone stops 08:00-16:00."""

    start_min: float = DAY_START_MIN
    end_min: float = 16 * 60
    violation_penalty: float = 1_000_000.0

    def route_penalty(self, problem: ProblemData, route: Route) -> float:
        return self.route_violation_count(problem, route) * self.violation_penalty

    def is_route_allowed(self, problem: ProblemData, route: Route) -> bool:
        return self.route_violation_count(problem, route) == 0

    def stop_violation(self, problem: ProblemData, stop: StopRecord, vehicle_type_id: str) -> bool:
        vehicle = VEHICLE_TYPES[vehicle_type_id]
        if vehicle.energy_type != "fuel":
            return False
        if int(stop.service_node_id) not in _green_node_ids(problem):
            return False
        return self.start_min <= float(stop.arrival_min) < self.end_min

    def stop_penalty(self, problem: ProblemData, stop: StopRecord, vehicle_type_id: str) -> float:
        return self.violation_penalty if self.stop_violation(problem, stop, vehicle_type_id) else 0.0

    def violating_stops(self, problem: ProblemData, route: Route) -> tuple[StopRecord, ...]:
        if route.vehicle_type.energy_type != "fuel":
            return ()
        green_nodes = _green_node_ids(problem)
        return tuple(
            stop for stop in route.stops
            if int(stop.service_node_id) in green_nodes
            and self.start_min <= float(stop.arrival_min) < self.end_min
        )

    def route_violation_count(self, problem: ProblemData, route: Route) -> int:
        return len(self.violating_stops(problem, route))

    def solution_penalty(self, problem: ProblemData, solution: Solution) -> float:
        return sum(self.route_penalty(problem, route) for route in solution.routes)

    def solution_violation_count(self, problem: ProblemData, solution: Solution) -> int:
        return sum(self.route_violation_count(problem, route) for route in solution.routes)


def _green_node_ids(problem: ProblemData) -> set[int]:
    cache_key = id(problem.service_nodes)
    cached = _GREEN_NODE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    green = set(
        problem.service_nodes.loc[
            problem.service_nodes["is_green_zone"], "node_id"
        ].astype(int).tolist()
    )
    _GREEN_NODE_CACHE[cache_key] = green
    return green
