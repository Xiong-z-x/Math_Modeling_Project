# Problem 1 Service-Quality Optimization Plan

## Goal
Implement the service-quality optimization design for Problem 1 in small,
tested steps.

## Task 1: Quality Metrics
- [x] Add tests for solution-level late, wait, return, and physical-vehicle trip
      metrics.
- [x] Implement `green_logistics/metrics.py`.
- [x] Extend Problem 1 output summary and tables with quality metrics.
- [x] Verify focused metric and output tests.

## Task 2: Service-Quality Scheduling
- [x] Add a regression test showing the scheduler chooses a new physical vehicle
      when reusing an existing one would create large lateness.
- [x] Replace the weak local scheduling score with route service-quality score.
- [x] Verify initial-solution tests and real-data scheduling diagnostics.

## Task 3: ALNS Search Score
- [x] Add tests that ALNS history records search score and quality metrics.
- [x] Make ALNS acceptance and best-solution selection use search score.
- [x] Keep official cost fields intact for reporting.

## Task 4: True-Lateness Operators
- [x] Change destroy operators to accept the current scheduled `Solution`.
- [x] Add `actual_late_remove`, `late_suffix_remove`, and
      `midnight_route_remove`.
- [x] Add `late_route_split` as a structural split operator.
- [x] Verify operators preserve service-node coverage after repair.

## Task 5: Real-Data Verification and Documentation
- [x] Run `pytest -v`.
- [x] Run Problem 1 on real data without overwriting the prior baseline until
      metrics look reasonable.
- [x] Generate final `outputs/problem1/` results.
- [x] Update `README.md`, `task_plan.md`, `progress.md`,
      `项目文件导航.md`, and relevant plan files.

## Notes
- The main model strongly penalizes cross-midnight routes, but does not add an
  unstated 22:00 hard constraint.
- If runtime becomes too high, finish Tasks 1-3 first and record the remaining
  operator work as the next safe phase.
- Final 40-iteration result after stronger default service-quality weights:
  total cost `48644.68`, 4 late stops, max lateness `31.60` min, and 0
  cross-midnight returns.
