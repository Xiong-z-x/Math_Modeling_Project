# Problem 1 Static Scheduling Summary

## Cost

- Initial total cost: `52245.49`
- Best total cost: `48644.68`
- Improvement: `3600.81`
- Fixed cost: `17200.00`
- Energy cost: `25091.79`
- Carbon cost: `5419.37`
- Time-window penalty: `933.53`

## Service Quality

- Late stops: `4`
- Total late minutes: `77.42`
- Max late minutes: `31.60`
- Routes returning after midnight: `0`
- Max return minute: `1428.52`
- Max trips per physical vehicle: `5`

## Feasibility

- Complete service-node coverage: `True`
- Capacity feasible trips: `True`
- Missing service nodes: `[]`
- Duplicate service nodes: `[]`

## Operations

- Depot-to-depot trips: `116`
- Physical vehicle usage: `{'E1': 10, 'F1': 33}`
- Trip usage by type: `{'E1': 32, 'F1': 84}`
- Total distance km: `13384.29`
- Carbon kg: `8337.49`

## Modeling Note

Routes in the code are depot-to-depot trips. Trips are assigned to physical vehicles sequentially, so fleet limits are checked against physical vehicles, not trip count. This is necessary because the current 148 virtual service nodes include more heavy nodes than the one-trip large-vehicle fleet can cover.

## Files

- `alns_history_csv`: `outputs\problem1\alns_history.csv`
- `cost_breakdown_png`: `outputs\problem1\cost_breakdown.png`
- `cost_summary_csv`: `outputs\problem1\cost_summary.csv`
- `quality_summary_csv`: `outputs\problem1\quality_summary.csv`
- `route_map_png`: `outputs\problem1\route_map.png`
- `route_summary_csv`: `outputs\problem1\route_summary.csv`
- `stop_schedule_csv`: `outputs\problem1\stop_schedule.csv`
- `summary_json`: `outputs\problem1\summary.json`
- `time_windows_png`: `outputs\problem1\time_windows.png`
- `vehicle_usage_csv`: `outputs\problem1\vehicle_usage.csv`
- `vehicle_usage_png`: `outputs\problem1\vehicle_usage.png`
