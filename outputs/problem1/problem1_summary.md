# Problem 1 Static Scheduling Summary

## Cost

- Initial total cost: `55322.71`
- Best total cost: `51870.90`
- Improvement: `3451.80`
- Fixed cost: `14800.00`
- Energy cost: `23017.23`
- Carbon cost: `4953.10`
- Time-window penalty: `9100.58`

## Feasibility

- Complete service-node coverage: `True`
- Capacity feasible trips: `True`
- Missing service nodes: `[]`
- Duplicate service nodes: `[]`

## Operations

- Depot-to-depot trips: `115`
- Physical vehicle usage: `{'E1': 10, 'F1': 27}`
- Trip usage by type: `{'E1': 39, 'F1': 76}`
- Total distance km: `13342.28`
- Carbon kg: `7620.15`

## Modeling Note

Routes in the code are depot-to-depot trips. Trips are assigned to physical vehicles sequentially, so fleet limits are checked against physical vehicles, not trip count. This is necessary because the current 148 virtual service nodes include more heavy nodes than the one-trip large-vehicle fleet can cover.

## Files

- `alns_history_csv`: `outputs\problem1\alns_history.csv`
- `cost_breakdown_png`: `outputs\problem1\cost_breakdown.png`
- `cost_summary_csv`: `outputs\problem1\cost_summary.csv`
- `route_map_png`: `outputs\problem1\route_map.png`
- `route_summary_csv`: `outputs\problem1\route_summary.csv`
- `stop_schedule_csv`: `outputs\problem1\stop_schedule.csv`
- `summary_json`: `outputs\problem1\summary.json`
- `time_windows_png`: `outputs\problem1\time_windows.png`
- `vehicle_usage_csv`: `outputs\problem1\vehicle_usage.csv`
- `vehicle_usage_png`: `outputs\problem1\vehicle_usage.png`
