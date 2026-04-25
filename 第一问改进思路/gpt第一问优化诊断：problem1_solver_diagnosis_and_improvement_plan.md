# 第一问求解器诊断与优化建议交接文档

生成日期：2026-04-24  
适用项目：`Xiong-z-x/Math_Modeling_Project`  
适用范围：第十八届华中杯 A 题《城市绿色物流配送调度》第一问：无绿色限行政策下的静态车辆调度。  
文档目标：把当前第一问结果的主要瓶颈、源码依据、诊断结论和下一步改进方案封装成可交接给 Codex、其他模型或协作者的单一 Markdown 文件。

---

## 0. 执行摘要

当前第一问求解器已经具备较完整的工程基础：数据层、时变行驶时间、Jensen 修正能耗、软时间窗成本、虚拟服务节点、异构车辆容量约束、初解、ALNS、输出模块均已实现。当前正式结果为：

```text
总成本：约 51870.90
固定成本：14800.00
能源成本：23017.23
碳排成本：4953.10
时间窗惩罚：9100.58
总距离：13342.28 km
碳排：7620.15 kg
depot-to-depot 趟次：115
物理车辆使用：10 辆 E1，27 辆 F1
覆盖完整：True
容量可行：True
迟到停靠：约 84 个
最大迟到：约 286 分钟
跨午夜返回趟次：8 个
```

综合源码审查后的结论：

```text
当前结果可作为“成本优先基线解”，但不建议直接作为最终主方案写入论文。
主要瓶颈不是数据层或容量约束，而是：
1. 官方成本目标和固定成本计费方式天然偏向少开车、多复用；
2. ALNS 算子评估使用 08:00 出发的局部路线成本，和真实物理车排班后的成本错位；
3. 物理车辆排班每次都会重算，但只是贪心局部排班，不是服务质量优先的二阶段优化；
4. ALNS 接受准则和 best 更新仍只看 true total cost，没有显式控制 late_count、max_late 和 midnight_count；
5. 17:00 之后和跨午夜速度被代码默认无限延续为 MEDIUM，这需要明确建模假设或强惩罚。
```

最优先改动：

```text
1. 增加服务质量指标：late_stop_count、total_late_min、max_late_min、return_after_midnight_count 等；
2. 增加 search_score，并让 ALNS 接受准则和 best 更新使用 search_score 或分阶段目标；
3. 改造 destroy operator 接口，使算子能读取当前真实排班后的 Solution；
4. 新增 actual_late_remove、late_suffix_remove、midnight_route_remove、late_route_split；
5. 升级 schedule_route_specs() 的排班评分，使其服务质量优先，而不是弱迟到惩罚的总成本优先。
```

---

## 1. 题面与补充说明中的关键事实

第一问是“静态环境下的车辆调度”。在无政策限制条件下，需要建立考虑车辆类型、载重体积约束、时间窗约束与速度时变特性的车辆调度模型，以总配送成本最低为目标，输出车辆使用方案、行驶路径、到达时间及成本构成。

题面给定：

```text
早到等待成本：20 元/小时
晚到惩罚成本：50 元/小时
服务时间：20 分钟
车辆启动成本：400 元/辆
```

补充说明给定绿色配送区为以市中心为圆心、半径 10 km 的圆形区域，且表 1 速度分布以补充说明为准。修正后的速度分布覆盖 8:00--17:00：

```text
拥堵时段：
8:00--9:00
11:30--13:00
v(t) ~ N(9.8, 4.7^2)

顺畅时段：
9:00--10:00
13:00--15:00
v(t) ~ N(55.3, 0.1^2)

一般时段：
10:00--11:30
15:00--17:00
v(t) ~ N(35.4, 5.2^2)
```

注意：补充说明没有定义 17:00 之后的速度分布，也没有定义跨午夜后的速度规则。

---

## 2. 已读取仓库文件与关键源码依据

### 2.1 仓库总体状态

读取到的主要文件：

```text
README.md
项目文件导航.md
progress.md
green_logistics/constants.py
green_logistics/travel_time.py
green_logistics/cost.py
green_logistics/data_processing/loader.py
green_logistics/solution.py
green_logistics/initial_solution.py
green_logistics/operators.py
green_logistics/alns.py
green_logistics/output.py
problems/problem1.py
outputs/problem1/summary.json
outputs/problem1/route_summary.csv
outputs/problem1/stop_schedule.csv
```

README 记录当前基础已经实现：

```text
1. 数据处理：2169 条订单聚合为 88 个 active customers，并拆分为 148 个 virtual service nodes；
2. travel_time.py：时变 ETA 和跨时段积分；
3. cost.py：Jensen 修正能耗、载重修正、碳成本、软时间窗惩罚；
4. solution.py：Route/trip 评价、容量检查、customer_id 距离查表、覆盖检查；
5. initial_solution.py、operators.py、alns.py：初解和 ALNS；
6. output.py、problem1.py：第一问 CSV/JSON/PNG 输出。
```

README 同时说明：

```text
Route 表示一次 depot-to-depot trip。
Trips 会被顺序分配给 physical vehicles。
fleet limits 按 physical vehicle counts 检查。
```

### 2.2 数据层确认

`green_logistics/data_processing/loader.py` 的关键逻辑：

```python
ProblemData:
    orders
    coordinates
    distance_matrix
    time_windows
    customer_demands
    service_nodes
    node_to_customer
    no_order_customer_ids
    green_customer_ids
    active_green_customer_ids
```

数据处理行为：

```text
1. 读取 2169 条订单；
2. 读取 99 个坐标节点，其中 0 是配送中心，1--98 是客户；
3. 读取 99 x 99 距离矩阵；
4. 读取 98 个客户时间窗；
5. 按 customer_id 聚合订单；
6. 标记绿色配送区；
7. 按最大 3000 kg、15 m³ 拆分为虚拟服务节点；
8. 输出 service_nodes，其中 node_id 是虚拟节点编号，customer_id 是原始客户编号。
```

重要判断：

```text
虚拟节点 node_id 不等于原始 customer_id。
任何距离查表都必须使用 customer_id，而不能使用 node_id。
```

`solution.py` 中 `_distance_km()` 使用：

```python
problem.distance_matrix.loc[int(from_customer_id), int(to_customer_id)]
```

因此当前距离矩阵索引逻辑是正确的。

### 2.3 常量与时间边界

`green_logistics/constants.py` 中与诊断相关的常量：

```python
DAY_START_MIN = 8 * 60
SERVICE_TIME_MIN = 20
FIXED_COST_PER_VEHICLE = 400.0

EARLY_PENALTY_PER_MIN = 20.0 / 60.0
LATE_PENALTY_PER_MIN = 50.0 / 60.0

VEHICLE_TYPES = {
    "F1": 3000 kg, 13.5 m3, count 60, fuel
    "F2": 1500 kg, 10.8 m3, count 50, fuel
    "F3": 1250 kg, 6.5 m3, count 50, fuel
    "E1": 3000 kg, 15.0 m3, count 10, ev
    "E2": 1250 kg, 8.5 m3, count 15, ev
}
```

速度时段代码中额外包含：

```python
SPEED_PERIODS = [
    (8 * 60, 9 * 60, "CONGESTED"),
    (9 * 60, 10 * 60, "SMOOTH"),
    (10 * 60, 11 * 60 + 30, "MEDIUM"),
    (11 * 60 + 30, 13 * 60, "CONGESTED"),
    (13 * 60, 15 * 60, "SMOOTH"),
    (15 * 60, 17 * 60, "MEDIUM"),
    (17 * 60, 24 * 60, "MEDIUM"),
]
```

注意：

```text
题面补充说明只定义到 17:00；
当前代码把 17:00--24:00 扩展为 MEDIUM。
```

`green_logistics/travel_time.py` 中，如果时间超过所有已列时段，会继续使用最后一个时段，并把结束时间设为无穷：

```python
last_start, _last_end, last_key = SPEED_PERIODS[-1]
return _build_speed_period(last_key, float(last_start), inf)
```

因此实际含义是：

```text
17:00 以后一直使用 MEDIUM 速度；
24:00 以后也继续使用 MEDIUM 速度。
```

这解释了为什么 8 个跨午夜返回趟次仍能被计算出来。但这属于代码假设，不是题面明确给定事实。

### 2.4 成本模块确认

`green_logistics/cost.py` 中：

```python
expected_consumption_rate(vehicle_type, period_key)
```

使用：

```python
second_moment = mu**2 + sigma2
```

再代入二次能耗函数。这是 Jensen / 二阶矩修正，符合当前建模思路。

`calculate_time_window_penalty()` 中：

```python
wait_min = max(earliest_min - arrival_min, 0.0)
late_min = max(arrival_min - latest_min, 0.0)
cost = wait_min * EARLY_PENALTY_PER_MIN + late_min * LATE_PENALTY_PER_MIN
```

因此时间窗确实是软约束，不是硬约束。

### 2.5 路线评价与固定成本确认

`green_logistics/solution.py` 中 `Route` 表示 depot-to-depot trip，字段包括：

```python
depart_min
return_min
fixed_cost
energy_cost
carbon_cost
penalty_cost
total_cost
physical_vehicle_id
trip_id
```

`evaluate_solution()` 汇总：

```python
fixed_cost = sum(route.fixed_cost for route in route_tuple)
total_cost = sum(route.total_cost for route in route_tuple)
```

物理车辆使用量通过 `physical_vehicle_id` 去重统计：

```python
by_type.setdefault(route.vehicle_type_id, set()).add(route.physical_vehicle_id)
physical_usage = len(ids)
```

所以固定成本到底按什么计，取决于每条 Route 的 `fixed_cost` 是如何在排班阶段赋值的。

### 2.6 初解与物理车辆排班确认

`green_logistics/initial_solution.py` 中，`construct_initial_route_specs()` 先构造未排班的 RouteSpec：

```python
RouteSpec(vehicle_type_id, service_node_ids)
```

`construct_initial_route_specs()` 的排序键：

```python
earliest_min
latest_min
-demand_weight
node_id
```

append 到已有 route 时主要检查：

```text
1. max_stops_per_trip
2. 重量和体积容量
3. earliest 时间差不超过 150 分钟
4. 容量剩余评分
```

这一阶段没有做完整的时变 ETA 和软时间窗评价。

`_smallest_feasible_vehicle_id_or_none()` 中优先尝试燃油车，且第一轮跳过 EV：

```python
for vehicle_type_id in ("F3", "E2", "F2", "F1", "E1"):
    ...
    if vehicle_type_id.startswith("E"):
        continue
    return vehicle_type_id
for vehicle_type_id in ("E2", "E1"):
    ...
```

因此初始 RouteSpec 通常会优先使用燃油车型，只有燃油不合适时才尝试 EV。

`schedule_route_specs()` 是当前物理车辆排班核心。它会：

```text
1. 按 route spec 的最早时间窗排序；
2. 对每条 spec 枚举候选车型；
3. 枚举该车型已有物理车；
4. 若还有未启用车辆，也尝试新开一辆；
5. 对每个候选车辆计算实际 depart_min 并 evaluate_route；
6. 选择 _scheduling_selection_score 最低的候选；
7. 若新开车辆，则 fixed_cost=400；
8. 若复用已有车辆，则 fixed_cost=0。
```

源码中，新开车：

```python
candidate = evaluate_route(
    ...,
    fixed_cost=FIXED_COST_PER_VEHICLE,
    physical_vehicle_id=vehicle_id,
)
```

复用已有车：

```python
candidate = evaluate_route(
    ...,
    fixed_cost=0.0,
    physical_vehicle_id=str(vehicle["vehicle_id"]),
)
```

因此固定成本明确是按物理车首次启用计，不按趟次计。

排班阶段有一个迟到加权：

```python
LATE_SCHEDULING_PRIORITY = 2.0
```

排班选择评分：

```python
def _scheduling_selection_score(route: Route) -> float:
    late_minutes = sum(stop.late_min for stop in route.stops)
    return route.total_cost + late_minutes * LATE_SCHEDULING_PRIORITY
```

这说明当前排班不是完全忽略迟到，但额外迟到权重仍然较弱，而且只在排班的局部选择阶段使用。

### 2.7 ALNS 算子确认

`green_logistics/operators.py` 中当前破坏算子：

```python
random_remove
worst_cost_remove
related_remove
time_penalty_remove
```

当前修复算子：

```python
greedy_insert
regret2_insert
time_oriented_insert
```

缺少：

```text
late-route split
late-suffix destroy
midnight-route destroy
route merging
intra-route 2-opt
Or-opt
inter-route relocate
inter-route swap
vehicle-type reassignment
physical schedule local search
small-node extraction
```

最关键的源码问题是 `_local_route_cost()`：

```python
def _local_route_cost(problem: ProblemData, spec: RouteSpec | None) -> float:
    if spec is None or not spec.service_node_ids:
        return 0.0
    return evaluate_route(
        problem,
        spec.vehicle_type_id,
        spec.service_node_ids,
        depart_min=DAY_START_MIN
    ).total_cost
```

也就是说，算子评估插入、删除、regret、worst cost 时，默认所有路线都是 08:00 出发。真实排班中，一个 route spec 可能被安排到 13:00、16:00、18:00 甚至更晚出发。

这会产生严重错位：

```text
算子优化的是：C_local(route, 08:00)
真实解评估的是：C_scheduled(route, actual_depart_min)
```

`time_penalty_remove()` 也只是：

```python
route = evaluate_route(problem, spec.vehicle_type_id, spec.service_node_ids, depart_min=DAY_START_MIN)
```

因此它不是从当前真实排班解中移除实际迟到最严重的节点，而是移除“假设 08:00 出发时 penalty 最大”的节点。

### 2.8 ALNS 主循环确认

`green_logistics/alns.py` 中 `run_alns()`：

```python
initial_solution = schedule_route_specs(problem, initial_spec_tuple)
...
partial_specs, removed = destroy(...)
candidate_specs = repair(...)
candidate_solution = schedule_route_specs(problem, candidate_specs)
```

所以每次 ALNS 候选解都会重新调用 `schedule_route_specs()` 做物理车辆排班。这一点需要修正上一版“不确定是否重新排班”的判断。

但是接受准则只使用 `total_cost`：

```python
accepted = _accept_candidate(
    current_solution.total_cost,
    candidate_solution.total_cost,
    temperature,
    rng,
)
```

best 更新也只使用 `total_cost`：

```python
if candidate_solution.total_cost < best_solution.total_cost and candidate_solution.is_complete:
    best_specs = candidate_specs
    best_solution = candidate_solution
```

因此：

```text
ALNS 有重新贪心排班，但不是服务质量优先；
ALNS 接受和 best 更新仍以 true total cost 为唯一目标；
late_count、max_late、midnight_count 没有进入 ALNS 主目标。
```

### 2.9 输出模块确认

`green_logistics/output.py` 的 `summary.json` 当前包含：

```python
route_count
is_complete
is_capacity_feasible
missing_node_ids
duplicate_node_ids
vehicle_trip_usage_by_type
vehicle_physical_usage_by_type
total_distance_km
carbon_kg
cost_breakdown
```

但没有包含：

```text
late_stop_count
total_late_min
max_late_min
total_wait_min
return_after_17_count
return_after_midnight_count
max_return_min
trips_per_physical_vehicle
```

这些指标只能从 `stop_schedule.csv` 或额外脚本中间接计算，不利于 ALNS 日志追踪和后续模型理解。

---

## 3. 源码审查后的根因排序

### 3.1 第一根因：固定成本按物理车计，多趟复用天然鼓励少开车

当前代码中，新开物理车计 400 元，复用已有物理车计 0 元。由于晚到惩罚是 50 元/小时，即 0.833 元/分钟，新增一辆车要减少至少：

```text
400 / 50 = 8 小时
```

累计晚到，才能在官方总成本上打平。

因此，在纯成本目标下，优化器会倾向：

```text
少开物理车
让已启动车辆多跑几趟
接受一些迟到
```

当前 37 辆物理车执行 115 趟，平均每辆车约 3.1 趟。这是目标函数自然导向，不是单一代码 bug。

类型：建模目标问题 + 成本结构问题。

### 3.2 第二根因：ALNS 算子用 08:00 局部成本，和真实排班成本错位

当前算子的 `_local_route_cost()` 统一使用：

```python
depart_min=DAY_START_MIN
```

即 08:00 出发的路线成本。真实排班中，很多 route spec 实际出发时间远晚于 08:00。因此插入/删除评价与最终排班评价不一致。

典型后果：

```text
1. 算子认为某个节点插入某条路线成本低；
2. 但该 route spec 实际被排到某辆车第 2 或第 3 趟；
3. 实际到达时间大幅推迟；
4. 真实 late_min 很大；
5. ALNS 很难定向修复，因为 destroy 阶段也看不到真实 late stop。
```

类型：算法评价函数问题。

### 3.3 第三根因：每次候选解虽重新排班，但排班器是贪心局部选择

`run_alns()` 每轮都调用 `schedule_route_specs()`，所以“没有重新排班”不是事实。真正问题是：排班器不是全局二阶段优化，而是逐条 route spec 贪心分配车辆。

对每个 route spec，当前选择局部评分最低的车辆：

```python
route.total_cost + 2.0 * total_late_minutes
```

这不足以控制：

```text
late_stop_count
max_late_min
return_after_midnight_count
```

也不能做以下全局交换：

```text
1. 将某个 late route 从已有车第 3 趟移动到一辆新车；
2. 交换两辆同类型车辆的后续趟次；
3. 为最紧时间窗的 route 优先保留早出发车辆；
4. 在服务质量恶化时强制新开车。
```

类型：排班算法问题。

### 3.4 第四根因：ALNS 主目标只看 true total cost，没有服务质量二级目标

排班局部阶段有轻度迟到加权，但 ALNS 接受准则和 best 更新仍只看 `solution.total_cost`。

因此，即使某个候选解减少迟到数量和最大迟到，只要 true total cost 增加，仍可能被拒绝；反之，某个候选解如果总成本降低但迟到质量变差，仍可能被接受或成为 best。

类型：优化目标问题。

### 3.5 第五根因：缺少强力降迟到算子

当前算子集偏基础：

```text
random remove
worst cost remove
related remove
time penalty remove
greedy insert
regret-2 insert
time-oriented insert
```

但当前的主要质量问题是：

```text
实际排班后迟到多
最大迟到大
后续趟次太晚
跨午夜返回
```

这些问题需要结构性算子：

```text
late-route split
late-suffix destroy
actual-late remove
midnight-route destroy
physical schedule reassignment
small-node extraction
2-opt / Or-opt / swap / relocate
```

类型：ALNS 算子不足问题。

### 3.6 第六根因：17:00 后速度和跨午夜速度是代码假设，不是题面事实

补充说明速度分布只覆盖 8:00--17:00。当前代码：

```text
17:00--24:00 使用 MEDIUM；
24:00 以后继续无限使用 MEDIUM。
```

这使跨午夜结果可计算，但论文中必须说明。如果不说明，模型边界与补充说明不一致。

类型：建模边界问题。

---

## 4. 哪些属于建模问题，哪些属于算法问题

| 问题 | 类型 | 说明 |
|---|---|---|
| 固定成本按物理车计、多趟复用 | 建模选择 | 可解释为“日启用成本”，但会鼓励少用车 |
| 晚到惩罚相对固定成本低 | 题面成本结构 + 优化目标问题 | 400 元新车需要抵消 8 小时迟到才划算 |
| 17:00 后速度延续为 MEDIUM | 建模假设 | 代码中存在，但题面补充说明未给出 |
| 跨午夜继续使用 MEDIUM | 建模边界问题 | 需要强惩罚或论文说明 |
| 初始解容量优先、时间近似 | 算法问题 | 初解可行但不一定时间质量好 |
| operator 局部成本假设 08:00 出发 | 算法问题 | 与真实排班出发时间错位 |
| schedule_route_specs 是贪心排班 | 算法问题 | 有重排班，但没有二阶段全局优化 |
| ALNS 接受只看 total_cost | 算法目标问题 | 未控制 late_count、max_late、midnight_count |
| 缺少 late split / suffix destroy / schedule local search | 算子问题 | 直接影响迟到修复能力 |
| F2/F3/E2 未使用 | 数据结构 + 算子问题 | 很多节点太重，小车不可服务；但也缺少小节点剥离策略 |

---

## 5. 对上一版诊断的修正

| 上一版判断 | 源码后结论 | 是否维持 |
|---|---|---|
| 固定成本按物理车计会鼓励少用车、多迟到 | 源码确认：新车 fixed_cost=400，复用 fixed_cost=0 | 维持 |
| 晚到惩罚相对新增车辆成本偏低 | 题面和常量均确认 | 维持 |
| 物理车辆排班可能没有独立优化 | 修正：每轮候选解都会重新贪心排班，但不是二阶段全局优化 | 修正 |
| ALNS 缺少关键降迟到算子 | 源码确认 | 维持 |
| 时间窗惩罚应更强进入评分 | 源码显示排班有 `late_minutes * 2.0`，但 ALNS 接受仍只看 total_cost | 维持但细化 |
| 跨午夜可能超出题目速度边界 | 源码确认 17:00 后和跨午夜被 MEDIUM 无限延长 | 维持且升级为确定问题 |
| F2/F3/E2 未使用可能是未鼓励开车 | 源码显示不是完全禁止，而是容量结构与算子缺失共同导致 | 修正 |

---

## 6. 必须先做的诊断实验

在大改代码前，建议先做以下 5 个实验。它们能判断迟到是数据必然、路线结构问题，还是排班问题。

### 实验 A：单节点直达最早到达下界

对每个虚拟服务节点 \(i\)，计算 08:00 从仓库直接出发到该节点的最早到达时间：

```python
arrival_direct = calculate_arrival_time(distance_matrix.loc[0, customer_id], 480)
direct_late = max(arrival_direct - latest_min, 0)
```

输出：

```text
direct_late_count
direct_total_late_min
direct_max_late_min
```

解释：

```text
如果 direct_late_count 很小，而当前 late_stop_count 是 84，
说明迟到主要不是数据必然，而是路线组合或排班造成。
```

### 实验 B：当前 115 条路线全部独立车辆 08:00 出发

保持当前 route_summary 中的 service_node_sequence 不变，但每条 route 都单独新开车辆，depart_min = 480。

输出：

```text
late_stop_count
total_late_min
max_late_min
fixed_cost
total_cost
```

解释：

```text
如果迟到大幅下降，说明主要问题在物理车多趟复用排班。
```

### 实验 C：保持路线不变，只重新做服务质量优先排班

输入当前 115 条 RouteSpec，修改排班器评分为：

```text
route.total_cost
+ 300 * late_stop_count
+ 5 * max_late_min
+ 1 * total_late_min
+ 1_000_000 * is_after_midnight
```

比较：

```text
原排班 vs 服务质量优先排班
```

解释：

```text
如果迟到下降明显，不必先大改 ALNS，优先改 schedule_route_specs。
```

### 实验 D：搜索阶段放大迟到权重

保持官方 true_cost 不变，但 ALNS 内部 search_score 加入服务质量项：

```text
search_score =
true_cost
+ 300 * late_stop_count
+ 5 * max_late_min
+ 1 * total_late_min
+ 1_000_000 * midnight_count
```

解释：

```text
如果迟到显著下降，说明当前主要是目标权重和接受准则问题。
```

### 实验 E：禁止或强惩罚跨午夜

方案：

```python
if route.return_min >= 1440:
    score += 1_000_000
```

解释：

```text
若跨午夜可消除且成本上升可接受，则论文主方案应尽量采用无跨午夜方案。
```

---

## 7. 具体修改方案

### 7.1 改进 1：新增服务质量指标

建议新增文件：

```text
green_logistics/metrics.py
```

或在 `solution.py` 中增加汇总函数。

建议数据结构：

```python
@dataclass(frozen=True)
class SolutionQualityMetrics:
    late_stop_count: int
    total_late_min: float
    max_late_min: float
    wait_stop_count: int
    total_wait_min: float
    max_wait_min: float
    return_after_17_count: int
    return_after_midnight_count: int
    max_return_min: float
    max_trips_per_physical_vehicle: int
    mean_trips_per_physical_vehicle: float
```

核心计算：

```python
def solution_quality_metrics(solution: Solution) -> SolutionQualityMetrics:
    stops = [stop for route in solution.routes for stop in route.stops]
    late_values = [stop.late_min for stop in stops]
    wait_values = [stop.wait_min for stop in stops]
    return_values = [route.return_min for route in solution.routes]

    trips_by_vehicle = Counter(
        route.physical_vehicle_id
        for route in solution.routes
        if route.physical_vehicle_id
    )

    return SolutionQualityMetrics(
        late_stop_count=sum(1 for v in late_values if v > 1e-9),
        total_late_min=sum(late_values),
        max_late_min=max(late_values, default=0.0),
        wait_stop_count=sum(1 for v in wait_values if v > 1e-9),
        total_wait_min=sum(wait_values),
        max_wait_min=max(wait_values, default=0.0),
        return_after_17_count=sum(1 for v in return_values if v > 17 * 60),
        return_after_midnight_count=sum(1 for v in return_values if v >= 24 * 60),
        max_return_min=max(return_values, default=0.0),
        max_trips_per_physical_vehicle=max(trips_by_vehicle.values(), default=0),
        mean_trips_per_physical_vehicle=(
            sum(trips_by_vehicle.values()) / len(trips_by_vehicle)
            if trips_by_vehicle else 0.0
        ),
    )
```

需要改的文件：

```text
green_logistics/solution.py 或新增 green_logistics/metrics.py
green_logistics/output.py
problems/problem1.py
tests/test_output.py 或新增 tests/test_metrics.py
```

输出 JSON 增加：

```json
"quality_metrics": {
  "late_stop_count": ...,
  "total_late_min": ...,
  "max_late_min": ...,
  "return_after_17_count": ...,
  "return_after_midnight_count": ...
}
```

### 7.2 改进 2：新增 search_score，与 true_cost 分离

保留官方成本：

```text
true_cost = fixed + energy + carbon + time_window_penalty
```

新增搜索评分：

```python
@dataclass(frozen=True)
class SearchScoreWeights:
    late_stop: float = 300.0
    total_late_min: float = 1.0
    max_late_min: float = 5.0
    midnight_route: float = 1_000_000.0
    after_17_route: float = 0.0
```

评分函数：

```python
def score_solution(solution: Solution, weights: SearchScoreWeights) -> float:
    q = solution_quality_metrics(solution)
    return (
        solution.total_cost
        + weights.late_stop * q.late_stop_count
        + weights.total_late_min * q.total_late_min
        + weights.max_late_min * q.max_late_min
        + weights.midnight_route * q.return_after_midnight_count
        + weights.after_17_route * q.return_after_17_count
    )
```

修改 `ALNSIteration`：

```python
@dataclass(frozen=True)
class ALNSIteration:
    iteration: int
    current_cost: float
    current_score: float
    best_cost: float
    best_score: float
    candidate_cost: float
    candidate_score: float
    candidate_late_count: int
    candidate_max_late_min: float
    accepted: bool
    destroy_operator: str
    repair_operator: str
```

修改 `run_alns()`：

```python
current_score = score_solution(current_solution, weights)
candidate_score = score_solution(candidate_solution, weights)

accepted = _accept_candidate(
    current_score,
    candidate_score,
    temperature,
    rng,
)

if (
    candidate_solution.is_complete
    and candidate_solution.is_capacity_feasible
    and candidate_score < best_score
):
    best_solution = candidate_solution
```

注意：

```text
最终报告仍输出 true_cost；
search_score 只是搜索引导，不是题面成本。
```

### 7.3 改进 3：改造 destroy operator 接口，使其能看到当前真实 Solution

当前接口：

```python
DestroyOperator = Callable[
    [ProblemData, Sequence[RouteSpec], Random, int],
    tuple[tuple[RouteSpec, ...], tuple[int, ...]]
]
```

建议改为：

```python
DestroyOperator = Callable[
    [ProblemData, Sequence[RouteSpec], Solution, Random, int],
    tuple[tuple[RouteSpec, ...], tuple[int, ...]]
]
```

旧算子可以包装为忽略 `solution`：

```python
def random_remove_operator(problem, specs, solution, rng, remove_count):
    return random_remove(specs, rng, remove_count=remove_count)
```

这样新增算子能读取当前真实排班后的 late stop。

### 7.4 改进 4：新增 actual_late_remove

目标：移除当前真实解中迟到最严重的节点，而不是 08:00 局部评价下 penalty 最大的节点。

伪代码：

```python
def actual_late_remove(problem, specs, solution, rng, remove_count):
    late_stops = []
    for route in solution.routes:
        for stop in route.stops:
            if stop.late_min > 0:
                late_stops.append((stop.late_min, stop.service_node_id))

    if not late_stops:
        return random_remove_operator(problem, specs, solution, rng, remove_count)

    selected = [
        node_id
        for late, node_id in sorted(late_stops, reverse=True)[:remove_count]
    ]
    return _remove_nodes(specs, selected), tuple(selected)
```

### 7.5 改进 5：新增 late_suffix_remove

目标：如果某条路线开始迟到，后续节点通常会继续被推迟。直接删除迟到后缀比随机移除更有效。

伪代码：

```python
def late_suffix_remove(problem, specs, solution, rng, remove_count):
    # 找到 max_late route
    target_route = max(
        solution.routes,
        key=lambda route: max((stop.late_min for stop in route.stops), default=0.0),
    )

    # 找到第一处迟到 stop_index
    suffix_nodes = []
    found = False
    for stop in target_route.stops:
        if stop.late_min > 0:
            found = True
        if found:
            suffix_nodes.append(stop.service_node_id)

    if not suffix_nodes:
        return random_remove_operator(problem, specs, solution, rng, remove_count)

    selected = tuple(suffix_nodes[:remove_count])
    return _remove_nodes(specs, selected), selected
```

### 7.6 改进 6：新增 midnight_route_remove

目标：消灭跨午夜路线。

伪代码：

```python
def midnight_route_remove(problem, specs, solution, rng, remove_count):
    midnight_routes = [
        route for route in solution.routes
        if route.return_min >= 24 * 60
    ]

    if not midnight_routes:
        return random_remove_operator(problem, specs, solution, rng, remove_count)

    target = max(midnight_routes, key=lambda route: route.return_min)
    selected = tuple(target.service_node_ids[:remove_count])
    return _remove_nodes(specs, selected), selected
```

### 7.7 改进 7：新增 late_route_split

目标：将一条迟到严重的长路线拆成两条路线，允许新增物理车或提前排班。

伪代码：

```python
def late_route_split(problem, specs, solution, rng, remove_count):
    target_route = max(
        solution.routes,
        key=lambda route: max((stop.late_min for stop in route.stops), default=0.0),
    )

    nodes = target_route.service_node_ids
    if len(nodes) <= 1:
        return tuple(specs)

    # 在第一处迟到或 max_late stop 处切分
    split_pos = None
    for idx, stop in enumerate(target_route.stops):
        if stop.late_min > 0:
            split_pos = idx
            break

    if split_pos is None or split_pos == 0:
        split_pos = len(nodes) // 2

    prefix = nodes[:split_pos]
    suffix = nodes[split_pos:]

    # 在 specs 中找到对应 spec 并替换
    new_specs = []
    replaced = False
    for spec in specs:
        if spec.service_node_ids == nodes and not replaced:
            if prefix:
                new_specs.append(_retyped_spec(problem, prefix))
            if suffix:
                new_specs.append(_retyped_spec(problem, suffix))
            replaced = True
        else:
            new_specs.append(spec)

    return tuple(spec for spec in new_specs if spec is not None)
```

### 7.8 改进 8：升级 schedule_route_specs() 的排班评分

当前：

```python
return route.total_cost + late_minutes * 2.0
```

建议先改为：

```python
def _scheduling_selection_score(route: Route) -> float:
    late_values = [stop.late_min for stop in route.stops]
    late_stop_count = sum(1 for v in late_values if v > 1e-9)
    total_late = sum(late_values)
    max_late = max(late_values, default=0.0)
    is_midnight = 1 if route.return_min >= 24 * 60 else 0

    return (
        route.total_cost
        + 300.0 * late_stop_count
        + 1.0 * total_late
        + 5.0 * max_late
        + 1_000_000.0 * is_midnight
    )
```

这会鼓励：

```text
1. 对紧时间窗 route 新开车辆；
2. 降低最大迟到；
3. 避免跨午夜；
4. 在必要时牺牲一部分固定成本换服务质量。
```

### 7.9 改进 9：新增 small_node_extraction

背景：

```text
当前所有 115 趟都使用 E1 或 F1；
F2/F3/E2 没有使用；
但很多虚拟节点本身超过 1500kg，小车确实不能服务。
```

因此不能简单要求“使用小车”，而应剥离可由小车服务的小需求节点。

算子目标：

```text
从 F1/E1 route 中抽取 demand_weight <= 1250 或 <=1500 的节点；
优先抽取 latest_min 早、late_min 高的小节点；
重新插入时允许 F2/F3/E2 单独服务或组合服务；
降低大车后续排班压力。
```

伪代码：

```python
def small_node_extraction(problem, specs, solution, rng, remove_count):
    lookup = _node_lookup(problem)
    candidates = []

    for route in solution.routes:
        if route.vehicle_type_id not in {"F1", "E1"}:
            continue
        for stop in route.stops:
            node = lookup[stop.service_node_id]
            weight = float(node["demand_weight"])
            volume = float(node["demand_volume"])
            if weight <= 1500 and volume <= 10.8:
                score = (
                    1000 * (stop.late_min > 0)
                    + stop.late_min
                    - float(node["latest_min"]) / 1000
                )
                candidates.append((score, stop.service_node_id))

    selected = [
        node_id
        for score, node_id in sorted(candidates, reverse=True)[:remove_count]
    ]

    if not selected:
        return random_remove_operator(problem, specs, solution, rng, remove_count)

    return _remove_nodes(specs, selected), tuple(selected)
```

修复阶段 `_retyped_spec()` 已经会按容量选车，但建议给小节点修复新增一个 repair：

```text
small_vehicle_priority_insert
```

优先尝试 F3、F2、E2，而不是总是追求局部 cost 最低。

---

## 8. 推荐的分阶段优化顺序

### 阶段 0：指标补全与边界检查

目标：

```text
补齐质量指标；
确认 direct_late_count；
确认 current independent-route lateness；
确认跨午夜数量；
确认 17:00 后速度假设。
```

不急于调参。

### 阶段 1：服务质量优先

目标函数：

```text
minimize:
1. return_after_midnight_count
2. late_stop_count
3. max_late_min
4. total_late_min
```

允许 true_cost 暂时上升。

重点算子：

```text
actual_late_remove
late_suffix_remove
midnight_route_remove
late_route_split
service-quality scheduling score
```

### 阶段 2：在服务质量阈值内降成本

设定约束：

```text
return_after_midnight_count = 0
late_stop_count <= 当前 best late count
max_late_min <= 当前 best max late
```

在不恶化这些指标的前提下优化 true_cost。

重点算子：

```text
route merging
regret insert
2-opt / Or-opt
vehicle type reassignment
```

### 阶段 3：能源与碳排微调

在服务质量不恶化的前提下，优化：

```text
energy_cost
carbon_cost
total_distance
vehicle-type mix
```

---

## 9. 建议的代码修改优先级

### P0：只加指标，不改变求解逻辑

文件：

```text
green_logistics/metrics.py 或 solution.py
green_logistics/output.py
problems/problem1.py
tests/test_metrics.py
```

验收：

```text
summary.json 包含 late_stop_count、max_late_min、return_after_midnight_count；
当前正式结果能复现 84 late stops、max late about 286 min、8 midnight trips；
pytest 通过。
```

### P1：排班评分服务质量化

文件：

```text
green_logistics/initial_solution.py
tests/test_initial_solution.py
```

改动：

```python
_scheduling_selection_score()
```

验收：

```text
同一批 route specs 下，服务质量排班 late_count 或 max_late 明显下降；
coverage 和 capacity 仍为 True；
跨午夜数量应下降，最好为 0。
```

### P2：ALNS 引入 search_score

文件：

```text
green_logistics/alns.py
green_logistics/metrics.py
tests/test_alns_smoke.py
```

改动：

```text
ALNSIteration 增加 score 与质量字段；
接受准则使用 search_score；
best 更新使用 search_score 或分阶段目标。
```

验收：

```text
history.csv 中有 true cost 与 search score；
ALNS 不再只保存最低 true_cost 的高迟到解。
```

### P3：改造 operator 接口，加入真实迟到 destroy

文件：

```text
green_logistics/operators.py
green_logistics/alns.py
tests/test_alns_smoke.py
```

新增：

```text
actual_late_remove
late_suffix_remove
midnight_route_remove
```

验收：

```text
destroy 算子能基于 current_solution 找到真实 late stop；
不破坏 coverage；
repair 后 solution complete=True。
```

### P4：加入 late_route_split 和 small_node_extraction

文件：

```text
green_logistics/operators.py
tests/test_alns_smoke.py
```

验收：

```text
max_late_min 明显下降；
F2/F3/E2 至少在服务质量方案中有机会被启用；
容量仍可行。
```

---

## 10. 论文表达建议

不要把当前 51870.90 方案直接包装成唯一最优调度方案。建议论文中分成三类方案：

| 方案 | 目标 | 说明 |
|---|---|---|
| 成本优先基线解 | 最小化官方 true_cost | 当前 51870.90 方案可归入此类 |
| 服务质量均衡解 | 控制迟到数量、最大迟到和跨午夜，再尽量降成本 | 推荐作为主方案 |
| 服务优先解 | 尽量降低迟到和跨午夜，允许成本上升 | 用于敏感性分析 |

解释方式：

```text
由于题面给定的是软时间窗，允许用惩罚成本刻画早到/晚到；
但运营上大量迟到不合理，因此在官方成本目标外加入服务质量指标；
最终报告同时给出成本和服务质量，体现绿色物流调度中的经济性与客户满意度权衡。
```

关于 17:00 后速度：

```text
若继续使用当前代码假设，应在论文中说明：
由于题目仅给出 8:00--17:00 速度分布，本文假设 17:00 后延续一般时段速度。
```

更稳妥的主方案：

```text
强惩罚跨午夜，尽量保证所有趟次在当日返回；
若仍允许 17:00 后返回，则明确说明速度延续假设。
```

---

## 11. 给后续 Codex/模型的直接任务提示

可以把以下提示直接交给 Codex 或实现模型：

```text
请在不推翻现有架构的前提下，改进第一问求解器的时间窗质量。

必须先阅读：
- green_logistics/solution.py
- green_logistics/initial_solution.py
- green_logistics/operators.py
- green_logistics/alns.py
- green_logistics/output.py
- outputs/problem1/summary.json

第一步：
新增 green_logistics/metrics.py，实现 solution_quality_metrics(solution)，统计：
late_stop_count、total_late_min、max_late_min、wait_stop_count、total_wait_min、
return_after_17_count、return_after_midnight_count、max_return_min、
max_trips_per_physical_vehicle、mean_trips_per_physical_vehicle。
把这些指标写入 summary.json 和 alns_history.csv。

第二步：
新增 score_solution(solution, weights)，保留 true_cost 不变，但 ALNS 接受准则和 best 更新使用 search_score：
search_score = true_cost
+ 300 * late_stop_count
+ 1 * total_late_min
+ 5 * max_late_min
+ 1_000_000 * return_after_midnight_count。

第三步：
升级 schedule_route_specs() 中的 _scheduling_selection_score()，使用与 search_score 类似的服务质量优先评分，
不要只使用 route.total_cost + 2.0 * late_minutes。

第四步：
改造 DestroyOperator 接口，使 destroy 算子能访问 current_solution。
新增 actual_late_remove、late_suffix_remove、midnight_route_remove。

第五步：
新增 late_route_split，对最大迟到 route 从第一处迟到 stop 或 max_late stop 处分裂为两条 RouteSpec。

要求：
- 不改 load_problem_data() 的稳定入口；
- 不改变 service_node_id/customer_id 的距离查表逻辑；
- 保持 coverage complete=True；
- 保持 capacity feasible=True；
- 正式输出中同时报告 true_cost 和 service-quality metrics；
- 优先目标是把跨午夜趟次从 8 降到 0，并显著降低 late_stop_count 和 max_late_min。
```

---

## 12. 最终判断

源码审查后，上一版诊断的核心方向仍然成立，但需要更精确地表述为：

```text
当前代码不是没有排班，也不是没有迟到惩罚；
当前代码的问题是：
1. 物理车固定成本模型鼓励多趟复用；
2. ALNS 算子使用 08:00 局部评价，无法精准感知真实排班后的迟到；
3. 物理车排班每次都会重算，但只是贪心局部选择；
4. ALNS 主循环只优化 true total cost，没有把 late_count、max_late、midnight_count 作为显式目标；
5. 17:00 后和跨午夜速度是代码假设，需要论文说明或算法强惩罚。
```

最值得立即实施的不是单纯增加 ALNS 迭代次数，而是：

```text
指标补全
+
服务质量 search_score
+
真实迟到导向 destroy
+
late-route split
+
服务质量优先排班
```

只要完成这些改动，预计能显著降低当前的迟到停靠数、最大迟到和跨午夜趟次；总成本可能会上升，但这将形成更合理、更容易在论文中解释的“服务质量均衡方案”。
