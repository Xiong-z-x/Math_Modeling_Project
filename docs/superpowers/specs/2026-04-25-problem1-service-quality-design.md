# Problem 1 Service-Quality Optimization Design

## Goal
Reduce the systematic lateness in the Problem 1 static scheduling solution while
preserving the official cost accounting, service-node coverage, capacity
feasibility, time-dependent travel-time integration, and customer-id distance
lookup rules.

The current cost-priority baseline remains useful as a reference, but the main
solver should produce a service-quality balanced solution with far fewer late
stops and no cross-midnight routes unless explicitly requested by a scenario.

## Current Facts
- `Route` is one depot-to-depot trip, not a full physical vehicle workday.
- `schedule_route_specs()` already assigns trips to physical vehicles and is
  called for every ALNS candidate.
- Fixed cost is charged once per physical vehicle; reusing a physical vehicle
  for later trips has zero additional fixed cost.
- The official time-window penalty is soft and relatively small compared with
  opening a new physical vehicle.
- Current ALNS operators score most insertions/removals using an artificial
  08:00 departure, so they do not see the actual scheduled lateness after
  physical-vehicle reuse.
- The official problem statement does not define a 22:00 return constraint. The
  main model should not add that as a hard constraint.

## Design
Add service-quality metrics as first-class outputs and auxiliary search inputs.
Official cost remains unchanged. ALNS may use a separate search score for
candidate acceptance and scheduling tie-breaking, but the formal best solution
must be selected by official total cost because Problem 1 asks for minimum total
delivery cost with soft time-window penalties.

The default search score is:

```text
true_total_cost
+ 500 * late_stop_count
+ 1 * total_late_min
+ 8 * max_late_min
+ 1_000_000 * return_after_midnight_count
```

This makes cross-midnight routes effectively unacceptable in the main search
without inventing a non-stated 22:00 hard constraint.

## Components
- `green_logistics/metrics.py`: service-quality metrics and search-score
  helpers for both full solutions and single routes.
- `green_logistics/output.py`: writes quality metrics into `summary.json` and a
  CSV table.
- `green_logistics/scheduler.py`: owns physical-vehicle scheduling and
  service-quality scoring; `initial_solution.py` keeps only construction and
  compatibility import.
- `green_logistics/diagnostics.py`: classifies residual late stops and prepares
  Problem 2 green-zone diagnostics.
- `green_logistics/trips.py`: provides lightweight trip descriptors.
- `green_logistics/policies.py`: reserves Problem 2 policy evaluator hooks.
- `green_logistics/alns.py`: records and optimizes `search_score` while keeping
  `total_cost` as the official cost.
- `green_logistics/operators.py`: lets destroy operators inspect the current
  scheduled `Solution` and adds true-lateness-oriented destroy operators.

## Guardrails
- Do not re-read or aggregate Excel outside `load_problem_data()`.
- Do not confuse virtual `node_id` with original `customer_id`.
- Do not replace official soft time-window costs with a changed objective in
  final cost reporting; search score is only a heuristic guide.
- Do not make 22:00 a default hard constraint.
- Keep coverage and capacity checks as hard verification requirements.

## Acceptance Targets
Initial implementation target:
- `return_after_midnight_count == 0`
- `late_stop_count <= 20`
- `max_late_min <= 120`
- `solution.is_complete is True`
- `solution.is_capacity_feasible is True`

Stretch target after late-route split and true-lateness operators:
- `late_stop_count <= 10`
- `max_late_min <= 60`
- total cost remains explainable as a service-quality tradeoff.

Current 2026-04-25 cost-primary result: total cost 48644.68, 4 late stops, max
lateness 31.60 min, and no cross-midnight returns. A zero-late trial cost more,
so it is not the formal Problem 1 answer.
