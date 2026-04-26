# TD-HFVRPTW Green Logistics Plan

## Purpose
This file is the persistent task plan for the project. It tracks phases,
decisions, and next actions so future windows can resume without rereading all
materials.

## Goal
Build executable and explainable Python solutions for the Huazhong Cup green
logistics scheduling task. Problem 1 is complete. Problem 2 now has a
policy-feasible, cost-primary formal result, and the next goal is to continue
Problem 2 optimization from a clearly documented handoff without confusing
formal outputs, scenario checks, and temporary experiments.

## Current Scope
This session is responsible for:
- Recording the current Problem 2 state for the next sub-dialogue.
- Keeping the Problem 2 objective aligned with the statement: minimum official
  total delivery cost, soft time windows, and hard green-zone policy feasibility.
- Marking temporary Problem 2 outputs as cleaned or non-formal.
- Preparing durable notes and an initialization prompt for the next
  optimization session.

## Phases

| Phase | Status | Output |
| --- | --- | --- |
| 1. Project/context scan | complete | File inventory, attachment availability, reference material status |
| 2. Data fact extraction | complete | Excel schema, demand aggregation, green-zone customers, overloaded customers |
| 3. Reference-solution audit | complete | Accepted/rejected modeling assumptions |
| 4. Architecture decision | complete | Data structures, objective, travel-time and cost interfaces, search algorithm |
| 5. Data-processing implementation | complete | `green_logistics/data_processing/` and pytest validation |
| 6. Test runner configuration | complete | `pytest.ini` for stable imports |
| 7. Main technical blueprint | complete | `解题总思路.md` |
| 8. Project file navigation | complete | `项目文件导航.md` |
| 9. Optimization implementation | complete | Problem 1 route evaluator, initial solution, ALNS, outputs, and runner implemented |
| 10. Service-quality optimization | complete | Metrics, search score, true-lateness operators, and improved Problem 1 result |
| 11. Problem 1 round-2 C-lite optimization | complete | Scheduler extraction, diagnostics, cost-primary best selection, and Problem 2 preparation hooks |
| 12. Problem 1 closeout documentation | complete | Paper-style summary in `docs/results/problem1_static_scheduling_summary.md` and output ledger in `outputs/README.md` |
| 13. Problem 2 route design | complete | Audited three Problem 2 reference plans and recorded the implementation roadmap in `docs/design/problem2_green_zone_policy_roadmap.md` |
| 14. Problem 2 implementation planning | complete | Promoted `GREEN_E2_ADAPTIVE` to a formal candidate mainline and wrote `docs/superpowers/plans/2026-04-25-problem2-engine-green-e2-adaptive.md` |
| 15. Problem 2 implementation and formal run | complete | Independent `Problem2Engine`, formal `outputs/problem2/`, and result summary in `docs/results/problem2_green_zone_policy_summary.md` |
| 16. Problem 2 handoff for sub-dialogue 3 | complete | `docs/design/problem2_subdialogue3_optimization_handoff.md`, output cleanup notes, and updated navigation/progress ledgers |

## Key Decisions So Far
- The local original-problem PDF appears to be a Baidu share printout, not the problem statement body. Treat coefficients from reference files as provisional unless also supported by accessible problem material.
- The original-problem PDF has been replaced and is now readable. It confirms
  the five vehicle classes, soft time-window costs, startup cost, U-shaped
  fuel/electricity formulas, and the three required questions.
- The supplement PDF is readable and has priority for green-zone and speed-distribution definitions.
- Data files are `.xlsx`, not `.csv`; loader should support both when practical.
- Internal service nodes must be virtual nodes after multi-trip splitting; distance matrix indices must remain original customer IDs.
- `Route` is interpreted as one depot-to-depot trip. Physical vehicles can be
  assigned multiple sequential trips, and fleet limits are checked against
  physical vehicle IDs.

## Approved Architecture For Implementation
- Use expected-speed deterministic approximation with segment integration as the primary model.
- Split overloaded customer demands into virtual service nodes by both weight and volume capacity.
- Integrate both travel time and energy cost over time segments. Use speed means for deterministic schedule propagation, and use second moments for expected U-shaped energy cost.
- Use a transparent heuristic stack: feasible construction plus ALNS/local search, not a pure black-box solver.
- Implement modules incrementally with pytest tests first.

## Module Structure
- `项目文件导航.md`: file ledger and onboarding guide. Update it whenever files
  or folders are created, moved, deleted, or renamed.
- `解题总思路.md`: main modeling and implementation blueprint for all future
  tasks.
- `green_logistics/constants.py`: all vehicles, time, speed, energy, carbon, and
  penalty constants.
- `green_logistics/data_processing/loader.py`: file discovery, raw data loading,
  validation, demand aggregation, green-zone marking, and virtual-node splitting.
- `green_logistics/data_processing/README.md`: data-processing handoff document
  for future sub-dialogues.
- `green_logistics/data_loader.py`: backward-compatible wrapper for older imports.
- `green_logistics/travel_time.py`: time-dependent ETA by segment integration.
- `green_logistics/cost.py`: expected energy, carbon, fixed, and time-window costs.
- `green_logistics/solution.py`: route and solution dataclasses.
- `green_logistics/metrics.py`: service-quality metrics and search-score
  helpers.
- `green_logistics/initial_solution.py`: feasible construction heuristic and
  compatibility import for the scheduler.
- `green_logistics/scheduler.py`: second-stage physical-vehicle scheduler,
  `SchedulingConfig`, reload/return-limit/departure-grid scenario knobs.
- `green_logistics/trips.py`: lightweight `TripDescriptor` helpers.
- `green_logistics/diagnostics.py`: late-stop, green-zone capacity, and Problem
  2 policy-conflict diagnostics.
- `green_logistics/policies.py`: policy evaluator interfaces for Problem 1/2.
- `green_logistics/problem_variants.py`: explicit Problem 2 data-variant layer
  for `DEFAULT_SPLIT` and `GREEN_E2_ADAPTIVE`.
- `green_logistics/problem2_engine.py`: independent Problem 2 orchestrator,
  not folded into the Problem 1 runner.
- `green_logistics/scheduler_local_search.py`: residual late-route rescue by
  targeted retyping/splitting.
- `green_logistics/alns.py` and `green_logistics/operators.py`: adaptive search.
- `green_logistics/output.py`: structured result export for papers.

## Optimization Implementation Progress

| Module | Status | Verification |
| --- | --- | --- |
| `green_logistics/travel_time.py` | complete | `pytest tests/test_travel_time.py -v` |
| `green_logistics/cost.py` | complete | `pytest tests/test_cost.py -v` |
| `green_logistics/solution.py` | complete | `pytest tests/test_solution.py -v` |
| `green_logistics/metrics.py` | complete | `pytest tests/test_metrics.py -v` |
| `green_logistics/initial_solution.py` | complete | `pytest tests/test_initial_solution.py -v` |
| `green_logistics/scheduler.py` / `green_logistics/trips.py` | complete | `pytest tests/test_scheduler.py tests/test_trips.py -v` |
| `green_logistics/diagnostics.py` / `green_logistics/policies.py` | complete | `pytest tests/test_diagnostics.py tests/test_policies.py -v` |
| `green_logistics/scheduler_local_search.py` | complete | `pytest tests/test_scheduler_local_search.py -v` |
| `green_logistics/operators.py` / `green_logistics/alns.py` | complete | `pytest tests/test_alns_smoke.py -v` |
| `green_logistics/output.py` / `problems/problem1.py` | complete | `pytest tests/test_output.py -v`; real run in `outputs/problem1/` |
| `green_logistics/problem_variants.py` / `green_logistics/problem2_engine.py` / `problems/problem2.py` | complete | `pytest tests/test_problem_variants.py tests/test_problem2_policy.py tests/test_problem2_engine.py -v`; real run in `outputs/problem2/` |

Latest Problem 1 cost-primary result:

- Command: `python problems/problem1.py --iterations 40 --remove-count 8 --seed 20260424 --output-dir outputs/problem1`
- Total cost: `48644.68`
- Time-window penalty: `933.53`
- Trips: `116`
- Physical vehicle usage: `{'E1': 10, 'F1': 33}`
- Late stops: `4`
- Max lateness: `31.60 min`
- Cross-midnight returns: `0`
- `outputs/problem1_baseline_quality_48644/` preserves the same cost-primary
  solution as a rerun backup.

## Compressed Handoff Context For Future Work

Current Problem 1 status:
- The original cost-priority baseline was complete and capacity feasible, but
  had systematic lateness: 84 late stops, max lateness about 286 min, and 8
  cross-midnight returns.
- The official Problem 1 objective is minimum total delivery cost. The solver
  keeps the official soft time-window cost unchanged and selects the formal
  result by `total_cost`; service-quality `search_score` is an auxiliary
  heuristic and reporting diagnostic, not the final objective.
- The latest formal result has 4 late stops, max lateness 31.60 min, no
  cross-midnight returns, and total cost 48644.68.

Current architecture:
- `Route` means one depot-to-depot trip.
- `RouteSpec` is the current unassigned trip representation searched by ALNS.
- `schedule_route_specs()` now lives in `green_logistics/scheduler.py`;
  `green_logistics/initial_solution.py` keeps a compatibility import.
- `green_logistics/metrics.py` provides service-quality metrics and
  `search_score`. Official reported cost remains
  fixed + energy + carbon + soft time-window penalty.
- `operators.py` now has true-lateness destroy/split operators that can inspect
  the current scheduled `Solution`.
- `diagnostics.py` writes residual lateness classification, green-zone capacity,
  and first-question Problem 2 policy-conflict reports.
- `policies.py` provides `NoPolicyEvaluator` and a Problem 2
  `GreenZonePolicyEvaluator` skeleton.

Important modeling boundaries:
- Never use virtual `node_id` as a distance-matrix index; use original
  `customer_id`.
- Travel time and energy must stay segment-integrated across speed periods.
- Jensen correction for expected energy must stay in place.
- Do not add a default 22:00 hard return constraint; the problem statement does
  not provide it. A 22:00 return limit may be a scenario/sensitivity parameter.
- The current code assumes 17:00 and later continue with the MEDIUM speed
  regime. This assumption must be stated in the paper unless later replaced by a
  configurable scenario.

Potential next architecture step:
- C-lite refactor is complete: physical scheduling is in
  `green_logistics/scheduler.py`, `TripDescriptor` lives in
  `green_logistics/trips.py`, and Problem 2 policy hooks are reserved.
- Full scheme C, where ALNS only emits trip descriptors and an independent
  scheduler owns all physical-vehicle neighborhoods, is cleaner long term but
  should be justified by Problem 2/3 needs rather than by current Problem 1
  service quality alone.

Problem 1 closeout:
- Formal output folder: `outputs/problem1/`.
- Output folder ledger: `outputs/README.md`.
- Paper-ready modeling and result summary:
  `docs/results/problem1_static_scheduling_summary.md`.
- Problem 2 route design:
  `docs/design/problem2_green_zone_policy_roadmap.md`.
- Problem 2 implementation plan:
  `docs/superpowers/plans/2026-04-25-problem2-engine-green-e2-adaptive.md`.
- Problem 2 formal output folder: `outputs/problem2/`.
- Problem 2 paper-ready result summary:
  `docs/results/problem2_green_zone_policy_summary.md`.
- Problem 2 continuation handoff for sub-dialogue 3:
  `docs/design/problem2_subdialogue3_optimization_handoff.md`.
- Historical Problem 2 status before the EV-reservation pass: the official
  objective remained total delivery cost with soft time-window penalties, while
  the green-zone fuel restriction was a hard feasibility gate. The then-formal
  recommendation was `DEFAULT_SPLIT` with total cost `49888.84` and zero policy
  conflicts. The current formal result is recorded in the later
  "Problem 2 EV-Reservation Optimization Status" and "Problem 2 Closeout
  Status" sections.
- Temporary Problem 2 output folders `outputs/problem2_smoke/` and
  `outputs/problem2_candidate_seed37_r16/` have been cleaned so future sessions
  do not confuse them with the formal result. `outputs/problem2_return1440_trial/`
  is retained only as a 24:00 return-limit scenario check; the problem
  statement does not make that a hard feasibility condition.
- Next optimization should prioritize lower official total cost with zero
  policy conflicts. Reducing the current maximum lateness of `124.92 min` is a
  valuable secondary diagnostic goal, but must not replace the official
  objective.

## Problem 2 Subdialogue 3 Roadmap Status

Current status:
- The requested subdialogue-three intake is complete: project docs, problem
  statement, supplement, current Problem 2 outputs, core code, tests, and the
  three new second-round reference files have been reviewed.
- The maximum-lateness bottleneck has been localized to EV multi-trip cascade,
  not direct time-window infeasibility: the worst stop is `T0021` on `E1-009`,
  customer `8`, service node `13`, late by `124.92 min`, after a non-green
  predecessor trip that appears fuel-feasible.
- The combined implementation route is documented in
  `docs/design/problem2_subdialogue3_optimization_roadmap.md`.

Next implementation phases:
- P0: preserve the formal `outputs/problem2/` result and build an experiment
  ledger for multi-seed/remove-count searches.
- P1: enhance `late_stop_diagnosis.csv` with EV-cascade and policy-induced
  lateness fields.
- P2: run lightweight parameter sweeps before changing core algorithms.
- P3: add optional EV scarcity/reservation scoring to the scheduler.
- P4: implement EV blocking-chain destroy/local-search neighborhoods.
- P5: add a cost-first near-cost elite pool only as a search aid.
- P6: test a bounded `GREEN_HOTSPOT_PARTIAL` variant before considering any
  larger data-layer rewrite.

Final 2026-04-26 calibration:
- Treat full `GREEN_E2_ADAPTIVE` as a documented comparison baseline, not the
  next optimization mainline.
- Execute the next code work in this order: experiment ledger, EV-cascade
  diagnostics, scheduler EV opportunity-cost scoring, blocking-chain
  neighborhoods, near-cost elite search aid, then `GREEN_HOTSPOT_PARTIAL`.
- Keep all auxiliary penalties and lateness tie-breaks outside the official
  cost formula; final recommendation remains cost-primary with zero policy
  conflicts.

## Problem 2 EV-Reservation Optimization Status

Completed in the 2026-04-26 execution pass:
- Added EV-cascade fields to `late_stop_diagnosis.csv`.
- Added optional scheduler EV reservation scoring with CLI flags
  `--use-ev-reservation` and `--ev-reservation-penalty`.
- Added `ev_blocking_chain_remove` for policy-operator experiments.
- Added bounded `GREEN_HOTSPOT_PARTIAL` as a third formal comparison variant.
- Added `problems/experiments/problem2_parameter_sweep.py` for incremental
  experiment ledgers.
- Promoted the best verified run to `outputs/problem2/`.

New formal Problem 2 command:

```powershell
python problems/problem2.py --iterations 40 --remove-count 16 --seed 20260427 --use-ev-reservation --ev-reservation-penalty 250 --output-dir outputs/problem2
```

New formal recommendation:
- Variant: `DEFAULT_SPLIT`
- Total cost: `49239.78`
- Policy conflicts: `0`
- Complete/capacity feasible: `True` / `True`
- Physical vehicles: `E1:10, F1:35`
- Late stops / max late: `12` / `129.44 min`
- Previous formal result is preserved at
  `outputs/problem2_previous_49888_20260425/`.

## Problem 2 Closeout Status

Completed for the current modeling round:
- Created the full paper-writing closeout document
  `docs/results/problem2_modeling_and_solution_closeout.md`.
- Cleaned the promoted intermediate folders
  `outputs/problem2_ev_reservation_p250/` and
  `outputs/problem2_ev_reservation_p250_full/` so `outputs/problem2/` remains
  the only formal Problem 2 answer folder.
- Preserved `outputs/problem2_previous_49888_20260425/` as the historical
  backup and `outputs/problem2_experiments/formal_screen_policy_ev_p500/` as
  the service-quality sensitivity case.

Problem 2 is temporarily closed. The next active modeling phase should start
Problem 3 and reuse the Problem 2 policy evaluator, scheduler, diagnostics,
engine, and experiment-ledger interfaces rather than reopening the Problem 2
objective unless a clearly lower official total-cost candidate is found.

## Problem 3 Handoff Preparation

Completed:
- Added `docs/design/problem3_subdialogue4_initialization_prompt.md` as the
  handoff report and ready-to-copy prompt for the next sub-dialogue.
- Confirmed the output layout is clean: `outputs/problem1/` and
  `outputs/problem2/` are formal, `outputs/problem2_previous_49888_20260425/`
  is historical backup, and `outputs/problem2_experiments/` is experiment
  ledger only.
- Recorded that Problem 3 should create `outputs/problem3/` and must not
  overwrite the first- or second-question formal outputs.

Next phase:
- Start Problem 3 by re-reading the original problem statement and supplement,
  then build a dynamic-event response roadmap before implementing
  `problems/problem3.py` and its tests.

## Problem 3 Dynamic Response Roadmap

Completed in the 2026-04-26 synthesis pass:
- Audited the three new Problem 3 reference files under `第三问参考思路/`.
- Reconfirmed from the original problem statement that Problem 3 lists order
  cancellation, new orders, address changes, and time-window adjustments, but
  does not provide concrete event data.
- Added `docs/design/problem3_dynamic_response_roadmap.md` as the integrated
  route. The mainline inherits the Problem 2 green-zone policy by assumption,
  uses `outputs/problem2/` `DEFAULT_SPLIT` as the primary baseline, and keeps
  `outputs/problem1/` only as a no-policy sensitivity baseline if needed.
- Recorded the physical cargo-state rule: already departed trips cannot receive
  new orders or transfer onboard undelivered goods to another vehicle unless a
  return-to-depot or transfer mechanism is explicitly modeled.

Next implementation priority:
- P0: add tests for dynamic event ledgers and freeze rules.
- P1: add `green_logistics/dynamic.py` for events, snapshots, frozen plans, and
  residual request pools.
- P2: add scheduler warm-start support for locked routes and initial vehicle
  availability.
- P3: add dynamic residual route evaluation without breaking the existing
  depot-to-depot `evaluate_route()` behavior.
- P4: add `green_logistics/problem3_engine.py`, `problems/problem3.py`, and
  output writers under `outputs/problem3/`.
- P5: add frozen-safe light ALNS and stability diagnostics only after the
  deterministic repair path is verified.

## Problem 3 Dynamic Response Implementation

Completed in the 2026-04-26 implementation pass:
- Added `green_logistics/dynamic.py` for dynamic events, route/visit snapshots,
  locked vs adjustable partitions, and event application to service-node data.
- Extended `green_logistics/scheduler.py` with `VehicleState`, warm-start
  availability, and first-use fixed-cost handling while preserving default
  static behavior.
- Added `green_logistics/problem3_engine.py` with baseline reconstruction,
  automatic representative scenarios, stable repair, light ALNS candidate
  generation, stability-aware selection, route-change diagnostics, and Problem
  3 output writers.
- Added `problems/problem3.py` CLI. Default baseline is
  `outputs/problem2/default_split`, and default output is `outputs/problem3/`.
- Added tests: `tests/test_dynamic.py`, `tests/test_problem3_engine.py`, and
  `tests/test_problem3.py`; updated `tests/test_scheduler.py` for warm-start
  scheduling.
- Generated `outputs/problem3/` and
  `docs/results/problem3_dynamic_response_summary.md`.

Current Problem 3 result:
- Baseline: Problem 2 `DEFAULT_SPLIT`, total cost `49239.78`.
- Four scenario assumptions: cancellation, new green order, time-window
  pull-forward, and address-change proxy.
- All four scenarios are complete, capacity feasible, physical-chain feasible,
  and policy-conflict free.
- Scenario costs: `48711.28`, `49237.36`, `49263.35`, and `49207.47`.

Known limitation:
- The event data are representative assumptions, not official records. Address
  changes and new orders use existing customer proxy points to avoid inventing
  a new road-distance matrix.
