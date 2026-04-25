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

## Tooling Notes
- PowerShell inline Python can corrupt Chinese path literals. Prefer filesystem enumeration (`Path.glob`) or explicit UTF-8 handling.
