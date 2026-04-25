# Problem 2 Green-Zone Policy Result Summary

## Policy Interpretation

Problem 2 keeps the official objective unchanged:

```text
fixed_cost + energy_cost + carbon_cost + soft_time_window_penalty
```

The green-zone restriction is a hard feasibility constraint: fuel vehicles may
not serve green-zone customers during `[480, 960)`, i.e. 08:00-16:00. Time
windows remain soft and are priced through the official penalty term. The
available data do not include road geometry, so the enforceable policy proxy is
fuel-vehicle service at green-zone customer stops; path traversal through the
green circle is not modeled as a hard constraint.

The problem statement does not impose a 24:00 hard return rule. Cross-midnight
returns are therefore reported as diagnostics, not as a formal feasibility
filter. The selected formal result has no cross-midnight return.

## Candidate Mainlines

Two candidate mainlines were solved:

- `DEFAULT_SPLIT`: keeps the first-question service-node granularity
  (`148` service nodes, `19` green service nodes) and adds the hard green-zone
  policy.
- `GREEN_E2_ADAPTIVE`: keeps non-green splits unchanged, but splits green
  customers by E2 capacity (`166` service nodes, `37` green service nodes) to
  test whether small EV cooperation improves the policy setting.

The recommendation rule is strict: a candidate must have complete service-node
coverage, capacity-feasible trips, and zero policy conflicts. Among feasible
candidates, the lowest official total cost is recommended.

## Formal Recommendation

Recommended variant: `DEFAULT_SPLIT`

Formal command:

```powershell
python problems/problem2.py --iterations 40 --remove-count 16 --seed 20260427 --output-dir outputs/problem2
```

Key result:

| Metric | Value |
| --- | ---: |
| Total cost | `49888.84` |
| Fixed cost | `18400.00` |
| Energy cost | `24688.13` |
| Carbon cost | `5327.28` |
| Time-window penalty | `1473.43` |
| Total distance km | `13377.44` |
| Carbon kg | `8195.81` |
| Depot-to-depot trips | `116` |
| Physical vehicles | `E1:10, E2:1, F1:35` |
| Policy conflict count | `0` |
| Complete service coverage | `True` |
| Capacity feasible | `True` |
| Late stops | `12` |
| Max late minutes | `124.92` |
| Cross-midnight returns | `0` |

## Variant Comparison

| Variant | Total Cost | Policy Conflicts | Service Nodes | Green Nodes | Physical Vehicles | Late Stops | Max Late |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `DEFAULT_SPLIT` | `49888.84` | `0` | `148` | `19` | `E1:10, E2:1, F1:35` | `12` | `124.92` |
| `GREEN_E2_ADAPTIVE` | `57109.67` | `0` | `166` | `37` | `E1:10, E2:3, F1:42` | `28` | `253.00` |

`GREEN_E2_ADAPTIVE` uses fewer depot-to-depot trips and a finer green-zone
service granularity, but in the formal run it uses more physical vehicles and
has much higher fixed and time-window penalty costs. Because the official goal
is minimum total delivery cost, it is not the recommended solution.

## Comparison With Problem 1

Problem 1 formal cost was `48644.68`. Problem 2's recommended policy-feasible
cost is `49888.84`, an increase of `1244.16`. This is consistent with the
modeling logic: under the same service-node granularity, adding a hard policy
constraint should not be expected to reduce the true optimum.

The main cost changes are:

- Fixed cost increases from `17200.00` to `18400.00` because one E2 and two more
  F1 physical vehicles are used.
- Energy and carbon costs decrease modestly because policy-aware rescheduling
  changes the route mix and distance profile.
- Time-window penalty increases from `933.53` to `1473.43`, reflecting the cost
  of hard green-zone compliance under soft time windows.

## Risk Notes

- The result is heuristic, not a proof of global optimality. A small multi-seed
  search found a better zero-conflict solution at `seed=20260427` than the
  original `seed=20260424`.
- Policy-specific destroy/repair operators were tested as an experimental
  option, but the first implementation worsened cost. They remain useful as a
  research direction, not as the formal default.
- Cross-midnight return is not a formal constraint; it remains a diagnostic
  because the task statement does not specify a 24:00 hard return deadline.

## Output Files

- `outputs/problem2/recommendation.json`
- `outputs/problem2/variant_comparison.csv`
- `outputs/problem2/default_split/`
- `outputs/problem2/green_e2_adaptive/`
