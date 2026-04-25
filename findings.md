# Findings

## Purpose
This file stores verified facts and audit notes from the problem statement,
supplement, data files, and reference solutions. It is evidence, not executable
solver code.

## Local Materials
- `A题：城市绿色物流配送调度.pdf` is now readable and confirms the original
  problem background, five vehicle classes, objective terms, U-shaped energy
  formulas, carbon parameters, and three subproblems.
- `关于第十八届“华中杯”大学生数学建模挑战赛A题的补充说明.pdf` is readable.
- The earlier Baidu-share printout PDF has been replaced by the readable
  original problem PDF.
- `参考思路/claude-华中杯A题_技术实现规范.md` is readable and useful as a technical draft.
- `参考思路/claude-华中杯A题_技术路线_Codex实施手册.docx` is readable and
  incorporates the supplement. It is useful, but still must be audited against
  the data.
- `参考思路/gpt数模思路.pdf` and `参考思路/gemini数模思路.pdf` have broken PDF text extraction. Their table-of-contents/numeric fragments are weak evidence only unless visually reviewed later.

## Supplement Constraints
- Green delivery zone: circle centered at city center `(0, 0)`, radius `10 km`.
- The city center `(0, 0)` is not the depot. The depot is data/distance-matrix
  node `0`; the coordinate file records it at `(20, 20)`. Problem 2 policy
  checks must use customer green-zone membership and treat depot departure/return
  as policy-exempt.
- Speed distribution by period:
  - Congested: 08:00-09:00 and 11:30-13:00, `v(t) ~ N(9.8, 4.7^2)` or table notation equivalent.
  - Smooth: 09:00-10:00 and 13:00-15:00, `v(t) ~ N(55.3, 0.1^2)`.
  - Normal: 10:00-11:30 and 15:00-17:00, `v(t) ~ N(35.4, 5.2^2)`.
- The supplement gives no explicit period after 17:00. A defensible implementation should either assume normal speed after 17:00 or make that assumption configurable and report it.

## Excel Data Facts
- Attachments are four `.xlsx` files:
  - Orders: 2169 rows, columns `订单编号, 重量, 体积, 目标客户编号`.
  - Coordinates: 99 rows, depot plus 98 customers.
  - Time windows: 98 rows.
  - Distance matrix: 99 x 99 after using first column as index, symmetric.
- Depot coordinate is `(20.0, 20.0)`.
- Green-zone customers by coordinate radius are IDs `1..15`; active green-zone customers are `2..13`.
- Active customers with orders: 88.
- No-demand customers: `[1, 14, 15, 17, 18, 20, 21, 22, 23, 96]`.
- Total demand: `285122.647 kg`, `772.431 m3`.
- Customers over 3000 kg: 36.
- If split by largest vehicle capacity `(3000 kg, 15 m3)`, virtual service nodes are 148; max split count is 5.
- Customers needing split service under `(3000 kg, 15 m3)` are:
  `[6, 7, 8, 10, 27, 28, 31, 36, 39, 42, 43, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61, 62, 63, 64, 65, 68, 70, 71, 74, 75]`.
- Time-window widths range from 48 to 90 minutes, average about 72.15 minutes.
- A single raw order can exceed the largest vehicle capacity: max single-order weight is about `5987.05 kg`. Therefore, strict indivisible-order bin packing is infeasible for this dataset. Demand splitting must be interpreted as divisible goods, or those oversized orders must be split before route construction.

## Reference Audit Notes
- The Claude draft correctly emphasizes multi-trip splitting, segment-integrated travel time, and strict virtual-node/customer-ID mapping.
- The Claude draft has a probable typo for smooth speed: it uses `53.3` in code snippets, while the supplement says `55.3`. Use `55.3`.
- The new Claude `.docx` correctly states active green-zone customers are 12 in
  the main text. If any downstream note says 9, that is inconsistent with the
  data and should be ignored.
- Splitting only by weight is insufficient in principle. Use `ceil(max(weight/max_weight, volume/max_volume))`, based on the largest admissible single-trip capacity for Problem 1 preprocessing, then validate route-specific vehicle capacity during insertion.
- Order-level first-fit bin packing is not suitable as the primary splitter because at least one raw order already exceeds all vehicle capacities.
- Cost over a trip should integrate energy over speed segments, not just use the departure speed for the whole arc, because the energy formulas are U-shaped functions of speed and speed changes inside an arc.
- Arrival-time penalties should use arrival time. Waiting until the early bound affects service start and downstream arrival times.
- With the current 148 virtual service nodes, 114 nodes have demand weight over
  `1500 kg`. These nodes can only be served by `F1` or `E1`, but the physical
  fleet contains only `70` such vehicles. Therefore a strict one-route-per-
  physical-vehicle interpretation is infeasible under the existing data layer.
  Problem 1 implementation should treat a `Route` as a depot-to-depot trip and
  then assign trips sequentially to physical vehicles of the same type, counting
  unique physical vehicles against fleet limits. This is also consistent with
  the reference specification's "Multi-Trip" framing.
- The first cost-priority Problem 1 result had systematic lateness: `84` late
  stops, maximum lateness about `286` minutes, and `8` cross-midnight returns.
  The 2026-04-25 service-quality optimization keeps the official soft
  time-window cost unchanged, but uses a separate heuristic search score to
  guide ALNS and physical scheduling. The first improved 40-iteration result
  had `4` late stops, maximum lateness `31.60` minutes, and `0` cross-midnight
  returns, while preserving complete coverage and capacity feasibility. This
  lower-cost comparison baseline is preserved in
  `outputs/problem1_baseline_quality_48644/`.
- The second-round C-lite run extracted physical scheduling into
  `green_logistics/scheduler.py` and corrected formal best-solution selection
  to use the official `total_cost`, not a zero-lateness surrogate. The formal
  output in `outputs/problem1/` is therefore the lower-cost 4-late-stop
  solution: total cost `48644.68`, fixed cost `17200.00`, time-window penalty
  `933.53`, `116` trips, physical vehicle usage `{'E1': 10, 'F1': 33}`, and
  `0` cross-midnight returns.
- Residual-lateness diagnosis on the 4-late baseline classified the stops as:
  one Type A direct-infeasible stop, two Type B multi-trip cascade stops, and
  one Type C route-order/composition stop. This justified strengthening
  scheduler service-quality preference instead of adding a default 22:00 hard
  return constraint.
- The Problem 2 precheck on the cost-primary Problem 1 solution reports `19`
  green-zone service nodes with total green-zone demand `35970.65 kg` and
  `103.96 m3`. One-trip EV capacity is `48750 kg` and `277.5 m3`, but only
  `4` green nodes fit E2; `15` need E1-class capacity. The first-question
  solution has fuel-vehicle green-zone service conflicts during 08:00-16:00,
  so Problem 2 must actively reassign or retime those stops.
- The three new Problem 2 reference files in `第二问参考思路/` were audited on
  2026-04-25. The strongest combined route is an independent `Problem2Engine`
  on the current C-lite architecture: hard policy gate, green-zone conflict
  removal, EV-first repair, scheduler-level retime/reassign, and formal
  comparison between `DEFAULT_SPLIT` and `GREEN_E2_ADAPTIVE`. A full
  trip-pool/two-stage rewrite remains a later quality upgrade if the
  Problem2Engine route cannot reach a good cost.
- Gemini's suggestion to split green-zone customers by E2 capacity is a real
  insight and has been promoted to a formal Problem 2 candidate mainline:
  with the current 3000 kg split, only `4` of `19` green service nodes fit E2;
  if green customers are split by E2 capacity, green service nodes increase to
  exactly `37` and total service nodes increase from `148` to `166`. This
  changes the service-node set, so it must be implemented through an explicit
  `GREEN_E2_ADAPTIVE` variant rather than by changing default
  `load_problem_data`. For fair interpretation, compare it with both the
  default-split Problem 2 candidate and an optional no-policy adaptive baseline.
- For Problem 2, policy violation should not be added to the official objective
  as a fifth cost component. The official objective remains fixed + energy +
  carbon + soft time-window penalty; green-zone fuel restriction is a hard
  feasibility condition. A large policy penalty may be used only inside
  heuristic search scores to steer candidates away from infeasible regions.
- Boundary convention selected for implementation: treat the restricted window
  as `[480, 960)`, so a fuel vehicle arriving at a green-zone customer exactly
  at `16:00` is considered outside the restriction. Exact-boundary cases are
  rare but should be fixed in tests.
- Under the same service-node set and exact optimization, adding the Problem 2
  green-zone hard constraint cannot improve the true optimum relative to
  Problem 1. However, the current solver is heuristic; if a future Problem 2 run
  finds a lower total cost than the current Problem 1 baseline, treat it first
  as evidence that the heuristic found a different/better feasible region, not
  as proof that the policy itself reduces cost.
- The formal Problem 2 result generated on 2026-04-25 uses
  `python problems/problem2.py --iterations 40 --remove-count 16 --seed 20260427 --output-dir outputs/problem2`.
  The recommended variant is `DEFAULT_SPLIT`: total cost `49888.84`, fixed
  `18400.00`, energy `24688.13`, carbon `5327.28`, time-window penalty
  `1473.43`, total distance `13377.44 km`, carbon `8195.81 kg`, 116 trips,
  physical vehicles `{'E1': 10, 'E2': 1, 'F1': 35}`, complete coverage,
  capacity feasible, and policy conflicts `0`.
- `GREEN_E2_ADAPTIVE` remains a valid formal candidate comparison, but the
  current run costs `57109.67`, so it is not recommended under the official
  cost-minimization objective. Its better late-stop metrics do not override the
  objective.
- A 24:00 return limit is not part of the official Problem 2 feasibility model.
  Cross-midnight returns should be reported as a diagnostic or scenario knob,
  not used as a formal selection criterion unless the user explicitly asks for
  that scenario.

## Tooling Notes
- PowerShell inline Python can corrupt Chinese path literals. Prefer filesystem enumeration (`Path.glob`) or explicit UTF-8 handling.
- Do not batch many long ALNS candidate runs behind one buffered command. Run
  expensive seeds one at a time or with unbuffered short batches so timeouts do
  not hide useful partial results.
- During the 2026-04-25 subdialogue-three intake, the current Problem 2 maximum
  lateness was traced to EV resource cascade rather than direct infeasibility.
  Customer `8` / service node `13` on route `T0021` uses `E1-009`, arrives at
  `831.92` against latest `707`, and is late by `124.92 min`; a direct or fresh
  route can serve it without lateness. The immediate predecessor on the same
  physical vehicle is a non-green customer `42` trip that appears feasible for
  F1-class service, so future optimization should test EV reservation and
  blocking-chain neighborhoods.
- The three second-round Problem 2 reference files agree on one practical
  point: full green-zone E2 splitting is too blunt for the current objective.
  The better near-term path is a bounded hotspot split only after diagnostics,
  parameter sweeps, and EV-cascade scheduling fixes have been tried.
- Current `--use-policy-operators` should not be treated as the default path:
  it targets fuel/green conflicts and post-16 fuel repair more than the
  observed EV multi-trip bottleneck. Any policy-operator rewrite should remove
  or retime blocking predecessor trips on scarce EV chains.
- The 2026-04-26 final Problem 2 route calibration changes the status of
  `GREEN_E2_ADAPTIVE`: it remains a useful comparison baseline, but should no
  longer be treated as the next optimization mainline because the measured
  official total cost `57109.67` is far above `DEFAULT_SPLIT` `49888.84`.
- The best synthesis of the three second-round reference files is:
  cost-discipline and seed sweeps from Claude; EV-cascade/blocking-chain
  repair from GPT; bounded hotspot partial split and search-only HIP/lexicographic
  ideas from Gemini. The conflict is resolved by prioritizing EV-cascade-aware
  scheduling/search first, then trying `GREEN_HOTSPOT_PARTIAL` only as a
  bounded third candidate.
- Any implementation of a blocking-chain operator must read physical vehicle
  order from the scheduled `Solution.routes`; the current `RouteSpec` does not
  contain predecessor/successor trip-chain state.
- The first executed EV-reservation optimization found a lower official Problem
  2 cost: `49239.78` versus the previous `49888.84`. The improvement comes
  primarily from reducing fixed cost to `18000.00` and lowering energy/carbon
  cost, while keeping policy conflicts at `0`.
- EV reservation penalty strength is sensitive. Penalty `500` improved service
  quality but cost `50010.53`; penalty `1000` reduced maximum lateness further
  in screening but badly worsened cost. Penalty `250` is the best verified
  official-cost setting so far.
- The experimental policy-operator path remains secondary: with EV reservation
  penalty `500`, it achieved excellent service quality (`2` late stops, max
  late `5.93`), but cost `50770.72`, so it should not be the formal answer
  under the official objective.
- `GREEN_HOTSPOT_PARTIAL` is useful as a bounded comparison variant, but the
  first verified run cost `52312.11`; it should not replace `DEFAULT_SPLIT`
  unless future search finds a lower official total cost.
- The 2026-04-26 Problem 2 closeout treats `outputs/problem2/` as the only
  formal answer folder. The previous `49888.84` run is retained only as
  `outputs/problem2_previous_49888_20260425/`, and the high-service-quality
  `policy operators + EV reservation p500` run is retained only as a
  sensitivity case in
  `outputs/problem2_experiments/formal_screen_policy_ev_p500/`.
- `docs/results/problem2_modeling_and_solution_closeout.md` is now the full
  paper-writing source for Problem 2. It should be used before drafting the
  final paper because it explicitly separates official objective, hard policy
  feasibility, auxiliary search penalties, service-quality sensitivity, and
  limitations such as the absence of road geometry and EV charging constraints.
