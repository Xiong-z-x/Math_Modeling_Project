# -*- coding: utf-8 -*-
"""Adaptive large-neighborhood search for Problem 1."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from random import Random
from typing import Sequence

from .data_processing.loader import ProblemData
from .initial_solution import RouteSpec, construct_initial_route_specs
from .metrics import SearchScoreWeights, score_solution, solution_quality_metrics
from .operators import DESTROY_OPERATORS, REPAIR_OPERATORS
from .policies import NoPolicyEvaluator, PolicyEvaluator
from .scheduler import SchedulingConfig, schedule_route_specs
from .scheduler_local_search import rescue_late_routes
from .solution import Solution


DEFAULT_DESTROY_OPERATOR_NAMES = (
    "random_remove",
    "worst_cost_remove",
    "related_remove",
    "time_penalty_remove",
    "actual_late_remove",
    "late_suffix_remove",
    "midnight_route_remove",
    "late_route_split",
)
DEFAULT_REPAIR_OPERATOR_NAMES = (
    "greedy_insert",
    "regret2_insert",
    "time_oriented_insert",
)


@dataclass(frozen=True)
class ALNSConfig:
    """Runtime configuration for a compact ALNS run."""

    iterations: int = 200
    remove_count: int = 8
    seed: int = 20260424
    initial_temperature: float = 5000.0
    cooling_rate: float = 0.995
    score_weights: SearchScoreWeights = field(default_factory=SearchScoreWeights)
    scheduling_config: SchedulingConfig | None = None
    postprocess_late_routes: bool = True
    policy_evaluator: PolicyEvaluator = field(default_factory=NoPolicyEvaluator)
    destroy_operator_names: tuple[str, ...] = DEFAULT_DESTROY_OPERATOR_NAMES
    repair_operator_names: tuple[str, ...] = DEFAULT_REPAIR_OPERATOR_NAMES


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
    schedule_cfg = cfg.scheduling_config or SchedulingConfig(
        score_weights=cfg.score_weights,
        policy_evaluator=cfg.policy_evaluator,
    )
    rng = Random(cfg.seed)
    initial_spec_tuple = tuple(initial_specs or construct_initial_route_specs(problem))
    initial_solution = schedule_route_specs(problem, initial_spec_tuple, config=schedule_cfg)
    initial_score = _candidate_search_score(problem, initial_solution, cfg)
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

    destroy_names = cfg.destroy_operator_names
    repair_names = cfg.repair_operator_names

    for iteration in range(1, cfg.iterations + 1):
        destroy_name = rng.choice(destroy_names)
        repair_name = rng.choice(repair_names)
        destroy = DESTROY_OPERATORS[destroy_name]
        repair = REPAIR_OPERATORS[repair_name]

        partial_specs, removed = destroy(problem, current_specs, current_solution, rng, cfg.remove_count)
        candidate_specs = repair(problem, partial_specs, removed)
        candidate_solution = schedule_route_specs(problem, candidate_specs, config=schedule_cfg)
        candidate_score = _candidate_search_score(problem, candidate_solution, cfg)
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

        if _is_better_formal_solution(
            candidate_solution,
            best_solution,
            problem=problem,
            policy_evaluator=cfg.policy_evaluator,
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

    if cfg.postprocess_late_routes:
        rescued_specs, rescued_solution = rescue_late_routes(
            problem,
            best_specs,
            best_solution,
            config=schedule_cfg,
        )
        rescued_score = _candidate_search_score(problem, rescued_solution, cfg)
        if _is_better_formal_solution(
            rescued_solution,
            best_solution,
            problem=problem,
            policy_evaluator=cfg.policy_evaluator,
        ):
            best_specs = rescued_specs
            best_solution = rescued_solution
            best_score = rescued_score

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


def _candidate_search_score(problem: ProblemData, solution: Solution, cfg: ALNSConfig) -> float:
    return score_solution(solution, cfg.score_weights) + cfg.policy_evaluator.solution_penalty(problem, solution)


def _is_better_formal_solution(
    candidate: Solution,
    incumbent: Solution,
    *,
    problem: ProblemData | None = None,
    policy_evaluator: PolicyEvaluator | None = None,
) -> bool:
    """Return whether candidate is better for the official objective and policy gate."""

    if not candidate.is_complete or not candidate.is_capacity_feasible:
        return False
    if not incumbent.is_complete or not incumbent.is_capacity_feasible:
        return True
    if problem is not None and policy_evaluator is not None:
        candidate_policy_ok = policy_evaluator.solution_violation_count(problem, candidate) == 0
        incumbent_policy_ok = policy_evaluator.solution_violation_count(problem, incumbent) == 0
        if not candidate_policy_ok:
            return False
        if not incumbent_policy_ok:
            return True
    if candidate.total_cost < incumbent.total_cost - 1e-9:
        return True
    if abs(candidate.total_cost - incumbent.total_cost) <= 1e-9:
        candidate_late = sum(stop.late_min for route in candidate.routes for stop in route.stops)
        incumbent_late = sum(stop.late_min for route in incumbent.routes for stop in route.stops)
        return candidate_late < incumbent_late - 1e-9
    return False
