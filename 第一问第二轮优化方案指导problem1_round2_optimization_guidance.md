# 华中杯 A 题第一问第二轮优化指导文件

适用仓库：`Xiong-z-x/Math_Modeling_Project`  
适用问题：第一问静态车辆调度，TD-HFVRPTW 变体，含软时间窗、多趟复用、时变路网、期望能耗与碳成本。  
文档目标：在第一轮服务质量优化已经成功的基础上，吸收 Claude 第二轮建议中真正有价值的部分，结合当前最新代码与题目事实，给出更符合物理逻辑、工程可落地、并可支撑第二问/第三问扩展的优化路线。

---

## 1. 当前状态判断

### 1.1 最新第一问结果

当前正式输出已经从早期“成本优先但服务质量差”的状态显著改善。最新 `outputs/problem1/summary.json` 显示：

```text
总成本：48644.68
固定成本：17200.00
能源成本：25091.79
碳成本：5419.37
时间窗惩罚：933.53
总距离：13384.29 km
碳排放：8337.49 kg
趟次数：116
物理车辆：10 E1 + 33 F1
覆盖完整：True
容量可行：True
迟到停靠数：4
总迟到：77.42 min
最大迟到：31.60 min
跨午夜返回：0
17:00 后返回趟次：71
最大返回时刻：1428.52 min，约 23:49
最大单车趟数：5
平均单车趟数：2.70
```

相对旧结果：

```text
迟到停靠：84 -> 4
最大迟到：约 286 min -> 31.60 min
跨午夜：8 -> 0
总成本：约 51870.90 -> 48644.68
物理车辆数：37 -> 43
```

这说明第一轮修复不是单纯用成本换服务质量，而是找到了同时降低真实成本与迟到的支配解。当前第一问作为主方案已经基本达标，第二轮优化不应再以“抢救第一问”为核心，而应转为：

```text
1. 验证 4 个残余迟到是否可避免；
2. 优化等待、晚归、迭代收敛等细节；
3. 清理架构边界，为第二问绿色限行与第三问动态调度提供可扩展接口；
4. 形成论文中更可信的对照、敏感性分析与物理解释。
```

---

## 2. 对 Claude 第二轮建议的吸收与校正

### 2.1 值得吸收的部分

Claude 建议中真正有价值的部分包括：

1. **先诊断 4 个残余迟到的性质**  
   这是最值得立即做的。当前只有 4 个迟到节点，继续堆算子之前，必须先判断它们是物理上不可避免、排班级联残余，还是算法局部最优。

2. **C-lite 而非完整方案 C**  
   当前第一问已达标，不宜推倒重写。但 `schedule_route_specs()` 仍在 `initial_solution.py`，职责混淆明显。应将物理排班抽出为独立 `scheduler.py`，保留现有 `RouteSpec / Route / Solution`，逐步引入 `SchedulingConfig / TripDescriptor / PolicyEvaluator`。

3. **增加 ALNS 迭代与收敛分析**  
   当前正式运行只有 40 次迭代，而 `alns_history.csv` 显示最优解在第 37 次附近才出现。应做 100/200/500 次与多 seed 收敛实验，以判断是否还有低风险改进空间。

4. **Or-opt 优先于 2-opt**  
   时变路网下 2-opt 翻转后不能用静态 delta 公式，必须完整重算 ETA。由于当前路线多为短趟，先实现 Or-opt 或小规模 relocate 更稳。

5. **不要盲目强推 F2/F3/E2**  
   题面所有车型固定成本相同；当前代码中燃油车基础能耗函数也不按车型区分，小车没有天然成本优势。大量虚拟节点超过 1500kg，小车无法服务。只有在小节点剥离、并行度提升或第二问新能源限行中，小车才可能有局部价值。

6. **绿区容量预判应在第二问前完成**  
   第二问本质是时间-区域-车型耦合约束。进入第二问前应先统计绿区虚拟节点总需求、EV 载重/体积能力、第一问中燃油车服务绿区的时段分布。

### 2.2 需要校正或暂缓的部分

1. **不应默认加入 22:00 硬返库约束**  
   题面没有给司机工作时长或 22:00 返库约束。主模型不能把 22:00 写成硬约束。可将其作为 `scenario_return_limit_min` 的敏感性分析参数。

2. **完整方案 C 暂不应立即实施**  
   目前第一问指标已经很强，完整重写为“ALNS 只生成 TripDescriptor，scheduler 全权调度”的收益边际不高，回归风险大。应先做 C-lite。

3. **路线池 + Set Partitioning 暂缓**  
   多趟问题中 trip 的真实成本强依赖物理排班后的出发时间。若路线池只用 08:00 成本或静态 trip cost 做集合划分，会重现旧问题。除非后续把 scheduler 嵌入候选评估，否则 route pool SP 仅适合作论文扩展，不适合现在主线。

4. **出发时刻优化有价值，但不应先做全局高频扫描**  
   当前 `_preferred_departure_min()` 只对齐第一站 earliest，未优化全 route 的等待/能耗。可以在 scheduler 层作为候选出发时间扫描，但应先作为可配置选项，避免每次评估计算量放大过多。

---

## 3. 第二轮优化的核心目标

第二轮不再以“救第一问迟到”为主，而应以以下四个目标为主：

```text
目标 A：验证当前 4 个迟到的性质，判断是否值得继续追 0 迟到。
目标 B：降低非物理或弱解释现象，如超长等待、接近午夜返回、17:00 后行驶假设依赖。
目标 C：把 scheduler 从 initial_solution.py 中抽离，形成清晰 C-lite 架构。
目标 D：为第二问绿色限行与第三问动态调度预留 policy / state 接口。
```

---

## 4. 必做诊断：4 个残余迟到分类

新增文件建议：

```text
green_logistics/diagnostics.py
```

新增函数：

```python
def diagnose_late_stops(problem: ProblemData, solution: Solution) -> pd.DataFrame:
    ...
```

每个迟到停靠至少输出：

```text
route_index / trip_id
physical_vehicle_id
vehicle_type
service_node_id
customer_id
earliest_min
latest_min
arrival_min
late_min
route_depart_min
route_return_min
trip_position_on_vehicle
is_direct_late_from_depot_0800
direct_arrival_min
direct_late_min
same_customer_split_count
classification
```

分类逻辑：

```text
Type A：直达也迟到
    08:00 从 depot 直达该 customer_id，arrival > latest_min。
    这种迟到是数据/交通时段导致的，论文中可解释为软时间窗必要性。

Type B：多趟级联残余
    直达不迟到，但该 trip 是物理车第 2/3/4/5 趟，且 route_depart_min 已明显晚于 08:00。
    这种迟到应优先通过 scheduler 层移动 trip 到新车或更早可用车解决。

Type C：路线内部顺序或局部最优
    直达不迟到，trip 也不是明显晚出发，但 route 内访问顺序导致迟到。
    这种迟到可通过 Or-opt / relocate / swap 修复。
```

验收：

```text
outputs/problem1/late_stop_diagnosis.csv
outputs/problem1/late_stop_diagnosis.md
```

决策规则：

```text
若 4 个迟到多为 Type A：停止追求 0 迟到，把当前方案作为主方案。
若 4 个迟到多为 Type B：优先做 scheduler-level move_late_trip_to_new_vehicle。
若 4 个迟到多为 Type C：优先做 Or-opt 或 route 内 relocate。
```

---

## 5. C-lite 架构升级方案

### 5.1 抽出 scheduler.py

新增：

```text
green_logistics/scheduler.py
```

迁移以下函数或逻辑：

```text
schedule_route_specs
_candidate_vehicle_type_ids
_preferred_departure_min
_scheduling_selection_score
车辆池 vehicles_by_type
available_min 更新逻辑
fixed_cost=400 / reuse fixed_cost=0 逻辑
```

`initial_solution.py` 应只保留：

```text
RouteSpec
construct_initial_solution
construct_initial_route_specs
初始 RouteSpec 构造相关辅助函数
```

兼容策略：

```python
# initial_solution.py 中保留旧路径兼容
from .scheduler import schedule_route_specs
```

### 5.2 新增 SchedulingConfig

```python
@dataclass(frozen=True)
class SchedulingConfig:
    score_weights: SearchScoreWeights = field(default_factory=SearchScoreWeights)
    forbid_midnight: bool = False
    midnight_penalty: float = 1_000_000.0
    scenario_return_limit_min: float | None = None
    reload_time_min: float = 0.0
    prefer_on_time: bool = True
    optimize_departure_grid_min: int | None = None
    max_departure_delay_min: float = 180.0
```

说明：

```text
forbid_midnight：默认 False；可通过 search score 强惩罚跨午夜。
scenario_return_limit_min：默认 None；22:00 只能作为情景参数，不是题面硬约束。
reload_time_min：默认 0，因为题面没有给再装车时间；可做 10/20 min 敏感性。
optimize_departure_grid_min：默认 None；若设置为 5/10，则在候选车辆可用时刻后做出发时刻离散扫描。
```

### 5.3 TripDescriptor 作为旁路描述层

新增：

```text
green_logistics/trips.py
```

```python
@dataclass(frozen=True)
class TripDescriptor:
    vehicle_type_id: str
    service_node_ids: tuple[int, ...]
    customer_ids: tuple[int, ...]
    total_weight_kg: float
    total_volume_m3: float
    earliest_window_min: float
    latest_window_min: float
    preferred_departure_min: float
    estimated_duration_min: float
    min_latest_slack_min: float
    is_green_zone_touched: bool
    green_stop_count: int
```

新增函数：

```python
def describe_route_spec(problem: ProblemData, spec: RouteSpec) -> TripDescriptor:
    ...
```

注意：

```text
第二轮不要让 ALNS 全面替换为 TripDescriptor。
RouteSpec 仍是 ALNS 主结构，TripDescriptor 先用于排序、调试、policy 预判、scheduler 评分。
```

---

## 6. 更符合物理逻辑的改进方向

### 6.1 出发时刻优化：减少等待与拥堵影响

当前 `_preferred_departure_min()` 只保证第一站尽量贴近 earliest。当前结果中：

```text
total_wait_min = 2607.04
max_wait_min = 539.45
```

说明车辆有大量早到等待。由于题面早到等待也计成本，且 08:00--09:00 拥堵严重，有些 trip 等到 09:00 后出发可能更快、更省能耗、更少等待。

建议在 scheduler 层增加可选离散扫描：

```python
def choose_departure_min(problem, spec, vehicle_type_id, available_min, config):
    if config.optimize_departure_grid_min is None:
        return _preferred_departure_min(...)

    candidates = [available_min, available_min + grid, ...]
    upper = min(available_min + config.max_departure_delay_min, descriptor.latest_window_min)
    for depart in candidates:
        route = evaluate_route(... depart_min=depart ...)
        score = route_quality_score(route, config.score_weights)
    return depart with best score
```

默认不启用。建议作为实验参数：

```text
--optimize-departure-grid-min 10
--max-departure-delay-min 180
```

验收：

```text
不增加 late_stop_count 和 max_late_min；
降低 total_wait_min 或 penalty_cost；
不显著增加 total_cost。
```

### 6.2 残余迟到拯救：按诊断结果选择

若诊断显示 Type B：新增 scheduler 层局部搜索。

建议文件：

```text
green_logistics/scheduler_local_search.py
```

优先实现：

```text
move_late_trip_to_new_vehicle
swap_suffix_between_same_type_vehicles
resequence_trips_on_vehicle
```

约束：

```text
只在保持 complete=True、capacity_feasible=True 下接受；
必须使用 schedule 后真实 metrics 判断是否改善；
默认只尝试迟到相关车辆，避免计算爆炸。
```

若诊断显示 Type C：实现 Or-opt。

建议文件：

```text
green_logistics/local_search.py
```

```python
def or_opt_route_spec(problem, spec, vehicle_type_id=None, segment_lengths=(1,2,3)) -> RouteSpec:
    ...
```

策略：

```text
只对 len(service_node_ids) >= 3 的 route 尝试；
使用 evaluate_route 完整时变重算；
按 route_quality_score 接受；
优先作为 ALNS 后处理，不要每次 repair 后全量运行。
```

### 6.3 更多迭代与多 seed 收敛分析

当前 40 次迭代太少，且最优在第 37 次出现，说明还不能证明收敛。

建议新增实验脚本：

```text
problems/experiments/problem1_convergence.py
```

运行：

```text
iterations = [40, 100, 200, 500]
seeds = [20260424, 20260425, 20260426, 20260427, 20260428]
```

输出：

```text
outputs/experiments/problem1_convergence/summary.csv
outputs/experiments/problem1_convergence/best_by_score.csv
outputs/experiments/problem1_convergence/best_by_true_cost.csv
```

比较字段：

```text
total_cost
search_score
late_stop_count
max_late_min
return_after_midnight_count
fixed_cost
energy_cost
carbon_cost
penalty_cost
route_count
physical_vehicle_count
runtime_seconds
```

若 200/500 次明显改善，则更新第一问正式结果；若改善不明显，则维持当前 40 次方案。

### 6.4 车辆类型使用：不要强推小车

当前只用 E1/F1 不必然是问题。原因：

```text
1. 大量虚拟节点超过 1500kg，F2/F3/E2 服务不了；
2. 题面所有车辆启动成本均为 400；
3. 当前代码中燃油车基础能耗不区分 F1/F2/F3，小车没有空载能耗优势；
4. load_factor 使用 current_weight / max_weight，小车对同样载重反而 payload ratio 更高。
```

建议只做诊断，不强制优化：

```text
vehicle_type_feasibility_report.csv
- service_node_id
- demand_weight
- demand_volume
- feasible_vehicle_types
```

若小节点数量足够，再考虑 `small_node_extraction`，否则不做。

### 6.5 17:00 后速度与晚归情景

题面补充说明只给出 8:00--17:00 速度分布。当前代码延续 MEDIUM 到 24:00，并在 24:00 后继续延续。主结果跨午夜为 0，但 71 趟 17:00 后返回、最晚 23:49。

建议：

```text
1. 主模型保留当前假设，但论文中明确写出：17:00 后延续一般时段速度。
2. 增加 early_return_scenario：对 22:00 或 23:00 后返回加软惩罚，而不是硬约束。
3. 输出 after_17_distance_km、after_17_route_count、max_return_time，用于论文解释。
```

不建议：

```text
把 22:00 写成默认硬约束。
```

---

## 7. 第二问前置准备

### 7.1 绿区服务容量预判

新增诊断：

```python
def diagnose_green_zone_capacity(problem):
    ...
```

输出：

```text
green_customer_count
green_service_node_count
green_total_weight
green_total_volume
EV_total_weight_capacity_once
EV_total_volume_capacity_once
E1_capacity_once
E2_capacity_once
green_nodes_feasible_by_E2_count
green_nodes_need_E1_count
```

说明：

```text
第二问 8:00--16:00 禁止燃油车进入绿色配送区。
如果 EV 一趟总容量不足以覆盖绿区需求，则第二问必须依赖多趟 EV、16:00 后燃油服务、或等待/重排策略。
```

### 7.2 第一问解中的绿区政策冲突预判

新增诊断：

```python
def diagnose_problem2_policy_conflicts(problem, solution):
    ...
```

输出第一问解中：

```text
fuel_vehicle_id
trip_id
service_node_id
customer_id
arrival_min
is_green_zone
would_violate_problem2_policy
```

这将直接告诉第二问需要重排的范围。

### 7.3 PolicyEvaluator 接口

新增：

```text
green_logistics/policies.py
```

接口：

```python
class PolicyEvaluator(Protocol):
    def route_penalty(self, problem, route) -> float: ...
    def is_route_allowed(self, problem, route) -> bool: ...
    def stop_penalty(self, problem, stop, vehicle_type_id) -> float: ...
```

第一问：

```python
NoPolicyEvaluator
```

第二问：

```python
GreenZonePolicyEvaluator
```

注意配送中心在 `(0,0)`，也就是绿色区圆心。第二问必须明确：

```text
配送中心视作政策豁免点；
限制主要作用于燃油车在 8:00--16:00 服务绿色区客户。
```

---

## 8. 不建议现在做的事情

### 8.1 不建议完整重构为方案 C

原因：

```text
第一问已达标；
完整重构风险大；
第二问政策细节尚未落地；
当前 RouteSpec / Route / Solution 已经稳定且经过测试。
```

### 8.2 不建议默认 22:00 硬约束

原因：

```text
题面没有司机工时或返库截止；
软时间窗已是题面给定机制；
22:00 可作为情景参数，不应成为主模型事实。
```

### 8.3 不建议强行使用 F2/F3/E2

原因：

```text
题面所有车型固定成本相同；
当前能耗模型不区分燃油车型基础能耗；
大量服务节点超 1500kg；
强制小车可能只是增加车辆数和成本，不符合当前模型事实。
```

### 8.4 不建议立即做路线池 + Set Partitioning

原因：

```text
route cost 强依赖 scheduled depart_min；
若用 08:00 静态成本做 SP，会回到旧错位问题；
只有在 scheduler 抽象稳定后才适合做 route-pool 后处理。
```

---

## 9. 推荐实施优先级

### P0：锁定当前第一问结果基线

内容：

```text
保存当前输出为 outputs/problem1_baseline_quality_48644/；
记录 summary.json、route_summary.csv、stop_schedule.csv、alns_history.csv；
新增回归测试或脚本验证：complete=True、capacity=True、midnight=0。
```

目的：后续重构不得回退到 84 个迟到或跨午夜。

### P1：残余迟到诊断

新增：

```text
green_logistics/diagnostics.py
outputs/problem1/late_stop_diagnosis.csv
```

若 4 个迟到是 Type A，可停止追 0 迟到；若是 Type B/C，再做针对性修复。

### P2：C-lite 职责重构

新增：

```text
green_logistics/scheduler.py
green_logistics/trips.py
SchedulingConfig
TripDescriptor
```

要求行为基本不变。

### P3：收敛与多 seed 实验

新增：

```text
problems/experiments/problem1_convergence.py
```

比较 40/100/200/500 次和多 seed。

### P4：物理逻辑增强

按诊断结果选择：

```text
Type B -> scheduler_local_search.py
Type C -> local_search.py / Or-opt
等待过大 -> departure_grid_search
晚归过多 -> early_return_scenario soft penalty
```

### P5：第二问准备

新增：

```text
green_logistics/policies.py
Green zone capacity diagnostics
Problem 1 policy conflict diagnostics
```

---

## 10. 给 Codex 的下一步说明词

```text
请基于最新第一问结果做第二轮优化与 C-lite 架构整理，不要推倒重写。

当前最新结果已经达标：
- total_cost = 48644.68
- late_stop_count = 4
- max_late_min = 31.60
- return_after_midnight_count = 0
- route_count = 116
- physical_vehicle_usage = {'E1': 10, 'F1': 33}
- complete=True
- capacity_feasible=True
- pytest 已通过 32 tests

下一步目标不是继续盲目压迟到，而是：
1. 诊断 4 个残余迟到是否物理可避免；
2. 抽出 scheduler.py，清理 initial_solution.py 职责；
3. 增加 TripDescriptor / SchedulingConfig，为第二问和第三问准备；
4. 做更多迭代和多 seed 收敛实验；
5. 只在诊断显示有必要时，实现 Or-opt 或 scheduler-level local search。

请按顺序实现：

P0. 锁定当前结果基线
- 保留当前 outputs/problem1 结果；
- 确保 summary.json 中 quality_metrics 完整；
- 保证 pytest 通过。

P1. 新增 green_logistics/diagnostics.py
实现：
- diagnose_late_stops(problem, solution)
- diagnose_green_zone_capacity(problem)
- diagnose_problem2_policy_conflicts(problem, solution)

late stop 诊断要输出：
- service_node_id / customer_id
- route / trip / vehicle
- arrival_min / latest_min / late_min
- direct_arrival_from_depot_0800
- direct_late_min
- trip_position_on_vehicle
- classification: Type A direct-infeasible / Type B multi-trip cascade / Type C route-order local-optimum

输出文件：
- outputs/problem1/late_stop_diagnosis.csv
- outputs/problem1/green_zone_capacity.csv
- outputs/problem1/problem2_policy_conflicts.csv

P2. 新增 green_logistics/scheduler.py
从 initial_solution.py 迁出：
- schedule_route_specs
- _candidate_vehicle_type_ids
- _preferred_departure_min
- _scheduling_selection_score
- vehicle pool / available_min 逻辑
initial_solution.py 仅保留 RouteSpec 和初始 RouteSpec 构造，并保留兼容导入。

P3. 新增 SchedulingConfig
字段建议：
- score_weights: SearchScoreWeights
- forbid_midnight=False
- midnight_penalty=1_000_000.0
- scenario_return_limit_min=None
- reload_time_min=0.0
- prefer_on_time=True
- optimize_departure_grid_min=None
- max_departure_delay_min=180.0
注意：22:00 返库不能作为默认硬约束，只能作为 scenario_return_limit_min 的情景参数；题面没有给这个硬约束。

P4. 新增 green_logistics/trips.py
定义 TripDescriptor：
- vehicle_type_id
- service_node_ids
- customer_ids
- total_weight_kg
- total_volume_m3
- earliest_window_min
- latest_window_min
- preferred_departure_min
- estimated_duration_min
- min_latest_slack_min
- is_green_zone_touched
- green_stop_count
实现 describe_route_spec(problem, spec)。
先只用于 scheduler 排序、调试和第二问预判，不要立即替换 RouteSpec。

P5. 收敛实验
新增 problems/experiments/problem1_convergence.py，运行：
- iterations: 40, 100, 200, 500
- seeds: 至少 5 个
输出 total_cost、search_score、late_stop_count、max_late_min、midnight_count、runtime。
若长迭代能显著改善，再更新正式结果；否则保留当前 40 次方案。

P6. 只在诊断支持时做局部搜索
- 若残余迟到 Type B：做 scheduler_local_search.py，尝试 move_late_trip_to_new_vehicle、swap_suffix_between_same_type_vehicles。
- 若残余迟到 Type C：做 local_search.py，实现 Or-opt。不要先做时变 2-opt。
- 若 total_wait_min / max_wait_min 过大：在 scheduler 中实现可选 departure_grid_search，默认关闭。

硬性要求：
- 不改 load_problem_data() 稳定入口；
- 不破坏 service_node_id/customer_id 距离查表；
- complete=True；
- capacity_feasible=True；
- return_after_midnight_count=0；
- late_stop_count 不应明显恶化，最好 <=4；
- max_late_min 不应明显恶化，最好 <=31.60；
- true total_cost 不应大幅恶化；
- pytest 必须全部通过。
```

---

## 11. 最终建议

第一问当前主解已经达标。第二轮优化不应继续把全部精力放在“迟到从 4 降到 0”，而应把重点转向：

```text
1. 残余迟到诊断；
2. C-lite 架构整理；
3. 收敛/鲁棒实验；
4. 17:00 后速度假设与晚归敏感性；
5. 第二问政策接口与绿区容量预判。
```

这样既不会浪费当前已经有效的求解器，也能让后续第二问、第三问更稳、更可解释、更符合题目物理逻辑。
