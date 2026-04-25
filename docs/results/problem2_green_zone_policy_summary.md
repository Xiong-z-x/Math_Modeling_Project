# Problem 2 Green-Zone Policy Result Summary

This is the compact result summary. The full paper-writing closeout, including
assumptions, symbols, formulas, constraints, algorithm design, visualization
guidance, and the reserved Problem 3 interface, is
`docs/results/problem2_modeling_and_solution_closeout.md`.

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

Three candidate mainlines were solved:

- `DEFAULT_SPLIT`: keeps the first-question service-node granularity
  (`148` service nodes, `19` green service nodes) and adds the hard green-zone
  policy.
- `GREEN_E2_ADAPTIVE`: keeps non-green splits unchanged, but splits green
  customers by E2 capacity (`166` service nodes, `37` green service nodes) to
  test whether small EV cooperation improves the policy setting.
- `GREEN_HOTSPOT_PARTIAL`: keeps most default nodes unchanged, but creates a
  small number of E2-sized chunks for high-risk green customers (`153` service
  nodes, `24` green service nodes). This is a bounded alternative to the full
  green-zone E2 split.

The recommendation rule is strict: a candidate must have complete service-node
coverage, capacity-feasible trips, and zero policy conflicts. Among feasible
candidates, the lowest official total cost is recommended.

## Formal Recommendation

Recommended variant: `DEFAULT_SPLIT`

Formal command:

```powershell
python problems/problem2.py --iterations 40 --remove-count 16 --seed 20260427 --use-ev-reservation --ev-reservation-penalty 250 --output-dir outputs/problem2
```

Key result:

| Metric | Value |
| --- | ---: |
| Total cost | `49239.78` |
| Fixed cost | `18000.00` |
| Energy cost | `24551.90` |
| Carbon cost | `5301.72` |
| Time-window penalty | `1386.17` |
| Total distance km | `13093.90` |
| Carbon kg | `8156.49` |
| Depot-to-depot trips | `115` |
| Physical vehicles | `E1:10, F1:35` |
| Policy conflict count | `0` |
| Complete service coverage | `True` |
| Capacity feasible | `True` |
| Late stops | `12` |
| Max late minutes | `129.44` |
| Cross-midnight returns | `0` |

## Variant Comparison

| Variant | Total Cost | Policy Conflicts | Service Nodes | Green Nodes | Physical Vehicles | Late Stops | Max Late |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `DEFAULT_SPLIT` | `49239.78` | `0` | `148` | `19` | `E1:10, F1:35` | `12` | `129.44` |
| `GREEN_E2_ADAPTIVE` | `57504.49` | `0` | `166` | `37` | `E1:10, E2:3, F1:44` | `24` | `253.00` |
| `GREEN_HOTSPOT_PARTIAL` | `52312.11` | `0` | `153` | `24` | `E1:10, E2:1, F1:35` | `22` | `119.21` |

`GREEN_E2_ADAPTIVE` and `GREEN_HOTSPOT_PARTIAL` remain useful comparisons, but
both cost more than the EV-reservation-guided `DEFAULT_SPLIT` recommendation.
The hotspot variant slightly lowers the maximum lateness relative to the new
recommendation, but its higher energy and carbon costs make it worse under the
official objective.

## Comparison With Problem 1

Problem 1 formal cost was `48644.68`. Problem 2's recommended policy-feasible
cost is `49239.78`, an increase of `595.10`. This is consistent with the
modeling logic: under the same service-node granularity, adding a hard policy
constraint should not be expected to reduce the true optimum.

The main cost changes are:

- Fixed cost increases from `17200.00` to `18000.00` because two more physical
  vehicles are used.
- Energy and carbon costs decrease modestly because policy-aware rescheduling
  changes the route mix and distance profile.
- Time-window penalty increases from `933.53` to `1386.17`, reflecting the cost
  of hard green-zone compliance under soft time windows.

## Risk Notes

- The result is heuristic, not a proof of global optimality. The latest
  improvement came from a search-only EV reservation score with penalty `250`;
  a stronger penalty improved lateness but worsened official cost.
- Policy-specific destroy/repair operators were tested as an experimental
  option. In the 40-iteration screened run they produced excellent service
  quality with EV reservation (`2` late stops, max late `5.93` min), but the
  total cost `50770.72` was higher than the formal recommendation, so they are
  not the default official result.
- The previous formal result (`49888.84`) is preserved in
  `outputs/problem2_previous_49888_20260425/`.
- Cross-midnight return is not a formal constraint; it remains a diagnostic
  because the task statement does not specify a 24:00 hard return deadline.

## Output Files

- `outputs/problem2/recommendation.json`
- `outputs/problem2/variant_comparison.csv`
- `outputs/problem2/default_split/`
- `outputs/problem2/green_e2_adaptive/`
- `outputs/problem2/green_hotspot_partial/`
- `docs/results/problem2_modeling_and_solution_closeout.md`
