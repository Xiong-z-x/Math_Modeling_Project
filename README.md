# City Green Logistics Scheduling

This repository contains the Python implementation work for Huazhong Cup
Problem A, "City Green Logistics Scheduling".

## File Map

- `项目文件导航.md`: file ledger and onboarding guide. Future sub-dialogues
  should read this first to understand the current project layout.
- `解题总思路.md`: main technical route and modeling blueprint. Future
  implementation work should align with this file first.
- `task_plan.md`: persistent task plan. It records phases, current status, and
  implementation decisions so later sessions can resume safely.
- `findings.md`: research notes. It stores verified facts from the problem PDF,
  supplement, data files, and reference solutions.
- `progress.md`: session log. It records what has been done and what should
  happen next.
- `docs/results/problem1_static_scheduling_summary.md`: paper-oriented
  closeout summary for Problem 1, including model formulas, assumptions,
  results, diagnostics, and visualization notes.
- `docs/design/problem2_green_zone_policy_roadmap.md`: integrated Problem 2
  route design after auditing the three new green-zone policy reference plans.
- `docs/results/problem2_green_zone_policy_summary.md`: paper-oriented
  closeout summary for the current Problem 2 result and candidate comparison.
- `docs/results/problem2_modeling_and_solution_closeout.md`: full
  paper-writing closeout for Problem 2, including assumptions, symbols,
  formulas, constraints, algorithm design, final results, sensitivity notes,
  visualization guidance, and the reserved Problem 3 interface.
- `docs/design/problem2_subdialogue3_optimization_handoff.md`: one-page
  handoff report plus a ready-to-use initialization prompt for the next Problem
  2 optimization sub-dialogue.
- `docs/superpowers/plans/2026-04-25-problem2-engine-green-e2-adaptive.md`:
  implementation plan for the independent Problem 2 engine and the
  original `GREEN_E2_ADAPTIVE` formal candidate. Later optimization retained
  it as a comparison baseline and added `GREEN_HOTSPOT_PARTIAL`.
- `outputs/README.md`: generated-output ledger. It marks `outputs/problem1/`
  as the formal Problem 1 result and separates audit/experiment folders.
- `.learnings/`: local self-improvement notes for tool errors and reusable
  lessons. These are ignored by git and are not solver input data.
- `green_logistics/`: Python package for the solver implementation.
- `green_logistics/data_processing/`: standalone data-processing package. Start
  future sub-dialogues by reading `green_logistics/data_processing/README.md`.
- `tests/`: pytest-based unit tests. Each core module should get tests before
  production code is written.

## Data Files

The local data attachments are currently stored in the project root:

- `订单信息.xlsx`
- `客户坐标信息.xlsx`
- `距离矩阵.xlsx`
- `时间窗.xlsx`

The loader also supports common English names such as `orders.xlsx`,
`coordinates.xlsx`, `distance_matrix.xlsx`, and `time_windows.xlsx` if a future
cleanup moves the files into a `data/` directory.

## Current Implementation Status

The implemented foundation now includes:

1. Data processing: load and validate all four data files, aggregate 2169 orders
   into 88 active customers, mark green-zone customers, and split oversized
   demand into 148 virtual service nodes.
2. `green_logistics/travel_time.py`: time-dependent ETA with speed-period
   segmentation and FIFO-oriented integration.
3. `green_logistics/cost.py`: Jensen-corrected expected energy, load
   adjustment, carbon cost, and soft time-window penalties.
4. `green_logistics/solution.py`: route/trip evaluation, capacity checks,
   customer-ID distance lookup, and solution coverage checks.
5. `green_logistics/metrics.py`: service-quality diagnostics and search-score
   helpers for late stops, maximum lateness, and cross-midnight returns.
6. `green_logistics/scheduler.py` and `green_logistics/trips.py`: C-lite
   physical-vehicle scheduling, scheduling scenario knobs, and lightweight trip
   descriptors for diagnostics and future policy logic.
7. `green_logistics/initial_solution.py`, `green_logistics/operators.py`,
   `green_logistics/scheduler_local_search.py`, and `green_logistics/alns.py`:
   feasible construction, true-lateness ALNS operators, scheduler-level
   residual-lateness rescue, and search-score-guided ALNS.
8. `green_logistics/diagnostics.py` and `green_logistics/policies.py`: residual
   lateness diagnostics, green-zone capacity reports, Problem 2 conflict
   precheck, and policy evaluator hooks.
9. `green_logistics/output.py`, `problems/problem1.py`, and
   `problems/experiments/problem1_convergence.py`: Problem 1 CSV/JSON exports,
   service-quality summaries, paper-ready plots, and convergence experiments.

Use the data layer through:

```python
from green_logistics.data_processing import load_problem_data

data = load_problem_data(".")
```

The current Problem 1 runner is:

```powershell
python problems/problem1.py --iterations 40 --remove-count 8 --seed 20260424 --output-dir outputs/problem1
```

Implementation note: `Route` means one depot-to-depot trip. Trips are assigned
sequentially to physical vehicles, and fleet limits are checked against physical
vehicle counts.

Latest Problem 1 cost-primary run (`2026-04-25`, 40 ALNS iterations):
total cost `48644.68`, fixed cost `17200.00`, time-window penalty `933.53`,
116 trips, physical vehicles `{'E1': 10, 'F1': 33}`, late stops `4`, maximum
lateness `31.60` min, and cross-midnight returns `0`.

Problem 1 closeout documentation is in
`docs/results/problem1_static_scheduling_summary.md`. The formal generated
answer remains `outputs/problem1/`; other output folders are audit or
experiment records as described in `outputs/README.md`.

The solver still reports service-quality diagnostics, but the formal Problem 1
answer is selected by official total delivery cost. Soft time windows mean a
small number of late stops can be optimal after their penalties are included in
the objective.

Problem 2 route design is now recorded in
`docs/design/problem2_green_zone_policy_roadmap.md`. The approved direction is
to keep the official total-cost objective, treat the green-zone fuel restriction
as a hard feasibility gate, and build an independent `Problem2Engine` rather
than folding Problem 2 into `problems/problem1.py`. The formal candidate set is
now `DEFAULT_SPLIT`, `GREEN_E2_ADAPTIVE`, and `GREEN_HOTSPOT_PARTIAL`. Full
green E2 splitting is retained as a comparison baseline, while the formal
recommendation currently comes from default-split scheduling with a search-only
EV reservation score.

The current formal Problem 2 result is in `outputs/problem2/` and summarized in
`docs/results/problem2_green_zone_policy_summary.md`. The full paper-writing
closeout is in `docs/results/problem2_modeling_and_solution_closeout.md`. It
recommends `DEFAULT_SPLIT` with total cost `49239.78`, policy conflicts `0`,
complete coverage, and capacity feasibility. The previous `49888.84` result is
backed up in `outputs/problem2_previous_49888_20260425/`. The formal command is:

```powershell
python problems/problem2.py --iterations 40 --remove-count 16 --seed 20260427 --use-ev-reservation --ev-reservation-penalty 250 --output-dir outputs/problem2
```

Problem 2 is now closed for the current modeling round. The service-quality
sensitivity case `policy operators + EV reservation p500` is preserved in
`outputs/problem2_experiments/formal_screen_policy_ev_p500/`: total cost
`50770.72`, policy conflicts `0`, 2 late stops, and max lateness `5.93` min.
It is useful for paper discussion, but the official answer remains the lower
cost `DEFAULT_SPLIT` solution. Follow-up work should move to Problem 3 while
reusing the Problem 2 engine, scheduler, policy evaluator, diagnostics, and
experiment-ledger interfaces.
