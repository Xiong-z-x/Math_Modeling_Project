# Problem2Engine With GREEN_E2_ADAPTIVE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independent Problem 2 solver that treats the green-zone fuel restriction as a hard feasibility gate, runs both `DEFAULT_SPLIT` and `GREEN_E2_ADAPTIVE` as formal candidate mainlines, and recommends the feasible lowest official-cost solution.

**Architecture:** Add a data-variant layer without changing default `load_problem_data`, then wire policy-aware scheduling, ALNS selection, diagnostics, and output through a new `Problem2Engine`. The first deliverable is a correct, reproducible MVP; policy-specific operators and scenario experiments come after the hard-feasibility pipeline is proven.

**Tech Stack:** Python 3, pandas, pytest, current `green_logistics` modules (`ProblemData`, `RouteSpec`, `Solution`, `SchedulingConfig`, ALNS), CSV/JSON/Markdown outputs.

---

## File Map

- Create `green_logistics/problem_variants.py`: explicit service-node split variants, including `DEFAULT_SPLIT` and `GREEN_E2_ADAPTIVE`.
- Create `tests/test_problem_variants.py`: proves default data is unchanged and adaptive green split preserves demand while increasing E2-feasible green nodes.
- Modify `green_logistics/policies.py`: make Problem 2 policy a hard, countable feasibility evaluator with `[480, 960)` boundary.
- Create `tests/test_problem2_policy.py`: exact policy boundary tests and route/solution violation-count tests.
- Modify `green_logistics/scheduler.py`: add optional policy-aware departure candidates so fuel trips touching green nodes can be delayed until legal service.
- Modify `green_logistics/alns.py`: accept a policy evaluator; final best for Problem 2 must be complete, capacity-feasible, and policy-feasible before comparing official total cost.
- Create `green_logistics/problem2_engine.py`: orchestrates one Problem 2 variant run and returns structured run metadata.
- Create `tests/test_problem2_engine.py`: small integration tests around variant execution, recommendation filtering, and zero-conflict requirement.
- Create `problems/problem2.py`: command-line runner that runs both candidate mainlines and writes `outputs/problem2/default_split/`, `outputs/problem2/green_e2_adaptive/`, and `outputs/problem2/recommendation.json`.
- Modify `green_logistics/output.py`: add Problem 2 comparison output writer.
- Create `docs/results/problem2_green_zone_policy_summary.md` after a real run.
- Update `README.md`, `项目文件导航.md`, `task_plan.md`, `findings.md`, and `progress.md` after implementation.

## Task 1: Data Variant Layer

**Files:**
- Create: `green_logistics/problem_variants.py`
- Create: `tests/test_problem_variants.py`
- Reference: `green_logistics/data_processing/loader.py`

- [ ] **Step 1: Write the failing variant tests**

Create `tests/test_problem_variants.py`:

```python
# -*- coding: utf-8 -*-

from collections import Counter

import pytest

from green_logistics.constants import VEHICLE_TYPES
from green_logistics.data_processing import load_problem_data
from green_logistics.problem_variants import SplitMode, load_problem_variant


def _split_counts(problem):
    rows = problem.customer_demands[["customer_id", "split_count"]].itertuples(index=False)
    return {int(row.customer_id): int(row.split_count) for row in rows}


def test_default_variant_matches_current_loader():
    direct = load_problem_data(".")
    variant = load_problem_variant(".", SplitMode.DEFAULT)

    assert variant.name == "default_split"
    assert len(variant.data.service_nodes) == 148
    assert variant.data.service_nodes.equals(direct.service_nodes)
    assert variant.data.node_to_customer == direct.node_to_customer


def test_green_e2_adaptive_preserves_total_demand_and_non_green_splits():
    default = load_problem_variant(".", SplitMode.DEFAULT)
    adaptive = load_problem_variant(".", SplitMode.GREEN_E2_ADAPTIVE)

    assert adaptive.name == "green_e2_adaptive"
    assert len(adaptive.data.service_nodes) == 166
    assert int(adaptive.data.service_nodes["is_green_zone"].sum()) == 37

    assert adaptive.data.service_nodes["demand_weight"].sum() == pytest.approx(
        default.data.service_nodes["demand_weight"].sum()
    )
    assert adaptive.data.service_nodes["demand_volume"].sum() == pytest.approx(
        default.data.service_nodes["demand_volume"].sum()
    )
    assert adaptive.data.active_green_customer_ids == default.data.active_green_customer_ids
    assert adaptive.data.green_customer_ids == default.data.green_customer_ids

    default_counts = _split_counts(default.data)
    adaptive_counts = _split_counts(adaptive.data)
    green_customers = set(default.data.active_green_customer_ids)
    for customer_id, split_count in default_counts.items():
        if customer_id not in green_customers:
            assert adaptive_counts[customer_id] == split_count


def test_green_e2_adaptive_green_nodes_fit_e2_capacity():
    adaptive = load_problem_variant(".", SplitMode.GREEN_E2_ADAPTIVE)
    e2 = VEHICLE_TYPES["E2"]
    green_nodes = adaptive.data.service_nodes[adaptive.data.service_nodes["is_green_zone"]]

    assert not green_nodes.empty
    assert (green_nodes["demand_weight"] <= e2.max_weight_kg + 1e-9).all()
    assert (green_nodes["demand_volume"] <= e2.max_volume_m3 + 1e-9).all()


def test_green_e2_adaptive_node_mapping_is_complete_and_unique():
    adaptive = load_problem_variant(".", SplitMode.GREEN_E2_ADAPTIVE)
    node_ids = adaptive.data.service_nodes["node_id"].astype(int).tolist()

    assert node_ids == list(range(1, len(node_ids) + 1))
    assert set(adaptive.data.node_to_customer) == set(node_ids)
    mapped_customers = Counter(adaptive.data.node_to_customer.values())
    demand_counts = _split_counts(adaptive.data)
    assert mapped_customers == Counter(demand_counts)
```

- [ ] **Step 2: Run tests to verify the expected red state**

Run:

```powershell
pytest tests/test_problem_variants.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'green_logistics.problem_variants'`.

- [ ] **Step 3: Implement `problem_variants.py`**

Create `green_logistics/problem_variants.py`:

```python
# -*- coding: utf-8 -*-
"""Problem-specific data variants for green logistics scheduling."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

import numpy as np

from .constants import VEHICLE_TYPES
from .data_processing import load_problem_data
from .data_processing.loader import ProblemData, _build_service_nodes


class SplitMode(str, Enum):
    """Supported service-node split modes."""

    DEFAULT = "default_split"
    GREEN_E2_ADAPTIVE = "green_e2_adaptive"


@dataclass(frozen=True)
class ProblemVariant:
    """A loaded data variant plus audit metadata."""

    name: str
    split_mode: SplitMode
    data: ProblemData
    default_service_node_count: int
    service_node_count: int
    green_service_node_count: int
    notes: tuple[str, ...]


def load_problem_variant(data_dir: str | Path = ".", split_mode: SplitMode | str = SplitMode.DEFAULT) -> ProblemVariant:
    """Load official data under an explicit service-node split mode."""

    mode = SplitMode(split_mode)
    base = load_problem_data(data_dir)
    if mode is SplitMode.DEFAULT:
        return ProblemVariant(
            name=mode.value,
            split_mode=mode,
            data=base,
            default_service_node_count=len(base.service_nodes),
            service_node_count=len(base.service_nodes),
            green_service_node_count=int(base.service_nodes["is_green_zone"].sum()),
            notes=("Matches load_problem_data exactly.",),
        )

    e2 = VEHICLE_TYPES["E2"]
    demands = base.customer_demands.copy()
    green_mask = demands["is_green_zone"].astype(bool)
    green_ratio = np.maximum(
        demands.loc[green_mask, "total_weight"].astype(float) / e2.max_weight_kg,
        demands.loc[green_mask, "total_volume"].astype(float) / e2.max_volume_m3,
    )
    demands.loc[green_mask, "split_count"] = np.ceil(green_ratio).astype(int).clip(lower=1)
    demands["split_count"] = demands["split_count"].astype(int)

    service_nodes, node_to_customer = _build_service_nodes(demands)
    data = replace(
        base,
        customer_demands=demands.reset_index(drop=True),
        service_nodes=service_nodes,
        node_to_customer=node_to_customer,
    )
    return ProblemVariant(
        name=mode.value,
        split_mode=mode,
        data=data,
        default_service_node_count=len(base.service_nodes),
        service_node_count=len(service_nodes),
        green_service_node_count=int(service_nodes["is_green_zone"].sum()),
        notes=(
            "Non-green customer split counts match default.",
            "Green customers are split by E2 capacity for Problem 2 candidate routing.",
        ),
    )
```

- [ ] **Step 4: Verify variant tests pass**

Run:

```powershell
pytest tests/test_problem_variants.py -q
```

Expected: `4 passed`.

## Task 2: Hard Policy Evaluator

**Files:**
- Modify: `green_logistics/policies.py`
- Create: `tests/test_problem2_policy.py`
- Keep: `tests/test_policies.py`

- [ ] **Step 1: Write policy boundary tests**

Create `tests/test_problem2_policy.py`:

```python
# -*- coding: utf-8 -*-

from dataclasses import replace

from green_logistics.data_processing import load_problem_data
from green_logistics.policies import GreenZonePolicyEvaluator
from green_logistics.solution import StopRecord, evaluate_route


def _stop(node_id: int, customer_id: int, arrival_min: float) -> StopRecord:
    return StopRecord(
        service_node_id=node_id,
        customer_id=customer_id,
        earliest_min=0.0,
        latest_min=2000.0,
        arrival_min=arrival_min,
        wait_min=0.0,
        late_min=0.0,
        service_start_min=arrival_min,
        departure_min=arrival_min + 20.0,
        demand_weight_kg=1.0,
        demand_volume_m3=1.0,
        load_before_service_kg=1.0,
        load_before_service_m3=1.0,
        load_after_service_kg=0.0,
        load_after_service_m3=0.0,
        penalty_cost=0.0,
    )


def _green_node(problem):
    row = problem.service_nodes[problem.service_nodes["is_green_zone"]].iloc[0]
    return int(row["node_id"]), int(row["customer_id"])


def _non_green_node(problem):
    row = problem.service_nodes[~problem.service_nodes["is_green_zone"]].iloc[0]
    return int(row["node_id"]), int(row["customer_id"])


def test_fuel_green_stop_restricted_window_is_violation():
    problem = load_problem_data(".")
    node_id, customer_id = _green_node(problem)
    policy = GreenZonePolicyEvaluator()

    assert policy.stop_violation(problem, _stop(node_id, customer_id, 480.0), "F1")
    assert policy.stop_violation(problem, _stop(node_id, customer_id, 959.9), "F1")
    assert not policy.stop_violation(problem, _stop(node_id, customer_id, 960.0), "F1")


def test_ev_and_non_green_stops_are_allowed():
    problem = load_problem_data(".")
    green_node_id, green_customer_id = _green_node(problem)
    non_green_node_id, non_green_customer_id = _non_green_node(problem)
    policy = GreenZonePolicyEvaluator()

    assert not policy.stop_violation(problem, _stop(green_node_id, green_customer_id, 600.0), "E1")
    assert not policy.stop_violation(problem, _stop(green_node_id, green_customer_id, 600.0), "E2")
    assert not policy.stop_violation(problem, _stop(non_green_node_id, non_green_customer_id, 600.0), "F1")


def test_route_and_solution_violation_counts_use_actual_arrival_times():
    from green_logistics.solution import evaluate_solution

    problem = load_problem_data(".")
    green_node_id, green_customer_id = _green_node(problem)
    route = evaluate_route(problem, "F1", (green_node_id,), depart_min=480.0)
    violating_stop = replace(route.stops[0], arrival_min=600.0, customer_id=green_customer_id)
    legal_stop = replace(route.stops[0], arrival_min=960.0, customer_id=green_customer_id)
    policy = GreenZonePolicyEvaluator()

    violating_route = replace(route, stops=(violating_stop,))
    legal_route = replace(route, stops=(legal_stop,))
    solution = evaluate_solution((violating_route, legal_route), required_node_ids=[green_node_id])

    assert policy.route_violation_count(problem, violating_route) == 1
    assert policy.route_violation_count(problem, legal_route) == 0
    assert policy.solution_violation_count(problem, solution) == 1
```

- [ ] **Step 2: Run policy tests to verify the expected red state**

Run:

```powershell
pytest tests/test_problem2_policy.py tests/test_policies.py -q
```

Expected: FAIL because `stop_violation`, `route_violation_count`, and `solution_violation_count` are missing, and the current end boundary treats `960` as restricted.

- [ ] **Step 3: Implement policy helpers**

Modify `green_logistics/policies.py` so `GreenZonePolicyEvaluator` contains these methods and uses vehicle `energy_type`:

```python
from .constants import DAY_START_MIN, VEHICLE_TYPES
from .solution import Route, Solution, StopRecord


def stop_violation(self, problem: ProblemData, stop: StopRecord, vehicle_type_id: str) -> bool:
    vehicle = VEHICLE_TYPES[vehicle_type_id]
    if vehicle.energy_type != "fuel":
        return False
    node = problem.service_nodes.set_index("node_id").loc[int(stop.service_node_id)]
    if not bool(node["is_green_zone"]):
        return False
    return self.start_min <= float(stop.arrival_min) < self.end_min


def stop_penalty(self, problem: ProblemData, stop: StopRecord, vehicle_type_id: str) -> float:
    return self.violation_penalty if self.stop_violation(problem, stop, vehicle_type_id) else 0.0


def violating_stops(self, problem: ProblemData, route: Route) -> tuple[StopRecord, ...]:
    return tuple(
        stop for stop in route.stops
        if self.stop_violation(problem, stop, route.vehicle_type_id)
    )


def route_violation_count(self, problem: ProblemData, route: Route) -> int:
    return len(self.violating_stops(problem, route))


def solution_violation_count(self, problem: ProblemData, solution: Solution) -> int:
    return sum(self.route_violation_count(problem, route) for route in solution.routes)


def solution_penalty(self, problem: ProblemData, solution: Solution) -> float:
    return sum(self.route_penalty(problem, route) for route in solution.routes)
```

Also add no-op `solution_violation_count` and `solution_penalty` to `NoPolicyEvaluator` so callers do not need special branches.

- [ ] **Step 4: Verify policy tests pass**

Run:

```powershell
pytest tests/test_problem2_policy.py tests/test_policies.py -q
```

Expected: all policy tests pass.

## Task 3: Policy-Aware Scheduling And ALNS Feasibility Gate

**Files:**
- Modify: `green_logistics/scheduler.py`
- Modify: `green_logistics/alns.py`
- Modify: `tests/test_scheduler.py`
- Modify: `tests/test_alns_smoke.py`

- [ ] **Step 1: Add focused scheduler tests**

Extend `tests/test_scheduler.py` with a real-data test that forces a fuel trip to a green stop and verifies policy-aware departure avoids the restricted window:

```python
from green_logistics.data_processing import load_problem_data
from green_logistics.initial_solution import RouteSpec
from green_logistics.policies import GreenZonePolicyEvaluator
from green_logistics.scheduler import SchedulingConfig, schedule_route_specs


def test_policy_scheduler_can_delay_fuel_green_trip_until_restriction_end():
    problem = load_problem_data(".")
    green_node_id = int(problem.service_nodes[problem.service_nodes["is_green_zone"]].iloc[0]["node_id"])
    spec = RouteSpec(vehicle_type_id="F1", service_node_ids=(green_node_id,))
    policy = GreenZonePolicyEvaluator()
    solution = schedule_route_specs(
        problem,
        (spec,),
        config=SchedulingConfig(policy_evaluator=policy, max_departure_delay_min=720.0),
    )

    assert policy.solution_violation_count(problem, solution) == 0
    assert solution.routes[0].stops[0].arrival_min >= 960.0
```

- [ ] **Step 2: Add ALNS best-selection test**

Extend `tests/test_alns_smoke.py` with a unit-level test around `_is_better_formal_solution`:

```python
from dataclasses import replace

from green_logistics.alns import _is_better_formal_solution
from green_logistics.data_processing import load_problem_data
from green_logistics.policies import GreenZonePolicyEvaluator
from green_logistics.solution import evaluate_route, evaluate_solution


def test_problem2_best_selection_rejects_lower_cost_policy_violation():
    problem = load_problem_data(".")
    green_node_id = int(problem.service_nodes[problem.service_nodes["is_green_zone"]].iloc[0]["node_id"])
    policy = GreenZonePolicyEvaluator()

    illegal_route = evaluate_route(problem, "F1", (green_node_id,), depart_min=480.0, fixed_cost=0.0)
    illegal_solution = evaluate_solution((illegal_route,), required_node_ids=[green_node_id])

    legal_route = evaluate_route(problem, "E1", (green_node_id,), depart_min=480.0, fixed_cost=400.0)
    legal_solution = evaluate_solution((legal_route,), required_node_ids=[green_node_id])

    cheap_illegal = replace(illegal_solution, total_cost=1.0)
    expensive_legal = replace(legal_solution, total_cost=9999.0)

    assert not _is_better_formal_solution(
        cheap_illegal,
        expensive_legal,
        problem=problem,
        policy_evaluator=policy,
    )
```

- [ ] **Step 3: Run tests to verify red state**

Run:

```powershell
pytest tests/test_scheduler.py tests/test_alns_smoke.py -q
```

Expected: FAIL because `SchedulingConfig.policy_evaluator` and `_is_better_formal_solution(..., policy_evaluator=...)` are not implemented.

- [ ] **Step 4: Implement scheduler policy candidates**

Modify `SchedulingConfig` in `green_logistics/scheduler.py`:

```python
from .policies import NoPolicyEvaluator, PolicyEvaluator


policy_evaluator: PolicyEvaluator = field(default_factory=NoPolicyEvaluator)
```

Modify `scheduling_selection_score`:

```python
score = route_quality_score(route, config.score_weights)
score += config.policy_evaluator.route_penalty(problem, route)
```

Because `scheduling_selection_score` currently only receives `route` and `config`, update its signature to:

```python
def scheduling_selection_score(problem: ProblemData, route: Route, config: SchedulingConfig) -> float:
```

Then update all call sites in `schedule_route_specs` and `choose_departure_min`.

Add a helper in `scheduler.py`:

```python
def policy_safe_departure_min(
    problem: ProblemData,
    spec: RouteSpecLike,
    vehicle_type_id: str,
    *,
    available_min: float,
    fixed_cost: float,
    config: SchedulingConfig,
) -> float | None:
    base = preferred_departure_min(problem, spec, available_min=available_min)
    route = evaluate_route(problem, vehicle_type_id, spec.service_node_ids, depart_min=base, fixed_cost=fixed_cost)
    if config.policy_evaluator.is_route_allowed(problem, route):
        return base

    high = base
    max_high = max(base, float(available_min)) + config.max_departure_delay_min
    while high <= max_high + 1e-9:
        high += 15.0
        route = evaluate_route(problem, vehicle_type_id, spec.service_node_ids, depart_min=high, fixed_cost=fixed_cost)
        if config.policy_evaluator.is_route_allowed(problem, route):
            return high
    return None
```

In `choose_departure_min`, add the returned safe departure to the candidate set when present. Keep all ETA calculations through `evaluate_route`; do not approximate travel time.

- [ ] **Step 5: Implement ALNS policy-aware scoring and best selection**

Modify `ALNSConfig`:

```python
from .policies import NoPolicyEvaluator, PolicyEvaluator


policy_evaluator: PolicyEvaluator = field(default_factory=NoPolicyEvaluator)
```

Add helper:

```python
def _candidate_search_score(problem: ProblemData, solution: Solution, cfg: ALNSConfig) -> float:
    return score_solution(solution, cfg.score_weights) + cfg.policy_evaluator.solution_penalty(problem, solution)
```

Use `_candidate_search_score` everywhere `score_solution` is currently called in `run_alns`.

Change `_is_better_formal_solution` signature:

```python
def _is_better_formal_solution(
    candidate: Solution,
    incumbent: Solution,
    *,
    problem: ProblemData | None = None,
    policy_evaluator: PolicyEvaluator | None = None,
) -> bool:
```

Before comparing total cost, reject candidates with policy conflicts when `problem` and `policy_evaluator` are provided:

```python
if problem is not None and policy_evaluator is not None:
    candidate_policy_ok = policy_evaluator.solution_violation_count(problem, candidate) == 0
    incumbent_policy_ok = policy_evaluator.solution_violation_count(problem, incumbent) == 0
    if not candidate_policy_ok:
        return False
    if not incumbent_policy_ok:
        return True
```

Pass `problem=problem, policy_evaluator=cfg.policy_evaluator` from `run_alns`.

- [ ] **Step 6: Verify focused tests pass**

Run:

```powershell
pytest tests/test_scheduler.py tests/test_alns_smoke.py tests/test_problem2_policy.py -q
```

Expected: tests pass.

## Task 4: Problem2Engine MVP

**Files:**
- Create: `green_logistics/problem2_engine.py`
- Create: `tests/test_problem2_engine.py`
- Create: `problems/problem2.py`
- Modify: `green_logistics/diagnostics.py`

- [ ] **Step 1: Write engine tests**

Create `tests/test_problem2_engine.py`:

```python
# -*- coding: utf-8 -*-

from pathlib import Path

from green_logistics.problem2_engine import Problem2Engine, choose_recommended_result
from green_logistics.problem_variants import SplitMode, load_problem_variant


def test_problem2_engine_smoke_default_variant_zero_policy_conflicts():
    variant = load_problem_variant(".", SplitMode.DEFAULT)
    engine = Problem2Engine(iterations=1, remove_count=4, seed=20260424)
    result = engine.run_variant(variant)

    assert result.variant_name == "default_split"
    assert result.solution.is_complete
    assert result.solution.is_capacity_feasible
    assert result.policy_conflict_count == 0


def test_problem2_recommendation_ignores_infeasible_result():
    class Result:
        def __init__(self, name, cost, conflicts):
            self.variant_name = name
            self.total_cost = cost
            self.policy_conflict_count = conflicts
            self.is_complete = True
            self.is_capacity_feasible = True

    recommended = choose_recommended_result(
        (
            Result("cheap_bad", 1.0, 2),
            Result("expensive_good", 100.0, 0),
        )
    )

    assert recommended.variant_name == "expensive_good"
```

- [ ] **Step 2: Run engine tests to verify red state**

Run:

```powershell
pytest tests/test_problem2_engine.py -q
```

Expected: FAIL because `green_logistics.problem2_engine` does not exist.

- [ ] **Step 3: Implement `problem2_engine.py`**

Create `green_logistics/problem2_engine.py`:

```python
# -*- coding: utf-8 -*-
"""Problem 2 orchestration for green-zone fuel restrictions."""

from __future__ import annotations

from dataclasses import dataclass

from .alns import ALNSConfig, ALNSResult, run_alns
from .initial_solution import construct_initial_route_specs
from .metrics import solution_quality_metrics
from .policies import GreenZonePolicyEvaluator
from .problem_variants import ProblemVariant
from .scheduler import SchedulingConfig, schedule_route_specs
from .solution import Solution


@dataclass(frozen=True)
class Problem2RunResult:
    variant_name: str
    service_node_count: int
    green_service_node_count: int
    initial_solution: Solution
    solution: Solution
    alns_result: ALNSResult
    policy_conflict_count: int
    total_cost: float
    is_complete: bool
    is_capacity_feasible: bool
    quality_metrics: dict[str, float | int]


@dataclass(frozen=True)
class Problem2Engine:
    iterations: int = 40
    remove_count: int = 8
    seed: int = 20260424
    optimize_departure_grid_min: int | None = 15
    max_departure_delay_min: float = 720.0

    def run_variant(self, variant: ProblemVariant) -> Problem2RunResult:
        policy = GreenZonePolicyEvaluator()
        scheduling_config = SchedulingConfig(
            policy_evaluator=policy,
            optimize_departure_grid_min=self.optimize_departure_grid_min,
            max_departure_delay_min=self.max_departure_delay_min,
        )
        initial_specs = construct_initial_route_specs(variant.data)
        initial_solution = schedule_route_specs(variant.data, initial_specs, config=scheduling_config)
        alns_result = run_alns(
            variant.data,
            initial_specs=initial_specs,
            config=ALNSConfig(
                iterations=self.iterations,
                remove_count=self.remove_count,
                seed=self.seed,
                scheduling_config=scheduling_config,
                policy_evaluator=policy,
            ),
        )
        solution = alns_result.best_solution
        conflict_count = policy.solution_violation_count(variant.data, solution)
        quality = solution_quality_metrics(solution).to_dict()
        return Problem2RunResult(
            variant_name=variant.name,
            service_node_count=variant.service_node_count,
            green_service_node_count=variant.green_service_node_count,
            initial_solution=initial_solution,
            solution=solution,
            alns_result=alns_result,
            policy_conflict_count=conflict_count,
            total_cost=solution.total_cost,
            is_complete=solution.is_complete,
            is_capacity_feasible=solution.is_capacity_feasible,
            quality_metrics=quality,
        )


def choose_recommended_result(results: tuple[Problem2RunResult, ...]):
    feasible = [
        result for result in results
        if result.is_complete and result.is_capacity_feasible and result.policy_conflict_count == 0
    ]
    if not feasible:
        raise ValueError("no policy-feasible Problem 2 result")
    return min(feasible, key=lambda result: result.total_cost)
```

- [ ] **Step 4: Implement the CLI runner**

Create `problems/problem2.py`:

```python
# -*- coding: utf-8 -*-
"""Run Problem 2: green-zone fuel restriction vehicle scheduling."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from green_logistics.output import write_solution_outputs
from green_logistics.problem2_engine import Problem2Engine, choose_recommended_result
from green_logistics.problem_variants import SplitMode, load_problem_variant


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    engine = Problem2Engine(
        iterations=args.iterations,
        remove_count=args.remove_count,
        seed=args.seed,
        optimize_departure_grid_min=args.optimize_departure_grid_min,
        max_departure_delay_min=args.max_departure_delay_min,
    )
    variants = tuple(load_problem_variant(args.data_dir, mode) for mode in (SplitMode.DEFAULT, SplitMode.GREEN_E2_ADAPTIVE))
    pairs = tuple((variant, engine.run_variant(variant)) for variant in variants)
    results = tuple(result for _, result in pairs)

    rows = []
    for variant, result in pairs:
        variant_dir = output_root / result.variant_name
        write_solution_outputs(result.solution, variant_dir, problem=variant.data)
        rows.append(_result_row(result))

    comparison = pd.DataFrame(rows)
    comparison_path = output_root / "variant_comparison.csv"
    comparison.to_csv(comparison_path, index=False, encoding="utf-8-sig")

    recommended = choose_recommended_result(results)
    recommendation = {
        "recommended_variant": recommended.variant_name,
        "total_cost": recommended.total_cost,
        "policy_conflict_count": recommended.policy_conflict_count,
        "is_complete": recommended.is_complete,
        "is_capacity_feasible": recommended.is_capacity_feasible,
        "variant_comparison_csv": str(comparison_path),
    }
    recommendation_path = output_root / "recommendation.json"
    recommendation_path.write_text(json.dumps(recommendation, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(recommendation, ensure_ascii=False, indent=2))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=".")
    parser.add_argument("--output-dir", default="outputs/problem2")
    parser.add_argument("--iterations", type=int, default=40)
    parser.add_argument("--remove-count", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260424)
    parser.add_argument("--optimize-departure-grid-min", type=int, default=15)
    parser.add_argument("--max-departure-delay-min", type=float, default=720.0)
    return parser.parse_args(argv)


def _result_row(result):
    return {
        "variant": result.variant_name,
        "service_node_count": result.service_node_count,
        "green_service_node_count": result.green_service_node_count,
        "total_cost": result.total_cost,
        "fixed_cost": result.solution.fixed_cost,
        "energy_cost": result.solution.energy_cost,
        "carbon_cost": result.solution.carbon_cost,
        "penalty_cost": result.solution.penalty_cost,
        "carbon_kg": result.solution.carbon_kg,
        "trip_count": len(result.solution.routes),
        "physical_vehicle_usage": json.dumps(result.solution.vehicle_physical_usage_by_type, ensure_ascii=False),
        "policy_conflict_count": result.policy_conflict_count,
        "is_complete": result.is_complete,
        "is_capacity_feasible": result.is_capacity_feasible,
    }


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Verify engine and runner smoke tests**

Run:

```powershell
pytest tests/test_problem2_engine.py tests/test_problem_variants.py tests/test_problem2_policy.py -q
python problems/problem2.py --iterations 1 --remove-count 4 --seed 20260424 --output-dir outputs/problem2_smoke
```

Expected: pytest passes; smoke run writes both variant folders and `outputs/problem2_smoke/recommendation.json` with `policy_conflict_count` equal to `0` for the recommended result.

## Task 5: Comparison Outputs And Documentation

**Files:**
- Modify: `green_logistics/output.py`
- Modify: `README.md`
- Modify: `项目文件导航.md`
- Modify: `task_plan.md`
- Modify: `findings.md`
- Modify: `progress.md`
- Create after real run: `docs/results/problem2_green_zone_policy_summary.md`

- [ ] **Step 1: Add comparison output test**

Create or extend `tests/test_output.py` with:

```python
from pathlib import Path

import pandas as pd

from green_logistics.output import write_problem2_comparison_outputs


def test_write_problem2_comparison_outputs(tmp_path):
    rows = [
        {"variant": "default_split", "total_cost": 10.0, "policy_conflict_count": 0, "is_complete": True, "is_capacity_feasible": True},
        {"variant": "green_e2_adaptive", "total_cost": 9.0, "policy_conflict_count": 0, "is_complete": True, "is_capacity_feasible": True},
    ]
    written = write_problem2_comparison_outputs(rows, tmp_path)

    assert written["variant_comparison_csv"].exists()
    table = pd.read_csv(written["variant_comparison_csv"])
    assert table["variant"].tolist() == ["default_split", "green_e2_adaptive"]
    assert written["policy_effect_summary_md"].read_text(encoding="utf-8").startswith("# Problem 2")
```

- [ ] **Step 2: Implement `write_problem2_comparison_outputs`**

Add to `green_logistics/output.py`:

```python
def write_problem2_comparison_outputs(rows: list[dict[str, object]], output_dir: str | Path) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    comparison = pd.DataFrame(rows)
    comparison_path = output_path / "variant_comparison.csv"
    comparison.to_csv(comparison_path, index=False, encoding="utf-8-sig")

    feasible = comparison[
        (comparison["policy_conflict_count"] == 0)
        & (comparison["is_complete"] == True)
        & (comparison["is_capacity_feasible"] == True)
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
```

- [ ] **Step 3: Run full regression after code changes**

Run:

```powershell
pytest -q
git diff --check
```

Expected: all tests pass; `git diff --check` reports no whitespace errors.

- [ ] **Step 4: Run formal Problem 2**

Run:

```powershell
python problems/problem2.py --iterations 40 --remove-count 8 --seed 20260424 --output-dir outputs/problem2
```

Expected: both candidate mainline outputs exist; `outputs/problem2/recommendation.json` points to a complete, capacity-feasible, zero-conflict variant.

- [ ] **Step 5: Update result documentation**

Create `docs/results/problem2_green_zone_policy_summary.md` with these sections:

```markdown
# Problem 2 Green-Zone Policy Result Summary

## Policy Interpretation

Fuel vehicles are forbidden from serving green-zone customers during `[480, 960)`. The available data do not contain road geometry, so traversal through the green circle between two customers is not directly observable.

## Candidate Mainlines

- `DEFAULT_SPLIT`: first-question service-node granularity with the Problem 2 hard policy gate.
- `GREEN_E2_ADAPTIVE`: non-green splits unchanged; green customers split by E2 capacity to enable small-EV cooperation.

## Recommendation Rule

The recommended result must be complete, capacity-feasible, and have zero policy conflicts. Among feasible candidates, the official total cost is minimized.

## Result Table

Use `outputs/problem2/variant_comparison.csv` as the numeric source.

## Interpretation Notes

If `GREEN_E2_ADAPTIVE` beats the first-question cost, describe it as demand-batch reconstruction under policy pressure, not as proof that adding a restriction reduces the same-model optimum.
```

Update navigation and progress docs with the exact commands and output metrics from the formal run.

## Task 6: Quality Upgrade After MVP

**Files:**
- Modify: `green_logistics/operators.py`
- Modify: `green_logistics/scheduler_local_search.py`
- Modify: `green_logistics/alns.py`
- Create: `problems/problem1_variant_baseline.py`
- Create: `problems/experiments/problem2_scenarios.py`

- [ ] **Step 1: Add policy-specific destroy/repair operators**

Add `policy_conflict_remove`, `green_related_remove`, and `ev_priority_insert` to `green_logistics/operators.py`. These functions should keep the current operator interface:

```python
def policy_conflict_remove(problem, specs, solution, rng, remove_count):
    policy = GreenZonePolicyEvaluator()
    conflict_node_ids = [
        int(stop.service_node_id)
        for route in solution.routes
        for stop in policy.violating_stops(problem, route)
    ]
    selected = tuple(conflict_node_ids[:remove_count])
    return _remove_nodes(specs, selected), selected
```

Register the operator by adding `"policy_conflict_remove": policy_conflict_remove`
to `DESTROY_OPERATORS`. The helper `_remove_nodes` already exists in
`operators.py`; use it for route-spec manipulation.

- [ ] **Step 2: Add scheduler local rescue for residual conflicts**

Add `rescue_policy_conflicts(problem, specs, solution, config)` to `green_logistics/scheduler_local_search.py`. Try replacements in this order:

1. Retype a violating F1 trip to E1 if capacity feasible.
2. Retype to E2 if all nodes fit E2.
3. Split the trip into smaller EV-feasible trips.
4. Delay the F1 trip so all green stops are outside `[480, 960)`.

Select the candidate with zero conflicts and the lowest official total cost.

- [ ] **Step 3: Add fair no-policy adaptive baseline**

Create `problems/problem1_variant_baseline.py` to run `GREEN_E2_ADAPTIVE` without green-zone policy. Output to `outputs/problem1_green_e2_adaptive_baseline/` so the paper can separate split-granularity benefits from policy costs.

- [ ] **Step 4: Add scenario experiments**

Create `problems/experiments/problem2_scenarios.py` with a small grid:

```python
SCENARIOS = (
    {"name": "restriction_8_13", "start_min": 480, "end_min": 780},
    {"name": "restriction_8_16", "start_min": 480, "end_min": 960},
    {"name": "restriction_8_17", "start_min": 480, "end_min": 1020},
)
```

Run each scenario for at least two seeds after the main Problem 2 solution is stable.

## Verification Gates

- Variant gate: `pytest tests/test_problem_variants.py -q`
- Policy gate: `pytest tests/test_problem2_policy.py tests/test_policies.py -q`
- Scheduler/ALNS gate: `pytest tests/test_scheduler.py tests/test_alns_smoke.py -q`
- Engine gate: `pytest tests/test_problem2_engine.py -q`
- Full regression: `pytest -q`
- Whitespace check: `git diff --check`
- Smoke run: `python problems/problem2.py --iterations 1 --remove-count 4 --seed 20260424 --output-dir outputs/problem2_smoke`
- Formal run: `python problems/problem2.py --iterations 40 --remove-count 8 --seed 20260424 --output-dir outputs/problem2`

## Implementation Order

1. Task 1: `problem_variants.py`, because `GREEN_E2_ADAPTIVE` must be explicit and testable before the engine can use it.
2. Task 2: policy evaluator hard boundary, because every later step depends on a reliable zero-conflict check.
3. Task 3: scheduler and ALNS policy gate, because the solver must not select infeasible Problem 2 solutions.
4. Task 4: `Problem2Engine` and runner, because this creates the first end-to-end deliverable.
5. Task 5: comparison outputs and result documentation.
6. Task 6: policy-specific operators, adaptive no-policy baseline, and scenario experiments to improve solution quality and paper strength.

## Risks To Watch

- Do not change default `load_problem_data`; first-question reproducibility depends on it.
- Do not use virtual `node_id` as a distance-matrix index; distance lookup stays on original `customer_id`.
- Do not add policy violation as a fifth official cost component.
- Do not claim route traversal through the green zone; current data only support service-stop policy checks.
- Do not treat E2 adaptive splitting as identical to the first-question baseline; it is a formal second-question candidate mainline with a separate fairness baseline.
- Do not create unreasonable midnight scheduling to avoid policy. The existing cross-midnight diagnostics must remain visible in outputs.
- Fixed cost must remain charged per physical vehicle, not per depot-to-depot trip.
