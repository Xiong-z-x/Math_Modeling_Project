# Progress

## Purpose
This file is the chronological session log. It records completed actions,
verification commands, and the next safe step.

## 2026-04-24
- Loaded requested skills: Superpowers workflow, brainstorming, find-skills, self-improvement, and Chinese file-planning.
- Scanned repository structure and confirmed local attachment/reference files.
- Extracted supplement PDF text successfully.
- Found that the original problem PDF is only a Baidu share printout.
- Read Excel schemas and computed core data statistics.
- Checked whether order-level indivisibility is feasible; it is not, because a raw order exceeds the largest vehicle capacity.
- Logged a PowerShell/Python Chinese-path encoding error in `.learnings/ERRORS.md`.
- Created durable planning files for follow-up windows.
- Completed the first-pass reference audit and identified required architecture revisions.
- Read the newly uploaded original problem PDF; it is valid and supersedes the
  earlier Baidu-share printout.
- Read the new Claude Codex implementation handbook and audited it against the
  data facts.
- Wrote data-layer tests first and confirmed the expected initial failure
  (`green_logistics` package missing).
- Implemented `green_logistics/constants.py` and
  `green_logistics/data_loader.py`.
- Verified the data layer with `python -m pytest tests/test_data_loader.py -v`:
  5 tests passed.
- Added `pytest.ini` to stabilize package imports for the bare `pytest`
  command. Verified with `pytest tests/test_data_loader.py -v`: 5 tests passed.
- Reorganized the data layer into `green_logistics/data_processing/`.
- Added `green_logistics/data_processing/README.md` as the data-processing
  handoff document for future sub-dialogues.
- Preserved `green_logistics/data_loader.py` as a compatibility wrapper.
- Updated `.gitignore` for `.pytest_cache/` and local `.learnings/`.
- Verified the reorganized data layer with `pytest tests/test_data_loader.py -v`:
  6 tests passed.
- Ran a direct loader smoke check from `green_logistics.data_processing`; it
  reported 2169 orders, 88 active customers, 148 service nodes, 12 active
  green-zone customers, and max virtual-node demand within `(3000 kg, 15 m3)`.
- Created `解题总思路.md` as the main technical route and modeling blueprint.
- Linked `解题总思路.md` from `README.md` and `task_plan.md`.
- Created `项目文件导航.md` as the project file ledger and onboarding guide.
- Linked `项目文件导航.md` from `README.md` and `task_plan.md`.
- Sub-dialogue 1 resumed with the scope narrowed to `travel_time.py` and
  `cost.py` before ALNS.
- Wrote `tests/test_travel_time.py` first and observed the expected red state:
  initial import failure for missing `green_logistics.travel_time`, then
  `NotImplementedError` failures after adding the interface skeleton.
- Implemented `green_logistics/travel_time.py` with speed-period lookup,
  cross-period segment integration, arrival-time calculation, and validation
  for negative distance / pre-08:00 departure.
- Verified travel-time behavior with `pytest tests/test_travel_time.py -v`:
  5 tests passed.
- Wrote `tests/test_cost.py` first and observed the expected red state:
  missing `green_logistics.cost`, then `NotImplementedError` failures after
  adding the interface skeleton.
- Added fuel and EV quadratic consumption coefficients to
  `green_logistics/constants.py`.
- Implemented `green_logistics/cost.py` with Jensen-corrected expected
  consumption, payload load factors, segment-accumulated energy/carbon cost,
  and arrival-based soft time-window penalties.
- Verified cost behavior with `pytest tests/test_cost.py -v`: 4 tests passed.
- Updated `README.md`, `task_plan.md`, and `项目文件导航.md` to record the new
  modules and tests.
- Ran full regression verification with `pytest -v`: 15 tests passed.
- Ran a real-data smoke check through `load_problem_data(".")`, using the first
  virtual service node's `customer_id` to look up `distance_matrix.loc[0,
  customer_id]`. For service node 1 / customer 2, depot distance was
  `38.223950 km`, arrival was `570.839729 min`, segments were congested then
  smooth, energy cost was `76.848521`, and carbon cost was `16.718340`.
- Continued Problem 1 implementation using the existing execution plan.
- Found an important feasibility issue: among the 148 virtual service nodes,
  114 nodes weigh more than `1500 kg`, while only 70 physical vehicles have
  3000 kg capacity (`F1` + `E1`). A strict one-trip-per-vehicle interpretation
  is infeasible. Recorded this in `findings.md` and `.learnings/LEARNINGS.md`.
- Implemented `green_logistics/solution.py` with trip-level route evaluation:
  virtual node to original customer mapping, distance-matrix lookup by
  `customer_id`, capacity checks, load-decreasing arc costs, soft time-window
  propagation, and solution coverage checks.
- Added `tests/test_solution.py`; verified with `pytest tests/test_solution.py
  -v`: 4 tests passed. During development, corrected two test hand-calculation
  mistakes in synthetic distance/time expectations.
- Implemented `green_logistics/initial_solution.py` with route-spec
  construction and physical-vehicle scheduling. Trips can be assigned
  sequentially to the same physical vehicle, and fixed cost is charged once per
  physical vehicle.
- Added `tests/test_initial_solution.py`; verified with `pytest
  tests/test_initial_solution.py -v`: 3 tests passed. Added a regression test
  so fresh vehicles delay departure to reduce first-stop waiting.
- Implemented `green_logistics/operators.py` with Random Remove, Worst Cost
  Remove, Related Remove, Time Penalty Remove, Greedy Insert, Regret-2 Insert,
  and Time-Oriented Insert.
- Implemented `green_logistics/alns.py` with simulated-annealing acceptance and
  complete candidate re-evaluation after each destroy/repair step.
- Added `tests/test_alns_smoke.py`; verified with `pytest
  tests/test_alns_smoke.py -v`: 2 tests passed.
- Implemented `green_logistics/output.py` with route summary, stop schedule,
  cost summary, vehicle usage, JSON summary, and PNG charts for route map, cost
  breakdown, vehicle usage, and time-window comparison.
- Added `tests/test_output.py`; verified with `pytest tests/test_output.py -v`:
  1 test passed.
- Added `problems/problem1.py` as the real-data runner.
- Verified the full test suite with `pytest -v`: 24 tests passed before the
  final documentation update.
- Ran real Problem 1 with `python problems/problem1.py --iterations 20
  --remove-count 8 --seed 20260424 --output-dir outputs/problem1`: best cost
  `74483.87`, complete and capacity feasible, 115 trips, 29 physical vehicles.
- Improved scheduling after diagnosing excessive first-stop waiting. Re-ran
  `pytest tests/test_initial_solution.py -v` and `pytest
  tests/test_alns_smoke.py -v`; both passed.
- Diagnosed an additional quality issue: allowing EV selection with a purely
  local greedy score overused the 10 E1 vehicles and inflated time-window
  penalty. Added a scheduling-selection late-risk score so EVs are used when
  beneficial without being blindly over-reused. Verified with `pytest
  tests/test_initial_solution.py -v`: 4 tests passed.
- Ran final real Problem 1 with `python problems/problem1.py --iterations 40
  --remove-count 8 --seed 20260424 --output-dir outputs/problem1`: best total
  cost `51870.90`; fixed `14800.00`, energy `23017.23`, carbon `4953.10`,
  time-window penalty `9100.58`; total distance `13342.28 km`; carbon
  `7620.15 kg`; 115 trips assigned to 10 E1 and 27 F1 physical vehicles;
  complete service coverage and capacity feasibility both `True`.
- Result caveat: the solution still has nontrivial soft time-window lateness
  (`84` late stops, max late about `286` min, `8` trips returning after
  midnight). This is a remaining heuristic/modeling tradeoff under multi-trip
  reuse and soft time windows, not something to hide in the paper.
- After documentation updates, ran final full regression with `pytest -v`: 25
  tests passed.
- Ran current-code Problem 1 smoke check with `python problems/problem1.py
  --iterations 1 --remove-count 4 --seed 20260424 --output-dir
  outputs/problem1_smoke`: completed, complete `True`, capacity feasible
  `True`. Removed the temporary smoke output directory afterward; the formal
  40-iteration result remains in `outputs/problem1/`.

## Next Step
Run final full regression after documentation updates, then either strengthen
Problem 1 optimization with longer ALNS / stricter service-day assumptions or
move to Problem 2 green-zone restrictions.
