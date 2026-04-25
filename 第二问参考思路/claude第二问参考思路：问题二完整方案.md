# 第二问完整方案：绿色配送区限行政策下的车辆调度策略

> **文档版本**：2026-04-25  
> **基于**：第一问正式结果（总成本 48,644.68 元，116 趟次，10 E1 + 33 F1）  
> **定位**：数学建模方案 + 实现规范 + Codex 编码指导  
> **要求**：符合题意，符合物理规律，不得引入题目未定义的约束

---

## 0. 前置：把题目要求说清楚

### 0.1 题目原文核心要求（逐字解析）

> "在问题 1 的基础上，加入绿色配送区限行政策：**8:00–16:00 禁止燃油车进入**'绿色配送区'（以市中心为圆心的半径 10 千米的圆形范围为'绿色配送区'）。请**重新规划车辆调度路径**，并给出该政策对**总成本、车辆使用结构与碳排放总量**的影响。"

逐条解析：

| 要素 | 解析 | 建模含义 |
|---|---|---|
| "绿色配送区" | 以市中心 (0,0) 为圆心，半径 10km 的圆形区域 | 用**坐标直线距离** √(x²+y²) ≤ 10 判断，与路网距离无关 |
| "禁止燃油车进入" | 燃油车（F1/F2/F3）不得停靠绿区内的客户点 | 约束作用于**服务停靠点**，而非经过路径 |
| "8:00–16:00" | 限行时段为半开区间 [480, 960) 分钟 | 到达时刻 t_arr < 960 才触发约束；t_arr ≥ 960 的燃油车不受限 |
| "重新规划" | 必须全局重优化，不是局部修补 | 需要重新运行完整 ALNS 流程，以限行约束为硬约束 |
| "总成本/车辆结构/碳排放" | 三项对比输出 | 输出格式：问题二结果 vs 问题一基线的差值和百分比 |

### 0.2 明确不在题目中的内容（禁止加入）

- ❌ 燃油车完全不能进入绿区（题目只限制 8:00–16:00，16:00 后可以进）
- ❌ 新能源车在绿区有特别优惠或减少成本
- ❌ 任何"充电桩"、"续航焦虑"等题目未定义的约束
- ❌ 绿区客户必须由新能源车服务（16:00 后燃油车也可以服务）
- ❌ 22:00 硬返库约束（题目无此规定）

---

## 1. 现状诊断：第一问方案的第二问合规性分析

### 1.1 已知的 Problem 2 预检结论（来自 `diagnostics.py`）

| 指标 | 数值 |
|---|---|
| 绿区虚拟服务节点数 | 19 个 |
| 绿区总重量需求 | 35,970.65 kg |
| 绿区总体积需求 | 103.96 m³ |
| 仅 E2 够用的绿区节点数 | 4 个（需求 ≤ 1250 kg） |
| 需要 E1 级别（3000 kg）的绿区节点数 | 15 个 |
| 第一问方案中存在的限行冲突 | **有**（燃油车在 8:00-16:00 服务了绿区节点） |

### 1.2 关键可行性预判：EV 容量够不够？

**计算过程：**

```
可用新能源车：10 辆 E1（3000 kg/15 m³）+ 15 辆 E2（1250 kg/8.5 m³）

绿区总需求：35,970.65 kg，103.96 m³

E1 可覆盖的绿区重量（单趟）：10 × 3000 = 30,000 kg < 35,970.65 kg
→ 单趟覆盖不够，需要多趟或部分时间段外燃油车补充

E1 双趟重量上限：10 × 3000 × 2 = 60,000 kg > 35,970.65 kg
→ 双趟在时间上可行吗？

绿区中心距配送中心（20,20）的典型距离：约 35-45 km（实际路网）
一趟服务 2-3 个绿区节点：行程约 80-100 km
顺畅时段（13:00-15:00）速度 55.3 km/h → 约 90 min 往返
顺畅时段一趟：约 2-2.5 小时

8:00 到 16:00 = 480 分钟
E1 可以完成的绿区趟次数：480 / 150 ≈ 3 趟
10 辆 E1 × 3 趟 × 3000 kg = 90,000 kg >> 35,970 kg
→ E1 时间容量完全充足
```

**结论：问题二在理论上完全可行。**  
- 10 辆 E1 可以在限行时段内多次往返绿区完成服务
- EV 不需要专门用于绿区——只需要让调度器优先把绿区节点分配给 EV
- 剩余非绿区节点仍由燃油车正常服务

### 1.3 存在真实冲突的情况：16:00 后窗口兜底

部分绿区客户时间窗可能在限行时段内（8:00–16:00）无法由现有 EV 完成（例如 EV 全忙、时间冲突），此时有两种合法兜底方案：

**方案A**：16:00 后燃油车服务（合法，题目只限 8:00-16:00）
- 条件：`t_arr_fuel_vehicle >= 960`（16:00）且在时间窗内
- 优先级：次选（惩罚成本较高，因为一般要等到 16:00）

**方案B**：EV 重新调度（优先）
- 重新为该绿区节点分配一辆有空余时间段的 EV
- 即使 EV 已经做了一趟，只要当前物理车有时间，就继续安排第二趟

---

## 2. 数学模型扩展

### 2.1 新增约束定义

在第一问模型的基础上，加入一条硬约束：

$$\text{（绿区限行约束）} \quad x_{ijk}^r = 0 \quad \forall (i,j,k,r) : i \in \mathcal{G},\; k \in \mathcal{K}_F,\; 480 \leq t_i^{arr} < 960$$

其中：
- $\mathcal{G} = \{2,3,4,5,6,7,8,9,10,11,12,13\}$ 为有效绿区客户集合（12 个）
- $\mathcal{K}_F = \{F1, F2, F3\}$ 为燃油车型集合
- $t_i^{arr}$ 为到达客户 $i$ 的实际时刻（分钟）

**等价表述（编码用）：**

```python
def is_green_zone_violation(customer_id: int, vehicle_type: str, arrival_time: float) -> bool:
    """
    检查是否违反绿色配送区限行约束。
    返回 True 表示违规（不可行）。
    
    注意事项：
    1. 判断依据是到达时间（进入绿区的时刻），不是出发时间
    2. 限行区间是半开区间 [480, 960)：16:00 到达不违规
    3. 绿区判断基于客户坐标距原点距离，不基于路网距离
    4. 虚拟节点（拆分后）的绿区属性继承自其父客户
    """
    if customer_id not in GREEN_ZONE_CUSTOMER_IDS:
        return False  # 非绿区客户，不受限
    if vehicle_type not in FUEL_VEHICLE_TYPES:
        return False  # 新能源车，不受限
    # 燃油车在限行时段内到达绿区 = 违规
    return 480.0 <= arrival_time < 960.0

GREEN_ZONE_CUSTOMER_IDS = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13}
FUEL_VEHICLE_TYPES = {"F1", "F2", "F3"}
```

### 2.2 目标函数不变

第二问的目标函数与第一问相同：

$$\min Z = C_{fixed} + C_{energy} + C_{carbon} + C_{penalty}$$

**不引入额外惩罚项**。限行约束作为硬约束处理，违约路线在搜索中直接视为不可行并以无穷大成本拒绝。

### 2.3 新的最优性含义

第二问的最优解与第一问相比：
- **必然 ≥ 第一问总成本**（额外约束不会降低最优值）
- **碳排放预期下降**（绿区内燃油车被 EV 替换）
- **EV 使用数量预期上升**（EV 承担更多绿区路线）
- **总成本增量 = 政策代价**（第二问最优 - 第一问最优）

---

## 3. 关键决策：对第一问架构的修改程度

### 3.1 不需要重写第一问

第一问的现有架构（ALNS + scheduler.py + policies.py）已经为第二问预留了接口。**不应该修改第一问的正式结果和代码**，而应新建 `problems/problem2.py` 作为独立求解脚本。

第一问最优解是无约束下的最优；第二问是有约束下的最优。二者分别是独立的优化问题，用于对比分析。

### 3.2 需要新增/修改的内容

| 模块 | 操作 | 说明 |
|---|---|---|
| `green_logistics/policies.py` | 完成 `GreenZonePolicyEvaluator` | 当前只是骨架，需要实现完整逻辑 |
| `green_logistics/operators.py` | 新增 `GreenZoneSegregationDestroy` | 专门针对绿区限行冲突的破坏算子 |
| `green_logistics/operators.py` | 新增 `VehicleTypeSwapRepair` | 绿区节点强制改为 EV 的修复算子 |
| `green_logistics/initial_solution.py` | 新增 `build_green_zone_first_initial_solution()` | 绿区优先的初始解构建 |
| `problems/problem2.py` | 新建 | 问题二求解主脚本 |
| `green_logistics/output.py` | 新增 `compare_p1_p2()` | 对比输出函数 |

**不需要修改**：`travel_time.py`, `cost.py`, `solution.py`, `scheduler.py`, `metrics.py`

---

## 4. 核心算法设计

### 4.1 完善 `GreenZonePolicyEvaluator`

```python
# green_logistics/policies.py

class GreenZonePolicyEvaluator:
    """
    问题二：绿色配送区限行政策评估器。
    
    物理约束：8:00-16:00（分钟480-960），燃油车不得停靠绿区内客户点。
    判断方式：基于到达时间 t_arr 和客户坐标距原点距离 ≤ 10km。
    16:00 后（t_arr ≥ 960）燃油车可以进入绿区。
    """
    
    RESTRICTION_START = 480.0   # 8:00
    RESTRICTION_END   = 960.0   # 16:00（不含）
    
    def __init__(self, green_zone_ids: set):
        self.green_zone_ids = green_zone_ids  # 有效绿区客户ID集合
    
    def check_route(self, route, vehicle_type: str, data) -> bool:
        """
        检查一条路线在给定车型下是否违反限行约束。
        返回 True = 合规，False = 违规。
        """
        if vehicle_type not in ("F1", "F2", "F3"):
            return True  # 新能源车无限制，始终合规
        
        for node, arrival in zip(route.service_nodes, route.arrival_times):
            cid = data.node_to_customer[node.id]
            if (cid in self.green_zone_ids and 
                self.RESTRICTION_START <= arrival < self.RESTRICTION_END):
                return False  # 违规：燃油车在限行时段服务绿区客户
        return True
    
    def find_violations(self, route, vehicle_type: str, data) -> list:
        """返回所有违规停靠点的列表，用于诊断和破坏算子。"""
        if vehicle_type not in ("F1", "F2", "F3"):
            return []
        violations = []
        for node, arrival in zip(route.service_nodes, route.arrival_times):
            cid = data.node_to_customer[node.id]
            if (cid in self.green_zone_ids and
                self.RESTRICTION_START <= arrival < self.RESTRICTION_END):
                violations.append((node, arrival, cid))
        return violations
    
    def can_fuel_serve_after_restriction(
        self, node, data, current_time: float
    ) -> tuple:
        """
        检查燃油车是否能在 16:00 后（t_arr ≥ 960）合法服务绿区节点。
        返回 (feasible: bool, earliest_feasible_arrival: float)
        
        这是兜底策略：若 EV 容量不足，燃油车在 16:00 后服务绿区是合法的。
        """
        cid = data.node_to_customer[node.id]
        if cid not in self.green_zone_ids:
            return (True, current_time)  # 非绿区，无限制
        
        tw_start, tw_end = data.time_windows[cid]
        # 燃油车最早可进入绿区的合法时刻
        earliest_legal = max(self.RESTRICTION_END, tw_start)
        
        if earliest_legal > tw_end:
            return (False, None)  # 16:00 后已超过时间窗，不可行
        return (True, earliest_legal)
```

### 4.2 绿区优先初始解

关键思路：**先为所有绿区虚拟节点指定 EV，再用贪心构建剩余路线。**

```python
# green_logistics/initial_solution.py 中新增

def build_green_zone_first_initial_solution(data, policy):
    """
    问题二专用初始解构建：绿区节点优先分配给新能源车。
    
    步骤：
    1. 将所有绿区虚拟节点（19个）分配给 E1/E2，构建 EV-only 路线
    2. 剩余 129 个非绿区虚拟节点用标准贪心构建燃油车路线
    3. 确保所有路线通过 policy.check_route() 验证
    
    关键保证：
    - E1/E2 共 25 辆，容量理论上足够（详见第 1.2 节预判）
    - 若 E1 容量不足，将剩余绿区节点安排在 16:00 后的 F1 路线（合法兜底）
    """
    green_nodes = [n for n in data.service_nodes if n.customer_id in policy.green_zone_ids]
    non_green_nodes = [n for n in data.service_nodes 
                       if n.customer_id not in policy.green_zone_ids]
    
    ev_route_specs = []
    fuel_route_specs = []
    
    # === Phase 1：绿区节点 → EV ===
    # 按时间窗截止时间排序（最紧急的优先）
    green_sorted = sorted(green_nodes, key=lambda n: data.time_windows[n.customer_id][1])
    
    # 贪心插入 E1（大容量 EV）
    e1_routes = greedy_insert_to_vehicle_type(
        green_sorted, vehicle_type="E1", data=data, policy=policy
    )
    
    # 未放入 E1 的节点（可能因时间窗冲突）尝试 E2
    remaining_green = [n for n in green_sorted 
                       if not any(n in r.service_nodes for r in e1_routes)]
    e2_routes = greedy_insert_to_vehicle_type(
        remaining_green, vehicle_type="E2", data=data, policy=policy
    )
    
    # 仍未覆盖的绿区节点：安排在 16:00 后的 F1（合法兜底）
    still_remaining = [n for n in remaining_green 
                       if not any(n in r.service_nodes for r in e2_routes)]
    if still_remaining:
        fuel_green_routes = build_post_restriction_fuel_routes(
            still_remaining, data, earliest_departure=960.0
        )
        fuel_route_specs.extend(fuel_green_routes)
    
    ev_route_specs = e1_routes + e2_routes
    
    # === Phase 2：非绿区节点 → 任意车型（优先 F1）===
    fuel_route_specs += build_standard_routes(non_green_nodes, data)
    
    return ev_route_specs + fuel_route_specs
```

### 4.3 专用破坏算子：`GreenZoneViolationDestroy`

```python
# green_logistics/operators.py 中新增

def green_zone_violation_destroy(solution, data, policy, rng):
    """
    破坏算子：专门针对绿区限行违规的路线进行破坏。
    
    逻辑：
    1. 找出所有存在限行违规的路线（燃油车在 8:00-16:00 服务绿区节点）
    2. 从这些路线中提取违规节点
    3. 返回被移除的节点列表（供修复算子处理）
    
    使用场景：在 ALNS 早期迭代中高频调用，快速消除初始解的违规情况。
    """
    violated_nodes = []
    violated_routes = []
    
    for route in solution.routes:
        vtype = route.vehicle_type
        violations = policy.find_violations(route, vtype, data)
        if violations:
            violated_nodes.extend([v[0] for v in violations])  # 提取节点
            violated_routes.append(route.id)
    
    if not violated_nodes:
        return [], violated_routes  # 无违规，不破坏
    
    # 移除违规节点
    for route in solution.routes:
        if route.id in violated_routes:
            for node in violated_nodes:
                if node in route.service_nodes:
                    route.remove_node(node)
    
    return violated_nodes, violated_routes


def vehicle_type_swap_repair(removed_nodes, solution, data, policy, rng):
    """
    修复算子：将绿区节点强制插入 EV 路线（或 16:00 后的燃油车路线）。
    
    逻辑：
    1. 按绿区节点的时间窗紧迫程度排序
    2. 对每个节点：
       a. 首选：插入现有 EV 路线的最低成本位置
       b. 次选：开新 EV 趟次（若 EV 数量未超上限）
       c. 兜底：插入时间调整后的燃油车路线（到达时间 ≥ 16:00）
    """
    green_nodes = [n for n in removed_nodes 
                   if n.customer_id in policy.green_zone_ids]
    non_green_nodes = [n for n in removed_nodes 
                       if n.customer_id not in policy.green_zone_ids]
    
    # 非绿区节点用标准 Greedy Insert 处理
    standard_greedy_insert(non_green_nodes, solution, data)
    
    # 绿区节点优先插入 EV 路线
    for node in sorted(green_nodes, key=lambda n: data.time_windows[n.customer_id][1]):
        ev_routes = [r for r in solution.routes 
                     if r.vehicle_type in ("E1", "E2")]
        
        best_cost = float('inf')
        best_position = None
        
        for route in ev_routes:
            for pos in range(1, len(route.nodes)):
                cost_delta = compute_insertion_cost(route, node, pos, data)
                if cost_delta < best_cost and is_capacity_feasible(route, node, data):
                    best_cost = cost_delta
                    best_position = (route, pos)
        
        if best_position:
            route, pos = best_position
            route.insert_node(node, pos)
        else:
            # EV 全忙：检查 16:00 后燃油车兜底是否可行
            feasible, earliest = policy.can_fuel_serve_after_restriction(node, data, 960.0)
            if feasible:
                # 开新趟次，出发时刻设为 earliest（≥ 16:00）
                new_route = RouteSpec(
                    service_node_ids=[node.id],
                    vehicle_type="F1",  # 16:00 后可用燃油车
                    preferred_depart=earliest
                )
                solution.add_route(new_route)
            else:
                # 真正的不可行（理论上不应发生，记录日志）
                logger.warning(f"无法在任何合法时间窗内服务绿区节点 {node.id}")
```

### 4.4 `problems/problem2.py` 主脚本框架

```python
# problems/problem2.py

import argparse
from green_logistics.data_processing import load_problem_data
from green_logistics.policies import GreenZonePolicyEvaluator
from green_logistics.initial_solution import build_green_zone_first_initial_solution
from green_logistics.alns import run_alns_with_policy
from green_logistics.scheduler import Scheduler, SchedulingConfig
from green_logistics.output import save_solution, compare_solutions
from green_logistics.diagnostics import verify_green_zone_compliance

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=80)
    parser.add_argument("--remove-count", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260424)
    parser.add_argument("--output-dir", default="outputs/problem2")
    parser.add_argument("--p1-result", default="outputs/problem1/solution.json",
                        help="问题一结果路径，用于对比分析")
    args = parser.parse_args()
    
    # 1. 加载数据
    data = load_problem_data(".")
    
    # 2. 激活绿区限行政策（第一问用 NoPolicyEvaluator，第二问用这个）
    policy = GreenZonePolicyEvaluator(
        green_zone_ids={2,3,4,5,6,7,8,9,10,11,12,13}
    )
    
    # 3. 绿区优先初始解
    initial_specs = build_green_zone_first_initial_solution(data, policy)
    
    # 4. 验证初始解合规性
    initial_solution = Scheduler(data).schedule(initial_specs)
    violations_before = verify_green_zone_compliance(initial_solution, data, policy)
    print(f"初始解违规数: {violations_before}")
    
    # 5. ALNS（含限行约束）
    best_solution = run_alns_with_policy(
        initial_solution=initial_solution,
        data=data,
        policy=policy,
        iterations=args.iterations,
        remove_count=args.remove_count,
        seed=args.seed,
        # 特别说明：前 20% 迭代高频调用 green_zone_violation_destroy
        # 剩余迭代回归标准算子池
        policy_operator_warmup_fraction=0.20
    )
    
    # 6. 最终合规验证
    violations_after = verify_green_zone_compliance(best_solution, data, policy)
    assert violations_after == 0, f"最终解仍有 {violations_after} 处违规！"
    
    # 7. 保存结果并生成对比报告
    save_solution(best_solution, data, args.output_dir)
    compare_solutions(
        p1_path=args.p1_result,
        p2_solution=best_solution,
        data=data,
        output_dir=args.output_dir
    )
    
    print(f"问题二总成本: {best_solution.total_cost:.2f}")
    print(f"问题一基线:   48644.68")
    print(f"政策代价:     {best_solution.total_cost - 48644.68:+.2f} 元")

if __name__ == "__main__":
    main()
```

---

## 5. ALNS 策略调整

### 5.1 算子权重初始化

问题二与问题一的关键差异：**初始存在大量限行违规**，需要在搜索早期快速消除违规，再进行成本优化。建议分两阶段设置算子权重：

```python
# ALNS 算子权重配置（问题二专用）

WARMUP_WEIGHTS = {
    # 破坏算子（前 20% 迭代）
    "green_zone_violation_destroy": 5.0,   # 高权重：专门消除违规
    "worst_cost_remove":            1.0,
    "random_remove":                1.0,
    "related_remove":               0.5,
    "actual_late_remove":           0.5,
    
    # 修复算子（前 20% 迭代）
    "vehicle_type_swap_repair":     5.0,   # 高权重：强制绿区→EV
    "greedy_insert":                1.0,
    "regret_insert":                0.5,
}

NORMAL_WEIGHTS = {
    # 破坏算子（后 80% 迭代，回归标准配置）
    "green_zone_violation_destroy": 1.0,   # 维持合规
    "worst_cost_remove":            2.0,   # 成本优化为主
    "random_remove":                1.5,
    "related_remove":               1.5,
    "actual_late_remove":           1.0,
    "late_suffix_remove":           0.5,
    
    # 修复算子
    "vehicle_type_swap_repair":     1.0,
    "greedy_insert":                2.0,
    "regret_insert":                1.5,
    "time_oriented_insert":         1.0,
}
```

### 5.2 SA 接受准则（与第一问相同）

不需要修改接受准则。但由于问题二的可行解空间更小（多了限行约束），建议：
- **初始温度适当降低**（可行解更集中，不需要大幅跳变）
- **降温速率不变**

---

## 6. 对比分析输出规范

### 6.1 必须输出的三项对比

**（1）总成本对比**

| 成本项 | 问题一 | 问题二 | 差值 | 变化率 |
|---|---|---|---|---|
| 固定启动成本 | 17,200.00 | ___ | ___ | ___ |
| 燃料/电能成本 | 25,091.79 | ___ | ___ | ___ |
| 碳排成本 | 5,419.37 | ___ | ___ | ___ |
| 时间窗惩罚 | 933.53 | ___ | ___ | ___ |
| **总成本** | **48,644.68** | **___** | **___** | **___** |

**（2）车辆使用结构对比**

| 车型 | 问题一数量 | 问题二数量 | 变化 | 说明 |
|---|---|---|---|---|
| F1（燃油大型） | 33 辆 | ___ | ___ | 绿区限行减少使用 |
| F2（燃油中型） | 0 辆 | ___ | ___ | |
| F3（燃油小型） | 0 辆 | ___ | ___ | |
| E1（新能源大型） | 10 辆 | ___ | ___ | 绿区限行增加使用 |
| E2（新能源小型） | 0 辆 | ___ | ___ | |
| **合计** | **43 辆** | **___** | **___** | |

**（3）碳排放对比**

| 指标 | 问题一 | 问题二 | 差值 | 变化率 |
|---|---|---|---|---|
| 总碳排放量（kg） | 8,337.49 | ___ | ___ | ___ |
| 绿区内碳排放（kg） | ___ | 0（如果绿区全由EV服务） | ___ | -100% |
| 非绿区碳排放（kg） | ___ | ___ | ___ | ___ |

### 6.2 政策效果的量化表述模板

论文中应包含以下结论性表述：

> "绿色配送区限行政策（8:00-16:00 燃油车禁入）使总配送成本增加 X 元（+Y%），主要来源于新能源车辆使用比例提升和路线重构带来的额外里程。在碳排放方面，政策使绿区内配送碳排放降至 0，全局碳排放总量降低 Z kg（-W%），说明限行政策在一定成本代价下显著改善了城市核心区的碳排放水平。"

---

## 7. 深度创新：时段-区域联合敏感性分析

这是第二问的核心创新点，也是与其他参赛队区分度最高的部分。

### 7.1 创新点一：绿区客户的"服务时段弹性"分析

对每个绿区客户 $i \in \mathcal{G}$，定义其**服务时段弹性**（Temporal Service Flexibility, TSF）：

$$\text{TSF}(i) = \frac{\max(0, \; t_i^{latest} - 960)}{t_i^{latest} - t_i^{earliest}}$$

- TSF = 0：客户时间窗完全在限行时段内（只能由 EV 服务）
- TSF = 1：客户时间窗完全在 16:00 之后（燃油车也可以服务）
- 0 < TSF < 1：部分时段弹性（EV 优先，燃油车可以在 16:00 后服务）

这个指标可以：
1. 事先判断绿区客户对 EV 资源的竞争强度
2. 指导初始解构建（TSF=0 的节点绝对优先分配 EV）
3. 在论文中展示绿区客户的异质性，体现模型的精细程度

```python
def compute_temporal_service_flexibility(customer_id: int, data, policy) -> float:
    """
    计算绿区客户的服务时段弹性。
    TSF = 0 表示只能由 EV 服务；TSF = 1 表示燃油车也完全可以服务。
    """
    if customer_id not in policy.green_zone_ids:
        return 1.0  # 非绿区客户，无限制
    
    tw_start, tw_end = data.time_windows[customer_id]
    window_width = tw_end - tw_start
    
    if window_width <= 0:
        return 0.0
    
    # 16:00 后可用的时间窗宽度
    after_restriction = max(0, tw_end - policy.RESTRICTION_END)
    return after_restriction / window_width
```

**预期结论**（基于数据特征）：由于时间窗平均宽度仅 72 分钟，且大多数绿区客户的时间窗在白天，预计 TSF=0 的比例较高（纯 EV 服务），这验证了 EV 在绿区的不可替代性。

### 7.2 创新点二：限行时段扩展的边际成本分析

分析如果限行时段从 "8:00-16:00" 扩展到 "全天"，成本和碳排放的变化。

这是一个情景分析（Scenario Analysis），用于回答：**当前政策（8:00-16:00）是否是一个经济上合理的折中点？**

```python
RESTRICTION_SCENARIOS = [
    (480, 600),   # 8:00-10:00（仅早高峰拥堵时段）
    (480, 780),   # 8:00-13:00（上午限行）
    (480, 960),   # 8:00-16:00（题目给定）
    (480, 1020),  # 8:00-17:00（扩展至晚高峰）
    (0, 1440),    # 全天禁止（极端情景）
]
```

对每个情景，运行一次问题二求解，记录总成本和碳排放，绘制成曲线：
- 横轴：限行时段长度（小时）
- 左纵轴：总成本增量（与第一问基线的差值）
- 右纵轴：碳排放减少量（kg）

这个分析能展示出"成本-减排帕累托边界"，具有很强的政策含义。

### 7.3 创新点三：EV 车队规模弹性分析

分析如果新能源车数量从当前 (10 E1 + 15 E2) 变化，问题二的总成本和可行性如何变化。

```python
EV_FLEET_SCENARIOS = [
    {"E1": 5,  "E2": 15},   # 减少 E1
    {"E1": 10, "E2": 15},   # 题目给定（基线）
    {"E1": 15, "E2": 15},   # 增加 E1
    {"E1": 10, "E2": 25},   # 增加 E2
    {"E1": 20, "E2": 20},   # 大幅扩充 EV
]
```

这个分析回答：**配送公司需要投资多少新能源车才能在不增加成本的情况下满足限行政策？**

---

## 8. 避坑清单（Codex 必读）

### Pit 1：限行约束的判断时机

```python
# ❌ 错误：用出发时间判断
if departure_time < 960 and vehicle_type in FUEL:
    violation = True

# ✅ 正确：用到达时间判断（进入绿区的时刻）
if 480 <= arrival_time < 960 and vehicle_type in FUEL:
    violation = True
```

**原因**：限行约束针对的是"进入绿区"的时刻，即到达客户的时刻，而非从配送中心出发的时刻。

### Pit 2：绿区判断用坐标距离，不用路网距离

```python
# ❌ 错误：用距离矩阵判断是否在绿区
is_green = distance_matrix[0][customer_id] <= 10

# ✅ 正确：用坐标距离判断
is_green = sqrt(customer_x**2 + customer_y**2) <= 10.0
```

**原因**：距离矩阵第 0 行是到**配送中心（20,20）**的距离，而绿区圆心是**城市中心（0,0）**，两者完全不同。

### Pit 3：虚拟节点的绿区属性继承

```python
# ❌ 错误：只检查原始客户，忘记虚拟节点
is_green_zone_violation(virtual_node.id, ...)  # virtual_node.id 可能是 101-148

# ✅ 正确：通过父客户ID判断
parent_customer_id = data.node_to_customer[virtual_node.id]
is_green_zone_violation(parent_customer_id, ...)
```

**原因**：虚拟节点（拆分后）的 ID 不等于客户 ID，但绿区属性继承自父客户的坐标位置。

### Pit 4：16:00 边界是包含还是不包含

```python
# 题目说"8:00-16:00禁止进入"
# 逻辑上：16:00 到达（t_arr = 960）属于"16:00 之后"，不违规

# ✅ 正确实现：半开区间 [480, 960)
is_restricted = 480.0 <= arrival_time < 960.0
```

### Pit 5：初始解的绿区合规性验证

```python
# 在 problem2.py 运行 ALNS 前，必须验证初始解是否合规
# 如果初始解已经全部合规，ALNS 只需要优化成本
# 如果初始解有违规，需要在 ALNS 早期优先消除违规

initial_violations = verify_green_zone_compliance(initial_solution, data, policy)
if initial_violations > 0:
    print(f"警告：初始解有 {initial_violations} 处违规，将在 ALNS 中修复")
```

### Pit 6：问题二与问题一使用独立的随机种子

```python
# 问题一和问题二分别运行独立的 ALNS，不共享状态
# 确保结果可复现：problem2.py 有自己的 --seed 参数
# 建议问题二种子与问题一不同，以探索不同的搜索方向
```

### Pit 7：成本对比必须使用相同的成本计算口径

```python
# ✅ 正确：两题都使用官方目标函数（软时间窗惩罚不排除）
p1_total = fixed + energy + carbon + penalty  # 48644.68
p2_total = fixed + energy + carbon + penalty  # 待计算

# ❌ 错误：用 p1 的 official_cost 比较 p2 的 search_score
```

---

## 9. 预期结果区间（基于物理推理）

以下是基于问题物理特性的结果预期，供验证解的合理性使用：

| 指标 | 预期范围 | 理由 |
|---|---|---|
| 问题二总成本 | 50,000–58,000 元 | 限行约束增加路线重构成本，但不应超过 20% |
| 固定成本变化 | +400–2,400 元（+1–6辆） | EV 可多趟使用，未必需要大量新增车辆 |
| 碳排放总量 | 6,000–7,500 kg | 绿区 EV 化降低总碳排，但非绿区不变 |
| 绿区碳排放 | 接近 0 | 若绿区完全由 EV 服务 |
| 限行政策政策代价 | 2,000–8,000 元 | 合理范围；超过 10,000 说明算法有问题 |
| 最大迟到（分钟） | ≤ 60 分钟 | 不应因限行约束大幅退化服务质量 |

**如果结果超出这些范围，优先检查：**
1. 是否有违规路线（EV 没有覆盖绿区节点）
2. 是否出现了不必要的新开车辆（EV 多趟能覆盖的却开了新车）
3. 成本计算是否与问题一使用相同口径

---

## 10. 文件结构变更清单

以下文件需要新建或修改（不更改第一问任何已有内容）：

### 新增文件

| 文件路径 | 说明 |
|---|---|
| `problems/problem2.py` | 问题二主求解脚本 |
| `tests/test_problem2_policy.py` | 政策约束的单元测试 |
| `tests/test_green_zone_operators.py` | 新算子的单元测试 |
| `docs/results/problem2_green_zone_policy_summary.md` | 问题二论文摘要 |

### 修改文件

| 文件路径 | 修改内容 |
|---|---|
| `green_logistics/policies.py` | 完善 `GreenZonePolicyEvaluator`（当前是骨架） |
| `green_logistics/operators.py` | 新增 `green_zone_violation_destroy` 和 `vehicle_type_swap_repair` |
| `green_logistics/initial_solution.py` | 新增 `build_green_zone_first_initial_solution()` |
| `green_logistics/output.py` | 新增 `compare_solutions()` 对比输出函数 |
| `green_logistics/diagnostics.py` | 新增 `verify_green_zone_compliance()` 合规验证函数 |
| `green_logistics/alns.py` | 支持 `policy` 参数和分阶段算子权重 |

### 不修改的文件（保持第一问结果不变）

- `green_logistics/travel_time.py`
- `green_logistics/cost.py`
- `green_logistics/solution.py`
- `green_logistics/scheduler.py`（已有 policy 接口）
- `green_logistics/metrics.py`
- `problems/problem1.py`
- `outputs/problem1/` 目录内所有文件

---

## 11. 测试规范

### 最低必须通过的测试

```python
# tests/test_problem2_policy.py

def test_fuel_vehicle_in_green_zone_during_restriction():
    """燃油车在限行时段服务绿区客户 → 违规"""
    policy = GreenZonePolicyEvaluator(GREEN_ZONE_IDS)
    assert policy.is_violation(customer_id=5, vehicle_type="F1", arrival_time=600) is True

def test_fuel_vehicle_in_green_zone_after_restriction():
    """燃油车在 16:00 后服务绿区客户 → 合规"""
    policy = GreenZonePolicyEvaluator(GREEN_ZONE_IDS)
    assert policy.is_violation(customer_id=5, vehicle_type="F1", arrival_time=960) is False
    assert policy.is_violation(customer_id=5, vehicle_type="F1", arrival_time=1080) is False

def test_ev_in_green_zone_always_compliant():
    """新能源车在任何时段服务绿区客户 → 始终合规"""
    policy = GreenZonePolicyEvaluator(GREEN_ZONE_IDS)
    for t in [480, 600, 800, 960, 1100]:
        assert policy.is_violation(customer_id=5, vehicle_type="E1", arrival_time=t) is False

def test_fuel_vehicle_outside_green_zone():
    """燃油车在限行时段服务非绿区客户 → 合规"""
    policy = GreenZonePolicyEvaluator(GREEN_ZONE_IDS)
    assert policy.is_violation(customer_id=50, vehicle_type="F1", arrival_time=600) is False

def test_restriction_boundary_exclusive():
    """限行时段边界：480 违规，960 不违规"""
    policy = GreenZonePolicyEvaluator(GREEN_ZONE_IDS)
    assert policy.is_violation(customer_id=5, vehicle_type="F1", arrival_time=480) is True
    assert policy.is_violation(customer_id=5, vehicle_type="F1", arrival_time=959.9) is True
    assert policy.is_violation(customer_id=5, vehicle_type="F1", arrival_time=960) is False
```

---

## 12. 参考文献说明

本方案的算法设计依据以下文献：

1. **Liu et al. (2023)** "Efficient feasibility checks and an adaptive large neighborhood search algorithm for the time-dependent green vehicle routing problem with time windows"，European Journal of Operational Research 310(1): 133-155  
   → 支持：在 TD-GVRPTW 中使用 ALNS 处理区域-时间联合约束的可行性检查方法

2. **Xu et al. (2023)** "Multi-Trip Vehicle Routing Problem with Time Windows and Resource Synchronization on Heterogeneous Facilities"，Systems 11(8): 412  
   → 支持：多趟次异构车队的两阶段调度框架（ALNS 生成 trips，后处理分配物理车辆）

3. **Zhang et al. (2024)** "Fleet-mix Electric Vehicle Routing Problem for E-commerce"  
   → 支持：混合车队中 EV 按时段（夜间/白天）限制和燃油车限制的建模方式

4. **Browne et al. (2007)** "Low emission zones: the likely effects on the freight transport sector"  
   → 支持：真实城市 LEZ 政策对货运成本的影响通常在 3-15%，验证预期成本增量范围合理

---

*文档结束。基于题目原文和实际数据事实，未引入任何题目外假设。*
