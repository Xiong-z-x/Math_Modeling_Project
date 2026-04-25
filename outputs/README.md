# Outputs Directory

This directory contains generated solver outputs. The official Problem 1 answer
is the cost-primary run in `outputs/problem1/`. The official Problem 2 answer is
the policy-feasible, cost-primary recommendation in `outputs/problem2/`.

## Formal Result

| Path | Status | Use |
| --- | --- | --- |
| `outputs/problem1/` | formal | Official Problem 1 result for paper writing and downstream handoff |
| `outputs/problem2/` | formal | Official Problem 2 result under the green-zone fuel restriction |

The formal run was generated with:

```powershell
python problems/problem1.py --iterations 40 --remove-count 8 --seed 20260424 --output-dir outputs/problem1
```

Key result: total cost `48644.68`, 116 trips, physical vehicles
`{'E1': 10, 'F1': 33}`, complete service coverage, capacity feasible, 4 late
stops, and 0 cross-midnight returns.

The formal Problem 2 run was generated with:

```powershell
python problems/problem2.py --iterations 40 --remove-count 16 --seed 20260427 --output-dir outputs/problem2
```

Key result: recommended variant `DEFAULT_SPLIT`, total cost `49888.84`, policy
conflicts `0`, complete service coverage, capacity feasible, 116 trips,
physical vehicles `{'E1': 10, 'E2': 1, 'F1': 35}`, 12 late stops, and 0
cross-midnight returns. `GREEN_E2_ADAPTIVE` is retained as a formal candidate
comparison, but it is not recommended because its total cost is higher.

## Audit And Experiment Outputs

| Path | Status | Use |
| --- | --- | --- |
| `outputs/problem1_baseline_quality_48644/` | audit backup | Preserved rerun of the same lower-cost 4-late baseline |
| `outputs/problem1_cost_100_trial/` | convergence check | Same seed, 100-iteration trial; no lower-cost solution found |
| `outputs/problem2_return1440_trial/` | scenario check | Problem 2 trial with a 24:00 return-limit scenario knob; not part of the official Problem 2 objective |
| `outputs/experiments/problem1_convergence_smoke/` | smoke experiment | Small convergence-script output, not a paper result |

These folders should not be cited as the main Problem 1 or Problem 2 answer
unless the paper explicitly presents them as sensitivity, convergence, or audit
evidence.

## Cleaned Temporary Outputs

The following Problem 2 folders were intermediate smoke/candidate runs and have
been removed from the working tree to avoid confusing later sessions:

- `outputs/problem2_smoke/`
- `outputs/problem2_candidate_seed37_r16/`

The formal Problem 2 result is only `outputs/problem2/` unless a future
optimization session explicitly promotes a new run after documenting and
verifying it.
