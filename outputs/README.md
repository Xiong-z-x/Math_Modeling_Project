# Outputs Directory

This directory contains generated solver outputs. The official Problem 1 answer
is the cost-primary run in `outputs/problem1/`.

## Formal Result

| Path | Status | Use |
| --- | --- | --- |
| `outputs/problem1/` | formal | Official Problem 1 result for paper writing and downstream handoff |

The formal run was generated with:

```powershell
python problems/problem1.py --iterations 40 --remove-count 8 --seed 20260424 --output-dir outputs/problem1
```

Key result: total cost `48644.68`, 116 trips, physical vehicles
`{'E1': 10, 'F1': 33}`, complete service coverage, capacity feasible, 4 late
stops, and 0 cross-midnight returns.

## Audit And Experiment Outputs

| Path | Status | Use |
| --- | --- | --- |
| `outputs/problem1_baseline_quality_48644/` | audit backup | Preserved rerun of the same lower-cost 4-late baseline |
| `outputs/problem1_cost_100_trial/` | convergence check | Same seed, 100-iteration trial; no lower-cost solution found |
| `outputs/experiments/problem1_convergence_smoke/` | smoke experiment | Small convergence-script output, not a paper result |

These folders should not be cited as the main Problem 1 answer unless the paper
explicitly presents them as sensitivity, convergence, or audit evidence.
