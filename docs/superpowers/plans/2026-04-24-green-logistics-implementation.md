# Green Logistics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested Python solver pipeline for the green logistics TD-HFVRPTW task, starting with the data layer.

**Architecture:** The solver uses explicit dataclasses, deterministic expected-speed time propagation, segment-integrated expected energy costs, and an ALNS search layer. The data layer creates virtual service nodes while preserving original customer IDs for distance-matrix access.

**Tech Stack:** Python 3, pandas, numpy, openpyxl, pytest.

---

## Purpose
This plan documents the implementation sequence and the responsibility of each
module. It is a handoff file for future coding windows.

Before starting any new implementation window, read `项目文件导航.md` and update
it when creating, moving, deleting, or renaming project files.

## File Structure
- `green_logistics/constants.py`: central constants and vehicle definitions.
- `green_logistics/data_processing/loader.py`: data discovery, validation, aggregation,
  green-zone tagging, and virtual service-node generation.
- `green_logistics/data_processing/README.md`: durable handoff document for
  data-processing assumptions and verified facts.
- `green_logistics/data_loader.py`: compatibility wrapper for older imports.
- `tests/test_data_loader.py`: regression tests for known data facts.
- `green_logistics/travel_time.py`: time-dependent ETA by segment integration.
- `green_logistics/cost.py`: expected energy, carbon, and penalty cost formulas.
- `green_logistics/solution.py`: route and solution dataclasses.
- `green_logistics/initial_solution.py`: feasible seed solution.
- `green_logistics/alns.py`: adaptive large-neighborhood search.
- `green_logistics/output.py`: result tables and paper-ready summaries.

### Task 1: Data Layer
- [x] Write pytest tests for known data facts: 88 active customers, 12 active
      green-zone customers, 36 split customers, and 148 virtual service nodes.
- [x] Run tests and confirm they fail because `green_logistics.data_loader` does
      not exist yet.
- [x] Implement constants and loader dataclasses.
- [x] Implement file discovery for both Chinese and English filenames.
- [x] Implement aggregation, validation, green-zone tagging, and splitting.
- [x] Reorganize the data layer into `green_logistics/data_processing/`.
- [x] Run `pytest tests/test_data_loader.py -v` and keep it green.

### Task 2: Travel Time
- [x] Test period lookup and cross-period ETA on small deterministic distances.
- [x] Implement segment integration using absolute minutes from 0:00.
- [x] Test FIFO monotonicity on sampled departures.

### Task 3: Cost
- [x] Test Jensen-corrected expected FPK/EPK values for all speed regimes.
- [x] Test load-factor interpolation for fuel and EV vehicles.
- [x] Implement segment-integrated energy and carbon cost.

### Task 4: Solver Core
- [x] Test route feasibility checks on small synthetic routes.
- [x] Implement route evaluation, initial construction, and ALNS operators.
- [x] Run focused solver smoke tests before long optimization runs.

## Execution Summary
- Problem 1 solver implemented through `problems/problem1.py`, with tables and
  figures generated under `outputs/problem1/`.
- Latest service-quality 40-iteration run: total cost `48644.68`, 116 trips,
  10 E1 and 33 F1 physical vehicles, complete service coverage, capacity
  feasible, 4 late stops, max lateness `31.60` min, and no cross-midnight
  returns.
- Modeling caveat: the official soft time-window cost is unchanged, but ALNS now
  uses a separate service-quality search score to avoid the earlier
  cost-priority solution's systematic lateness.
