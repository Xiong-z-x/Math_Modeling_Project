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
python problems/problem2.py --iterations 40 --remove-count 16 --seed 20260427 --use-ev-reservation --ev-reservation-penalty 250 --output-dir outputs/problem2
```

Key result: recommended variant `DEFAULT_SPLIT`, total cost `49239.78`, policy
conflicts `0`, complete service coverage, capacity feasible, 115 trips,
physical vehicles `{'E1': 10, 'F1': 35}`, 12 late stops, and 0 cross-midnight
returns. `GREEN_E2_ADAPTIVE` and `GREEN_HOTSPOT_PARTIAL` are retained as formal
candidate comparisons, but neither is recommended because their total costs are
higher.

## Audit And Experiment Outputs

| Path | Status | Use |
| --- | --- | --- |
| `outputs/problem1_baseline_quality_48644/` | audit backup | Preserved rerun of the same lower-cost 4-late baseline |
| `outputs/problem1_cost_100_trial/` | convergence check | Same seed, 100-iteration trial; no lower-cost solution found |
| `outputs/problem2_return1440_trial/` | scenario check | Problem 2 trial with a 24:00 return-limit scenario knob; not part of the official Problem 2 objective |
| `outputs/problem2_previous_49888_20260425/` | audit backup | Previous formal Problem 2 result before EV-reservation optimization; total cost `49888.84` |
| `outputs/problem2_experiments/` | experiment ledger | Parameter and operator screening outputs; not formal unless promoted; `formal_screen_policy_ev_p500/` is retained as the service-quality sensitivity case with total cost `50770.72`, 2 late stops, and max late `5.93` min |
| `outputs/experiments/problem1_convergence_smoke/` | smoke experiment | Small convergence-script output, not a paper result |

These folders should not be cited as the main Problem 1 or Problem 2 answer
unless the paper explicitly presents them as sensitivity, convergence, or audit
evidence.

## Cleaned Temporary Outputs

The following Problem 2 folders were intermediate smoke/candidate runs and have
been removed from the working tree to avoid confusing later sessions:

- `outputs/problem2_smoke/`
- `outputs/problem2_candidate_seed37_r16/`
- `outputs/problem2_ev_reservation_p250/`
- `outputs/problem2_ev_reservation_p250_full/`

The formal Problem 2 result is only `outputs/problem2/` unless a future
optimization session explicitly promotes a new run after documenting and
verifying it.
