# -*- coding: utf-8 -*-
"""Adaptive large-neighborhood search for Problem 1."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from random import Random
from typing import Sequence

from .data_processing.loader import ProblemData
from .initial_solution import RouteSpec, construct_initial_route_specs, schedule_route_specs
from .metrics import SearchScoreWeights, score_solution, solution_quality_metrics
from .operators import DESTROY_OPERATORS, REPAIR_OPERATORS
from .solution import Solution


@dataclass(frozen=True)
class ALNSConfig:
    """Runtime configuration for a compact ALNS run."""

    iterations: int = 200
    remove_count: int = 8
    seed: int = 20260424
    initial_temperature: float = 5000.0
    cooling_rate: float = 0.995
    score_weights: SearchScoreWeights = field(default_factory=SearchScoreWeights)


@dataclass(frozen=True)
class ALNSIteration:
    """One recorded ALNS iteration."""

    iteration: int
    current_cost: float
    current_score: float
    best_cost: float
    best_score: float
    candidate_cost: float
    candidate_score: float
    candidate_late_stop_count: int
    candidate_max_late_min: float
    candidate_return_after_midnight_count: int
    accepted: bool
    destroy_operator: str
    repair_operator: str


@dataclass(frozen=True)
class ALNSResult:
    """ALNS output bundle."""

    initial_specs: tuple[RouteSpec, ...]
    best_specs: tuple[RouteSpec, ...]
    initial_solution: Solution
    best_solution: Solution
    history: tuple[ALNSIteration, ...]


def run_alns(
    problem: ProblemData,
    *,
    initial_specs: Sequence[RouteSpec] | None = None,
    config: ALNSConfig | None = None,
) -> ALNSResult:
    """Run a short ALNS optimization from an initial route-spec solution."""

    cfg = config or ALNSConfig()
    rng = Random(cfg.seed)
    initial_spec_tuple = tuple(initial_specs or construct_initial_route_specs(problem))
    initial_solution = schedule_route_specs(problem, initial_spec_tuple)
    initial_score = score_solution(initial_solution, cfg.score_weights)
    initial_quality = solution_quality_metrics(initial_solution)

    current_specs = initial_spec_tuple
    current_solution = initial_solution
    current_score = initial_score
    best_specs = current_specs
    best_solution = current_solution
    best_score = initial_score
    temperature = cfg.initial_temperature
    history: list[ALNSIteration] = [
        ALNSIteration(
            iteration=0,
            current_cost=current_solution.total_cost,
            current_score=current_score,
            best_cost=best_solution.total_cost,
            best_score=best_score,
            candidate_cost=current_solution.total_cost,
            candidate_score=current_score,
            candidate_late_stop_count=initial_quality.late_stop_count,
            candidate_max_late_min=initial_quality.max_late_min,
            candidate_return_after_midnight_count=initial_quality.return_after_midnight_count,
            accepted=True,
            destroy_operator="initial",
            repair_operator="initial",
        )
    ]

    destroy_names = tuple(DESTROY_OPERATORS)
    repair_names = tuple(REPAIR_OPERATORS)

    for iteration in range(1, cfg.iterations + 1):
        destroy_name = rng.choice(destroy_names)
        repair_name = rng.choice(repair_names)
        destroy = DESTROY_OPERATORS[destroy_name]
        repair = REPAIR_OPERATORS[repair_name]

        partial_specs, removed = destroy(problem, current_specs, current_solution, rng, cfg.remove_count)
        candidate_specs = repair(problem, partial_specs, removed)
        candidate_solution = schedule_route_specs(problem, candidate_specs)
        candidate_score = score_solution(candidate_solution, cfg.score_weights)
        candidate_quality = solution_quality_metrics(candidate_solution)

        accepted = _accept_candidate(
            current_score,
            candidate_score,
            temperature,
            rng,
        )
        if accepted:
            current_specs = candidate_specs
            current_solution = candidate_solution
            current_score = candidate_score

        if (
            candidate_score < best_score
            and candidate_solution.is_complete
            and candidate_solution.is_capacity_feasible
        ):
            best_specs = candidate_specs
            best_solution = candidate_solution
            best_score = candidate_score

        history.append(
            ALNSIteration(
                iteration=iteration,
                current_cost=current_solution.total_cost,
                current_score=current_score,
                best_cost=best_solution.total_cost,
                best_score=best_score,
                candidate_cost=candidate_solution.total_cost,
                candidate_score=candidate_score,
                candidate_late_stop_count=candidate_quality.late_stop_count,
                candidate_max_late_min=candidate_quality.max_late_min,
                candidate_return_after_midnight_count=candidate_quality.return_after_midnight_count,
                accepted=accepted,
                destroy_operator=destroy_name,
                repair_operator=repair_name,
            )
        )
        temperature *= cfg.cooling_rate

    return ALNSResult(
        initial_specs=initial_spec_tuple,
        best_specs=best_specs,
        initial_solution=initial_solution,
        best_solution=best_solution,
        history=tuple(history),
    )


def _accept_candidate(current_cost: float, candidate_cost: float, temperature: float, rng: Random) -> bool:
    if candidate_cost <= current_cost:
        return True
    if temperature <= 1e-9:
        return False
    probability = exp(-(candidate_cost - current_cost) / temperature)
    return rng.random() < probability
