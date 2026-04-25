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
6. `green_logistics/initial_solution.py`, `green_logistics/operators.py`, and
   `green_logistics/alns.py`: feasible construction, service-quality-aware
   scheduling, true-lateness ALNS operators, and search-score-guided ALNS.
7. `green_logistics/output.py` and `problems/problem1.py`: Problem 1 CSV/JSON
   exports, service-quality summaries, and paper-ready plots under
   `outputs/problem1/`.

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

Latest Problem 1 service-quality run (`2026-04-25`, 40 ALNS iterations):
total cost `48644.68`, fixed cost `17200.00`, time-window penalty `933.53`,
116 trips, physical vehicles `{'E1': 10, 'F1': 33}`, late stops `4`, maximum
lateness `31.60` min, and cross-midnight returns `0`.
