# -*- coding: utf-8 -*-
"""Policy hooks for Problem 1/2 routing evaluations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .constants import DAY_START_MIN
from .data_processing.loader import ProblemData
from .solution import Route, StopRecord


class PolicyEvaluator(Protocol):
    """Interface for optional policy penalties and feasibility checks."""

    def route_penalty(self, problem: ProblemData, route: Route) -> float:
        """Return a policy penalty for an evaluated route."""

    def is_route_allowed(self, problem: ProblemData, route: Route) -> bool:
        """Return whether a route satisfies this policy."""

    def stop_penalty(self, problem: ProblemData, stop: StopRecord, vehicle_type_id: str) -> float:
        """Return a policy penalty for a stop and vehicle type."""


@dataclass(frozen=True)
class NoPolicyEvaluator:
    """Problem 1 policy: no green-zone restriction."""

    def route_penalty(self, _problem: ProblemData, _route: Route) -> float:
        return 0.0

    def is_route_allowed(self, _problem: ProblemData, _route: Route) -> bool:
        return True

    def stop_penalty(self, _problem: ProblemData, _stop: StopRecord, _vehicle_type_id: str) -> float:
        return 0.0


@dataclass(frozen=True)
class GreenZonePolicyEvaluator:
    """Problem 2 skeleton: fuel vehicles may not serve green-zone stops 08:00-16:00."""

    start_min: float = DAY_START_MIN
    end_min: float = 16 * 60
    violation_penalty: float = 1_000_000.0

    def route_penalty(self, problem: ProblemData, route: Route) -> float:
        return sum(
            self.stop_penalty(problem, stop, route.vehicle_type_id)
            for stop in route.stops
        )

    def is_route_allowed(self, problem: ProblemData, route: Route) -> bool:
        return self.route_penalty(problem, route) <= 1e-9

    def stop_penalty(self, problem: ProblemData, stop: StopRecord, vehicle_type_id: str) -> float:
        if not vehicle_type_id.startswith("F"):
            return 0.0
        node = problem.service_nodes.set_index("node_id").loc[int(stop.service_node_id)]
        if not bool(node["is_green_zone"]):
            return 0.0
        if self.start_min <= stop.arrival_min <= self.end_min:
            return self.violation_penalty
        return 0.0
