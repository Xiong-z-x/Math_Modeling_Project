# TD-HFVRPTW Green Logistics Plan

## Purpose
This file is the persistent task plan for the project. It tracks phases,
decisions, and next actions so future windows can resume without rereading all
materials.

## Goal
Build an executable and explainable Python solution for Problem 1 of the Huazhong Cup green logistics scheduling task, while keeping the design extensible for green-zone restrictions and dynamic rescheduling.

## Current Scope
This session is responsible for:
- Reading and auditing the local problem materials.
- Fixing the modeling direction before implementation.
- Defining the data-processing layer and algorithm architecture.
- Preparing durable notes for follow-up implementation sessions.

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
- `green_logistics/initial_solution.py`: feasible construction heuristic.
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
| `green_logistics/operators.py` / `green_logistics/alns.py` | complete | `pytest tests/test_alns_smoke.py -v` |
| `green_logistics/output.py` / `problems/problem1.py` | complete | `pytest tests/test_output.py -v`; real run in `outputs/problem1/` |

Latest Problem 1 service-quality result:

- Command: `python problems/problem1.py --iterations 40 --remove-count 8 --seed 20260424 --output-dir outputs/problem1`
- Total cost: `48644.68`
- Time-window penalty: `933.53`
- Trips: `116`
- Physical vehicle usage: `{'E1': 10, 'F1': 33}`
- Late stops: `4`
- Max lateness: `31.60 min`
- Cross-midnight returns: `0`
