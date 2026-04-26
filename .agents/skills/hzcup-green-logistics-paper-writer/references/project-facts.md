# Project Facts For Paper Writing

## Problem Identity

Project root: `c:\Math_Modeling_Project`.

Problem: 第十八届“华中杯”大学生数学建模挑战赛 A 题，城市绿色物流配送调度。

Recommended model name:

`TD-HFVRPTW-LD-GZ-DYN`

Meaning: time-dependent heterogeneous-fleet vehicle routing with soft time windows, load-dependent energy, green-zone policy, and dynamic event response.

## Data Facts

| Item | Fact |
| --- | ---: |
| Raw orders | 2169 |
| Coordinate nodes | 99, including depot and 98 customers |
| Active customers | 88 |
| Customers without orders | 10 |
| Total demand weight | 285122.647 kg |
| Total demand volume | 772.431 m3 |
| Customers requiring split | 36 |
| Virtual service nodes | 148 |
| Active green-zone customers | 12 |
| Green-zone virtual service nodes | 19 |
| Depot coordinate | `(20,20)` |
| Green-zone center | `(0,0)` |
| Green-zone radius | `10 km` |
| Service time | `20 min` |

The green zone is determined by Euclidean distance from `(0,0)`, not by the distance matrix. The distance matrix is indexed by original `customer_id`; solver service granularity is `service_node_id`.

## Official Cost Terms

Use only:

\[
C=C_{\mathrm{fixed}}+C_{\mathrm{energy}}+C_{\mathrm{carbon}}+C_{\mathrm{tw}}.
\]

Do not add policy conflict, EV reservation, stability, or route disturbance to official cost. These are feasibility or diagnostic quantities only.

Fixed cost is counted by enabled physical vehicles. One physical vehicle may execute multiple depot-to-depot trips.

## Problem 1 Formal Result

Formal folder: `outputs/problem1/`.

| Metric | Value |
| --- | ---: |
| Total cost | `48644.68` |
| Fixed cost | `17200.00` |
| Energy cost | `25091.79` |
| Carbon cost | `5419.37` |
| Soft-time-window penalty | `933.53` |
| Carbon emission | `8337.49 kg` |
| Route/trip count | `116` |
| Physical vehicle usage | `E1:10, F1:33` |
| Trip usage | `E1:32, F1:84` |
| Late stops / max lateness | `4 / 31.60 min` |
| Coverage/capacity | feasible |

Paper interpretation: Problem 1 is the static no-policy baseline. Residual lateness is allowed by the soft time-window model and is included in the penalty cost.

## Problem 2 Formal Result

Formal recommendation: `DEFAULT_SPLIT`.

Formal folders/files:

- `outputs/problem2/recommendation.json`
- `outputs/problem2/default_split/`
- `outputs/problem2/variant_comparison.csv`

| Metric | Value |
| --- | ---: |
| Total cost | `49239.78` |
| Fixed cost | `18000.00` |
| Energy cost | `24551.90` |
| Carbon cost | `5301.72` |
| Soft-time-window penalty | `1386.17` |
| Carbon emission | `8156.49 kg` |
| Route/trip count | `115` |
| Physical vehicle usage | `E1:10, F1:35` |
| Trip usage | `E1:28, F1:87` |
| Policy conflict count | `0` |
| Late stops / max lateness | `12 / 129.44 min` |

Relative to Problem 1, Problem 2 costs `595.10` more, about `1.22%`, while satisfying green-zone policy with zero conflict.

Service-quality sensitivity output:

- `outputs/problem2_experiments/formal_screen_policy_ev_p500/`
- total cost `50770.72`
- late stops `2`
- max lateness `5.93 min`

Use this only as a sensitivity/service-quality tradeoff, not as the formal recommendation.

## Problem 3 Formal Result

Formal folder: `outputs/problem3/`.

Important boundary: The problem statement gives event types but no official dynamic event records. The four rows are representative scenario assumptions.

| Scenario | Event type | Event time | Dynamic cost | Delta vs P2 | Policy conflicts | Late stops / max lateness | Changed stops |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cancel_future_order_1030` | cancel | `630` | `48711.28` | `-528.51` | `0` | `12 / 129.44` | `1` |
| `new_green_order_1330` | new order | `810` | `49237.36` | `-2.42` | `0` | `12 / 129.44` | `2` |
| `time_window_pull_forward_1500` | time-window change | `900` | `49263.35` | `+23.57` | `0` | `13 / 129.44` | `1` |
| `address_change_proxy_1200` | address change | `720` | `49207.47` | `-32.31` | `0` | `12 / 129.44` | `2` |

All four scenarios pass coverage, capacity, physical vehicle chain, and green policy checks.

## Core Innovation Claims

Use these claims, with evidence:

1. Virtual service-node decomposition makes overloaded customer demand physically serviceable while preserving original customer distance indexing.
2. Time-dependent ETA uses piecewise integration rather than a single average speed.
3. Expected energy uses Jensen correction \(E[v^2]=\mu^2+\sigma^2\), preserving the second-moment effect of speed randomness.
4. Load-dependent energy links route order to energy and carbon costs.
5. Green-zone policy is handled as a hard feasibility guard, separate from official cost.
6. Physical vehicle reuse separates depot-to-depot trips from fixed-cost vehicle counting.
7. Dynamic response freezes executed facts and locked in-transit segments before reoptimizing the future pool.
8. The final result set includes feasibility, sensitivity, and error-analysis evidence, not only a cost table.

## Claims To Avoid

Avoid:

- global optimality;
- zero-carbon EVs;
- road-level green-zone crossing detection;
- official dynamic event data;
- Monte Carlo robustness values unless actually generated;
- 400-iteration/10-seed stability numbers unless backed by project outputs;
- treating Problem 2 service-quality sensitivity as the official recommended result.
