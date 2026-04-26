# 第三问完整方案：动态事件响应下的实时车辆调度策略

> **版本**：2026-04-26  
> **定位**：第三问完整技术方案，含题意分析、数学模型、算法设计、实现规范、情景设计  
> **依赖**：基于第一问正式结果（总成本 48,644.68）和第二问正式结果（总成本 49,239.78）  
> **核心原则**：目标始终是官方总成本最低；绿色限行若继承则为硬约束；不引入题外约束

---

## 零、题意精确解读（红线优先）

### 0.1 原题第三问要求逐字解析

> "配送过程中可能出现**订单取消、新增订单、配送地址变更或时间窗调整**等突发事件。请设计一个能**实时响应**并调整路径的**动态调度策略**，并给出**一个或者几个突发事件**下的车辆调度策略。"

**关键词逐条解析**：

| 关键词 | 解析 | 建模含义 |
|---|---|---|
| "配送过程中" | 事件发生在配送执行阶段，而非规划阶段 | 存在"已完成服务"和"未完成服务"的区分；已完成部分冻结不变 |
| "实时响应" | 方案调整必须在有限时间内完成 | 不能重跑完整 ALNS（太慢）；需快速启发式修复 + 轻量局部重优化 |
| "动态调度策略" | 策略是通用的，不只是单个事件的答案 | 需要设计事件分类处理逻辑，而非枚举所有可能情况 |
| "一个或几个突发事件" | 可以展示 1-3 个典型情景 | 每个情景单独输出调整方案和成本对比 |
| 订单取消 | 某客户取消全部或部分订单 | 从路线中移除对应虚拟服务节点 |
| 新增订单 | 新客户需要配送 | 需要将新节点插入现有路线或开新趟次 |
| 地址变更 | 客户配送地点发生变化 | 更新距离计算节点，重算 ETA 和成本 |
| 时间窗调整 | 客户允许接收货物的时间段发生变化 | 更新软约束参数，重算时间窗惩罚 |

### 0.2 第三问不确定的内容（必须明确假设）

原题**没有给出**以下信息，实现时必须做出假设并在论文中说明：

1. **事件发生时刻**：几点钟触发？哪辆车受影响？→ 必须由我们设计有代表性的情景
2. **新增订单的数据**：重量、体积、地址、时间窗 → 必须人为构造
3. **地址变更的新地址**：现有 98 个客户中的哪个？还是全新地址？→ 建议从现有客户中选择
4. **是否继承绿色限行**：第三问没有明确说继续沿用第二问政策 → 建议以**第一问**（无限行）为基准，体现灵活性；但也可以设计"含绿区限行"情景作为对照

**保守建议**：以第一问 P1 为基准方案（无绿色限行，总成本 48,644.68），这样情景设计更灵活且不受绿区约束限制。可以在情景 C 中加入"绿区限行继续有效"的变体作为附加分析。

---

## 一、整体架构：滚动时域局部重优化（RHO）

### 1.1 设计哲学

第三问的本质是一个**在线随机 VRP**（Online Stochastic VRPTW）问题的简化版本。其核心难点不在于算法复杂度，而在于**状态管理的正确性**：

```
t_now（事件触发时刻）
     ↓
已完成服务 ← 冻结，不可修改
     ↓
正在路上的车辆 ← 只能修改"下一个停靠点之后"的部分
     ↓
未出发的趟次 ← 完全可重排
     ↓
受事件影响的节点集合 ← 局部重优化的目标
```

**不应该做的事**：重跑完整的 ALNS（慢，且不尊重已执行部分）  
**应该做的事**：①冻结已完成部分 → ②构造"残余子问题" → ③快速修复 → ④轻量局部搜索

### 1.2 架构示意

```
基准方案（P1 或 P2 结果）
         │
         ▼
  DynamicEventHandler
  ┌─────────────────────────────────────┐
  │  1. 解析事件类型和参数             │
  │  2. 冻结 t_now 前已完成的节点      │
  │  3. 确定"正在路上"的车辆位置      │  ← 近似规则（见 1.4 节）
  │  4. 构造残余子问题                 │
  └─────────────────────────────────────┘
         │
         ▼
  ResidualProblemSolver
  ┌─────────────────────────────────────┐
  │  Step 1: 确定性快速修复            │  ← 保证产出可行解
  │    - 删除取消节点                  │
  │    - 插入新增节点（Greedy Insert） │
  │    - 更新地址/时间窗参数           │
  │  Step 2: 轻量 ALNS（限时）         │  ← 提升成本质量
  │    - 对残余节点集合做局部搜索      │
  │    - 最多 20-30 次迭代             │
  └─────────────────────────────────────┘
         │
         ▼
  DynamicReoptimizationResult
  ┌─────────────────────────────────────┐
  │  - 调整后完整方案                  │
  │  - 相比基准的成本变化              │
  │  - 路线变动量                      │
  │  - 合规性验证                      │
  └─────────────────────────────────────┘
```

### 1.3 与第一/二问的代码复用关系

| 模块 | 复用方式 | 是否需要修改 |
|---|---|---|
| `data_processing/loader.py` | 直接复用，加载基准数据 | 无需修改 |
| `travel_time.py` | 直接复用 ETA 函数 | 无需修改 |
| `cost.py` | 直接复用能耗/碳排/惩罚计算 | 无需修改 |
| `solution.py` | 直接复用 Route/Solution 数据结构 | 无需修改 |
| `scheduler.py` | 复用物理车辆排班逻辑 | 可能小改：支持"部分冻结" |
| `operators.py` | 复用 Greedy Insert、Worst Remove 等算子 | 无需修改 |
| `alns.py` | 复用 ALNS 主循环，但限制迭代次数 | 小改：支持"只对残余节点搜索" |
| `policies.py` | 若继承绿区限行则复用 | 无需修改 |
| **新增 `dynamic.py`** | 事件类型、状态冻结、残余子问题构造 | **全新** |
| **新增 `problems/problem3.py`** | 第三问主脚本 | **全新** |

---

## 二、数学模型

### 2.1 动态问题状态定义

设基准方案为 $S^* = \{R_1, R_2, \ldots, R_m\}$，其中每条路线 $R_k$ 是一个 depot-to-depot 趟次。

在事件触发时刻 $t_{now}$，定义：

**冻结集合**（Frozen Set）：

$$\mathcal{F}(t_{now}) = \left\{ (k, i) \mid R_k \text{ 中节点 } i \text{ 的到达时刻 } t_i^{arr} < t_{now} \right\}$$

**正在路上的车辆**（In-Transit Vehicles）：

$$\mathcal{T}(t_{now}) = \left\{ k \mid \exists (k,i) \notin \mathcal{F}, \text{ 且 } R_k \text{ 的出发时刻} < t_{now} \right\}$$

**可重排的趟次集合**（Reschedulable Trips）：

$$\mathcal{U}(t_{now}) = \left\{ k \mid R_k \text{ 的出发时刻} \geq t_{now} \right\}$$

### 2.2 各事件类型的数学表述

**事件 1：订单取消**  
客户 $c$ 在时刻 $t_{now}$ 取消订单，$c$ 对应的虚拟服务节点集合为 $\mathcal{N}(c)$。

操作：
$$\forall i \in \mathcal{N}(c): \text{若} (k,i) \notin \mathcal{F}(t_{now}) \Rightarrow \text{从 } R_k \text{ 中移除 } i$$

约束：已完成配送（$(k,i) \in \mathcal{F}$）不可撤回，若已送达则订单取消对成本无影响（物理上已执行）。

**事件 2：新增订单**  
新客户 $c_{new}$ 在时刻 $t_{now}$ 下单，需求为 $(W_{new}, V_{new})$，时间窗为 $[e_{new}, l_{new}]$，坐标为 $(x_{new}, y_{new})$（或使用现有客户的 ID 替代）。

操作：构造新虚拟服务节点 $i_{new}$，将其插入某条满足容量约束的路线的最优位置。

**目标**：最小化插入增量成本：

$$\Delta C_{insert}(i_{new}, R_k, pos) = C(R_k \text{ 插入 } i_{new} \text{ 后}) - C(R_k)$$

**事件 3：地址变更**  
客户 $c$ 的配送地址从原坐标变更为新地址（用另一个现有客户 ID 的坐标替代）。

操作：更新 $c$ 对应虚拟节点的距离查找 ID，对所有包含 $c$ 的未执行路线重新计算 ETA 和成本。

**事件 4：时间窗调整**  
客户 $c$ 的时间窗从 $[e_c, l_c]$ 变为 $[e_c', l_c']$。

操作：更新时间窗参数，重算受影响路线的软时间窗惩罚。若 $l_c' < t_c^{arr}$（已到达但窗口缩短），则惩罚增加；若 $l_c' > l_c$（窗口放宽），则惩罚可能减少。

### 2.3 动态目标函数

动态调整后的目标仍与静态问题相同：

$$\min Z_{dynamic} = C_{fixed}' + C_{energy}' + C_{carbon}' + C_{penalty}'$$

**其中**：
- $C_{fixed}'$：调整后实际使用的物理车辆数 × 400 元（注意：若取消导致某辆车可以取消出发，则固定成本减少）
- $C_{energy}', C_{carbon}'$：只计算**从 $t_{now}$ 开始的未执行路段**（已执行路段成本已是沉没成本，但在对比时计入"全程总成本"）
- $C_{penalty}'$：更新时间窗参数后的重算惩罚

**注意**：动态调整的成本对比分为两种口径：

1. **全程总成本**：基准方案的已执行成本 + 调整后未执行部分成本（用于与基准对比）
2. **增量成本**：调整前后的成本差（用于量化事件代价或收益）

---

## 三、车辆状态近似规则（关键工程决策）

题目没有给出实时轨迹数据，因此需要明确的近似规则来确定"正在路上"的车辆位置。

### 3.1 近似规则定义

```python
def estimate_vehicle_position(route: Route, t_now: float, data) -> VehiclePosition:
    """
    估计在 t_now 时刻物理车辆的状态。
    
    规则：
    1. 找到路线中最后一个 arrival_time < t_now 的节点 i_last（已完成服务）
    2. 找到路线中第一个 arrival_time >= t_now 的节点 i_next（下一目的地）
    
    三种情况：
    (a) 还没出发：route.departure_time >= t_now → 车辆在配送中心
    (b) 已完成所有服务并返回：route.return_time < t_now → 车辆在配送中心
    (c) 正在路上/服务中：
        - 若 t_last_service_end < t_now < eta(i_last, i_next)：正在前往 i_next
        - 若 arrival_i_next <= t_now < departure_i_next：正在服务 i_next
    
    近似：认为"正在路上"的车辆处于 i_last 的位置（已离开但尚未到达 i_next 时，
    用 i_last 作为当前出发点），这是保守估计（不声称拥有精确实时位置）。
    """
    ...
```

**关键假设（必须在论文中声明）**：
> 本文假设在事件触发时刻 $t_{now}$，已完成服务节点的信息可由调度中心实时获取（如通过 GPS 签收确认）。对于"正在前往下一节点途中"的车辆，以其上一个完成服务节点的位置作为当前位置近似，忽略在途距离，这会略微高估后续行程时间。

### 3.2 冻结边界的精确处理

```python
def get_frozen_boundary(route: Route, t_now: float) -> int:
    """
    返回冻结节点的最后一个索引。
    索引 <= frozen_idx 的节点已完成，不可修改。
    索引 > frozen_idx 的节点可以重排（仅限同一趟次内的重排，跨趟次重排需要额外检查）。
    
    特殊情况：
    - 若路线尚未出发（departure_time >= t_now），frozen_idx = 0（只有 depot 冻结）
    - 若路线已完成返回（return_time < t_now），frozen_idx = len(route.nodes) - 1（全部冻结）
    """
    ...
```

---

## 四、算法设计

### 4.1 快速确定性修复（必须先做）

快速修复的目标是在 < 1 秒内产出一个可行方案，为后续 ALNS 提供起点。

```python
def fast_repair(
    base_solution: Solution,
    event: DynamicEvent,
    t_now: float,
    data,
    policy: Optional[PolicyEvaluator] = None
) -> Solution:
    """
    快速确定性修复算法。
    
    输入：基准方案、动态事件、事件时刻
    输出：快速修复后的可行方案（不保证最优）
    
    时间复杂度：O(n) 量级，秒级响应
    """
    
    solution = deepcopy(base_solution)
    
    if event.type == EventType.ORDER_CANCEL:
        # 找到包含取消节点的路线，移除节点，重算时间和成本
        affected_routes = find_routes_with_nodes(solution, event.nodes_to_remove, t_now)
        for route in affected_routes:
            for node in event.nodes_to_remove:
                if node in route.reschedulable_nodes(t_now):
                    route.remove_node(node)
            route.recalculate_times_from(t_now)
        
        # 尝试取消不再需要出发的趟次（节省固定成本）
        # 规则：若某趟次的所有节点都被取消且趟次尚未出发
        solution = cancel_empty_unstarted_trips(solution, t_now)
    
    elif event.type == EventType.NEW_ORDER:
        # Greedy Best-Insert：找成本增量最小的插入位置
        # 只考虑有足够时间余量和容量余量的路线
        new_node = create_virtual_node_for_new_order(event.new_order, data)
        best_insert = find_best_insertion(
            new_node, solution, t_now, data, policy,
            allow_new_trip=True  # 如果没有合适路线，允许开新趟次
        )
        solution = apply_insertion(solution, new_node, best_insert)
    
    elif event.type == EventType.ADDRESS_CHANGE:
        # 更新距离矩阵代理（或坐标），重算受影响路线的 ETA 和成本
        affected_routes = find_routes_with_customer(solution, event.customer_id, t_now)
        for route in affected_routes:
            route.update_customer_address(event.customer_id, event.new_address_id, data)
            route.recalculate_times_from(
                max(t_now, route.departure_time)
            )
    
    elif event.type == EventType.TIME_WINDOW_CHANGE:
        # 更新时间窗参数，重算惩罚
        data.time_windows[event.customer_id] = (event.new_earliest, event.new_latest)
        affected_routes = find_routes_with_customer(solution, event.customer_id, t_now)
        for route in affected_routes:
            route.recalculate_penalty(data)
    
    return solution
```

### 4.2 轻量 ALNS（限时局部优化）

快速修复后，对"可重排区域"做限时 ALNS 优化：

```python
def lightweight_alns(
    repaired_solution: Solution,
    t_now: float,
    data,
    policy: Optional[PolicyEvaluator] = None,
    max_iterations: int = 30,    # 比完整 ALNS 少很多（完整是 40 次，但针对全量节点）
    max_seconds: float = 10.0,   # 硬性时间限制
    seed: int = 42
) -> Solution:
    """
    对可重排部分做轻量 ALNS 优化。
    
    关键约束：
    1. 只移动 t_now 之后尚未执行的节点
    2. 不移动冻结节点（已完成服务）
    3. 不改变正在路上车辆的下一停靠点（保守处理）
    4. 时间硬限制：超时立即返回当前最优解
    """
    
    reschedulable_nodes = get_reschedulable_nodes(repaired_solution, t_now)
    
    if len(reschedulable_nodes) == 0:
        return repaired_solution  # 全部冻结，无需优化
    
    # 使用完整 ALNS 的算子，但只操作 reschedulable_nodes
    return run_alns_on_subset(
        solution=repaired_solution,
        node_subset=reschedulable_nodes,
        data=data,
        policy=policy,
        max_iterations=max_iterations,
        max_seconds=max_seconds,
        seed=seed
    )
```

### 4.3 多事件并发处理

若多个事件同时触发（如情景 C 所设计的），按以下优先顺序串行处理：

```python
EVENT_PRIORITY = [
    EventType.ORDER_CANCEL,          # 优先级 1：取消订单先处理（释放资源）
    EventType.ADDRESS_CHANGE,        # 优先级 2：地址变更（影响路线结构）
    EventType.TIME_WINDOW_CHANGE,    # 优先级 3：时间窗调整（影响惩罚）
    EventType.NEW_ORDER,             # 优先级 4：新增订单最后处理（利用前三步释放的资源）
]
```

**理由**：取消订单先处理，可以释放车辆容量；新增订单最后处理，能利用前步骤释放的容量。这个顺序在物理上也更合理（先知道"少送什么"，再决定"多送什么"）。

---

## 五、情景设计

根据题目要求"给出一个或几个突发事件下的车辆调度策略"，设计以下三个有代表性的情景：

### 情景 A：单一事件——大需求客户取消订单（10:30）

**事件描述**：
- 事件类型：订单取消
- 触发时刻：$t_{now} = 630$ 分钟（10:30）
- 取消客户：客户 50（为原题中有拆分需求的大客户之一）
- 对应虚拟节点：2-3 个（取决于拆分数量）

**选择理由**：
1. 10:30 处于普通时段（10:00-11:30），速度均值 35.4 km/h，ETA 计算典型
2. 大需求客户取消会释放大量车辆容量，可能触发"是否能合并路线/减少车辆"的决策
3. 此时一部分路线已出发，一部分尚未出发，状态混合，最能展示冻结规则

**预期效果**：
- 总成本**下降**（取消订单 → 减少服务节点 → 可能减少物理车辆）
- 路线变动：包含客户 50 虚拟节点的路线被修改，可能有路线被取消
- 论文展示意义：体现"紧急取消"场景中动态调度对成本的积极影响

**验证清单**：
- 客户 50 的所有虚拟节点不再出现在任何路线中
- 其他客户的服务不受影响
- 已出发并服务了部分节点的路线，仍保留冻结部分不变

---

### 情景 B：单一事件——新增紧急订单（09:30）

**事件描述**：
- 事件类型：新增订单
- 触发时刻：$t_{now} = 570$ 分钟（09:30）
- 新增客户参数（构造）：
  - 坐标：使用客户 30 的坐标（现有客户，有对应距离矩阵数据）
  - 需求：重量 800 kg，体积 2.5 m³（单趟可行，适合 F2/F3）
  - 时间窗：[660, 750]（11:00-12:30，有一定紧迫性）
  - 虚拟节点 ID：149（超出原 148 节点的新节点）

**选择理由**：
1. 09:30 正好在顺畅时段（09:00-10:00）末尾，出发窗口有限
2. 需求 800 kg 可以被 F2/F3 服务，考察中小型车辆的调度弹性
3. 时间窗在 11:00-12:30，在插入决策时有实质性约束压力

**关键技术挑战**：
- 新节点 149 没有在原始距离矩阵中，需要用客户 30 的 `customer_id` 代理
- 新节点的绿区属性：客户 30 是否在绿区？如果是，且继承限行政策，则只能分配给 EV

**预期效果**：
- 总成本**上升**（增加服务节点 → 增加行驶距离/可能新开趟次）
- 若能插入现有路线空余段，增量很小；若需开新趟次，增加 400 元固定成本

**验证清单**：
- 新节点 149 被服务恰好一次
- 服务时刻在时间窗 [660, 750] 范围内（或记录超时惩罚）
- 原有 148 个虚拟节点覆盖不受影响

---

### 情景 C：复合事件——地址变更 + 时间窗调整（11:00，绿区继承）

**事件描述**：
- 触发时刻：$t_{now} = 660$ 分钟（11:00）
- 事件 1：地址变更——客户 6（绿区大需求客户）的配送地址变更为客户 40 的坐标（非绿区）
- 事件 2：时间窗调整——客户 25 的最晚到达时间从原值提前 30 分钟（窗口收窄，压力增大）
- 政策继承：**继承第二问绿色限行**（8:00-16:00 燃油车禁入绿区）

**选择理由**：
1. 地址变更使原"绿区客户 6"变为"非绿区客户"，可能允许燃油车服务，改变路线结构
2. 时间窗收窄测试惩罚计算的更新逻辑
3. 两事件并发展示多事件处理的优先级逻辑
4. 绿区政策继承展示第二问架构的复用能力

**关键技术挑战**：
- 客户 6 地址变更后，若已有 EV 路线服务了客户 6（在绿区时间段），需要检查地址变更后该路线是否仍需 EV（因为新地址可能不在绿区）
- 需要正确传递"旧地址的已冻结服务保持不变，新地址只影响未执行的服务节点"

**预期效果**：
- 客户 6 的未执行节点路线可以重新考虑使用燃油车（节约 EV 资源）
- 客户 25 时间窗收窄后惩罚可能增加，或需要路线调整

---

## 六、新模块：`green_logistics/dynamic.py`

### 6.1 数据结构定义

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Tuple

class EventType(Enum):
    ORDER_CANCEL = "order_cancel"
    NEW_ORDER = "new_order"
    ADDRESS_CHANGE = "address_change"
    TIME_WINDOW_CHANGE = "time_window_change"

@dataclass
class DynamicEvent:
    """动态事件描述符"""
    event_type: EventType
    t_now: float                          # 事件触发时刻（分钟）
    
    # 订单取消
    cancelled_customer_ids: List[int] = field(default_factory=list)
    
    # 新增订单
    new_customer_proxy_id: Optional[int] = None   # 用现有客户 ID 代理坐标
    new_demand_weight: float = 0.0
    new_demand_volume: float = 0.0
    new_tw_earliest: float = 0.0
    new_tw_latest: float = 1440.0
    
    # 地址变更
    changed_customer_id: Optional[int] = None
    new_address_proxy_id: Optional[int] = None    # 用现有客户 ID 代理新地址
    
    # 时间窗调整
    tw_changed_customer_id: Optional[int] = None
    new_tw_e: Optional[float] = None
    new_tw_l: Optional[float] = None


@dataclass
class FrozenRoutePrefix:
    """已执行且不可修改的路线前缀"""
    route_id: str
    vehicle_id: str
    vehicle_type: str
    frozen_nodes: List[int]               # 已完成服务的虚拟节点 ID 列表
    frozen_cost: float                    # 已执行部分的成本（沉没成本）
    last_completed_customer_id: int       # 上一个完成服务的客户 ID
    last_completed_time: float            # 上一个服务完成时刻
    current_load_weight: float            # 当前剩余载重
    current_load_volume: float            # 当前剩余体积


@dataclass
class DynamicProblemState:
    """t_now 时刻的动态问题状态"""
    t_now: float
    base_solution_id: str                 # "problem1" 或 "problem2"
    event: DynamicEvent
    
    frozen_prefixes: List[FrozenRoutePrefix]
    reschedulable_node_ids: List[int]     # 尚未执行、可重排的节点 ID
    unstarted_trip_ids: List[str]         # 尚未出发的趟次 ID
    
    available_vehicles: Dict[str, int]    # 车型 → 可用物理车辆数
    

@dataclass  
class DynamicReoptimizationResult:
    """动态重优化结果"""
    scenario_name: str
    t_now: float
    event_summary: str
    
    # 核心结果
    adjusted_solution: object             # Solution 对象
    
    # 成本对比
    base_total_cost: float
    adjusted_total_cost: float
    cost_delta: float                     # adjusted - base
    
    # 分项成本
    adjusted_fixed_cost: float
    adjusted_energy_cost: float
    adjusted_carbon_cost: float
    adjusted_penalty_cost: float
    
    # 质量指标
    policy_conflicts: int
    coverage_complete: bool
    capacity_feasible: bool
    late_stops: int
    max_lateness: float
    
    # 变动指标
    routes_modified: int
    nodes_moved: int
    trips_cancelled: int
    trips_added: int
```

### 6.2 核心函数骨架

```python
# green_logistics/dynamic.py

def build_dynamic_state(
    base_solution: Solution,
    event: DynamicEvent,
    data,
) -> DynamicProblemState:
    """
    根据事件和基准方案，构建 t_now 时刻的动态问题状态。
    明确区分冻结部分和可重排部分。
    """
    t_now = event.t_now
    frozen_prefixes = []
    reschedulable_nodes = []
    
    for route in base_solution.routes:
        frozen_idx = get_frozen_boundary(route, t_now)
        
        if frozen_idx > 0:
            frozen_prefixes.append(FrozenRoutePrefix(
                route_id=route.id,
                vehicle_id=route.vehicle_id,
                vehicle_type=route.vehicle_type,
                frozen_nodes=route.service_nodes[:frozen_idx],
                frozen_cost=compute_partial_cost(route, 0, frozen_idx, data),
                last_completed_customer_id=route.service_nodes[frozen_idx-1].customer_id,
                last_completed_time=route.arrival_times[frozen_idx],
                current_load_weight=route.remaining_weight_after(frozen_idx),
                current_load_volume=route.remaining_volume_after(frozen_idx),
            ))
        
        # 未冻结的节点可重排
        reschedulable_nodes.extend(route.service_nodes[frozen_idx:])
    
    return DynamicProblemState(
        t_now=t_now,
        event=event,
        frozen_prefixes=frozen_prefixes,
        reschedulable_node_ids=[n.id for n in reschedulable_nodes],
        ...
    )


def apply_event_and_reoptimize(
    base_solution: Solution,
    event: DynamicEvent,
    data,
    policy=None,
    alns_iterations: int = 25,
    scenario_name: str = "unnamed"
) -> DynamicReoptimizationResult:
    """第三问主入口：处理事件，返回调整结果"""
    
    # Step 1: 构建动态状态
    state = build_dynamic_state(base_solution, event, data)
    
    # Step 2: 快速确定性修复
    repaired = fast_repair(base_solution, event, event.t_now, data, policy)
    
    # Step 3: 验证修复结果可行性
    assert verify_feasibility(repaired, state, data, policy), "快速修复未能产出可行解"
    
    # Step 4: 轻量 ALNS
    optimized = lightweight_alns(repaired, event.t_now, data, policy, 
                                  max_iterations=alns_iterations)
    
    # Step 5: 计算结果
    return build_result(base_solution, optimized, state, scenario_name, data)
```

---

## 七、`problems/problem3.py` 主脚本框架

```python
# problems/problem3.py

"""
第三问主脚本：动态事件下的实时车辆调度策略。

三个演示情景：
  情景 A：订单取消（10:30，客户 50 取消）
  情景 B：新增订单（09:30，新增客户代理坐标 ID=30，800kg，TW=[660,750]）
  情景 C：地址变更 + 时间窗调整（11:00，继承绿区限行）

使用方法：
  python problems/problem3.py --base p1 --output-dir outputs/problem3
  python problems/problem3.py --base p2 --output-dir outputs/problem3
"""

import argparse
from green_logistics.data_processing import load_problem_data
from green_logistics.dynamic import (
    DynamicEvent, EventType, apply_event_and_reoptimize
)
from green_logistics.output import save_dynamic_result, compare_dynamic_scenarios

SCENARIOS = {
    "scenario_a_cancel": DynamicEvent(
        event_type=EventType.ORDER_CANCEL,
        t_now=630.0,  # 10:30
        cancelled_customer_ids=[50],
    ),
    "scenario_b_new_order": DynamicEvent(
        event_type=EventType.NEW_ORDER,
        t_now=570.0,  # 09:30
        new_customer_proxy_id=30,   # 用客户 30 的坐标
        new_demand_weight=800.0,
        new_demand_volume=2.5,
        new_tw_earliest=660.0,      # 11:00
        new_tw_latest=750.0,        # 12:30
    ),
    "scenario_c_address_tw": DynamicEvent(
        event_type=EventType.ADDRESS_CHANGE,  # 主事件
        t_now=660.0,  # 11:00
        changed_customer_id=6,
        new_address_proxy_id=40,
        # 附带时间窗调整
        tw_changed_customer_id=25,
        new_tw_e=None,   # 从数据中读取并减去 30 分钟
        new_tw_l=-30.0,  # 最晚时间缩短 30 分钟（相对值）
    ),
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", choices=["p1", "p2"], default="p1",
                        help="基准方案：p1=第一问，p2=第二问")
    parser.add_argument("--output-dir", default="outputs/problem3")
    parser.add_argument("--alns-iterations", type=int, default=25)
    parser.add_argument("--seed", type=int, default=20260426)
    args = parser.parse_args()
    
    data = load_problem_data(".")
    
    # 加载基准方案
    if args.base == "p1":
        base_solution = load_solution("outputs/problem1/solution.json", data)
        policy = NoPolicyEvaluator()
        base_name = "P1_静态调度基准"
    else:
        base_solution = load_solution("outputs/problem2/default_split/solution.json", data)
        policy = GreenZonePolicyEvaluator({2,3,4,5,6,7,8,9,10,11,12,13})
        base_name = "P2_绿区限行基准"
    
    results = {}
    for scenario_name, event in SCENARIOS.items():
        print(f"\n=== 处理情景: {scenario_name} ===")
        result = apply_event_and_reoptimize(
            base_solution=base_solution,
            event=event,
            data=data,
            policy=policy,
            alns_iterations=args.alns_iterations,
            scenario_name=scenario_name,
        )
        results[scenario_name] = result
        save_dynamic_result(result, data, f"{args.output_dir}/{scenario_name}/")
        
        print(f"  基准成本: {result.base_total_cost:.2f}")
        print(f"  调整后成本: {result.adjusted_total_cost:.2f}")
        print(f"  成本变化: {result.cost_delta:+.2f}")
        print(f"  政策冲突: {result.policy_conflicts}")
        print(f"  路线变动: {result.routes_modified} 条路线")
    
    compare_dynamic_scenarios(results, base_name, f"{args.output_dir}/")

if __name__ == "__main__":
    main()
```

---

## 八、输出格式与论文表述规范

### 8.1 每个情景的输出文件

```
outputs/problem3/
├── recommendation.json          # 三情景汇总推荐
├── scenario_comparison.csv      # 三情景横向对比表
├── scenario_a_cancel/
│   ├── summary.json             # 情景 A 完整统计
│   ├── route_summary.csv        # 路线汇总（含变动标注）
│   ├── stop_schedule.csv        # 停靠时间表（冻结节点标注 [FROZEN]）
│   ├── route_changes.csv        # 路线变动记录（新增/删除/修改）
│   ├── dynamic_diagnosis.csv    # 动态诊断（事件影响分析）
│   └── policy_conflicts.csv     # 政策冲突（若为 P2 基准）
├── scenario_b_new_order/
│   └── ...
└── scenario_c_address_tw/
    └── ...
```

### 8.2 `scenario_comparison.csv` 格式

| 字段 | 情景 A | 情景 B | 情景 C |
|---|---|---|---|
| 事件类型 | 订单取消 | 新增订单 | 地址变更+时间窗调整 |
| 触发时刻 | 10:30 | 09:30 | 11:00 |
| 基准总成本 | 48,644.68 | 48,644.68 | 49,239.78 |
| 调整后总成本 | ___ | ___ | ___ |
| 成本变化 | ___ | ___ | ___ |
| 路线变动条数 | ___ | ___ | ___ |
| 政策冲突 | 0 | 0 | 0 |
| 迟到点数 | ___ | ___ | ___ |
| 快速修复耗时(ms) | ___ | ___ | ___ |
| 总优化耗时(ms) | ___ | ___ | ___ |

### 8.3 论文表述要点

**关于冻结规则（必须说明）**：
> "在事件触发时刻 $t_{now}$，所有到达时刻 $t_i^{arr} < t_{now}$ 的节点视为已完成服务并冻结，不参与重优化。"

**关于"正在路上"车辆的近似（必须说明）**：
> "对于已出发但尚未到达下一服务点的车辆，以其上一完成服务节点为当前位置近似，计算后续路线时从该节点出发。"

**关于计算效率（竞赛加分点）**：
> "动态响应分为快速修复阶段（确定性启发，秒级响应）和优化阶段（轻量 ALNS，不超过 30 次迭代）。在演示情景中，快速修复阶段在 200 毫秒内完成，满足实时配送系统的响应需求。"

---

## 九、创新点总结（论文用）

| 创新点 | 内容 | 技术依据 |
|---|---|---|
| **滚动时域局部重优化（RHO）** | 以冻结规则为边界，只对残余子问题重优化，避免了全量重规划的计算开销 | 参考：Bent & Van Hentenryck (2004) VRPTW rolling horizon |
| **优先级串行事件处理** | 取消→地址变更→时间窗→新增的处理顺序，保证资源释放先于资源分配 | 本文根据物理逻辑设计 |
| **车辆状态近似的保守处理** | 明确声明"以上一完成节点为当前位置"的假设，避免虚假精度 | 工程诚实性原则 |
| **快速修复+轻量 ALNS 两段式** | 先确定性修复保证可行性，再限时 ALNS 提升质量 | Liu et al. (2023) GVRPTW 可行性修复策略 |
| **沉没成本 vs 增量成本的双口径分析** | 区分"全程总成本对比"和"动态调整增量成本"，提供更完整的决策视角 | 标准管理会计区分 |

---

## 十、避坑清单（Codex 专用）

### Pit 1：新增订单的 node_id 和 customer_id 映射

```python
# ❌ 错误：直接用 new_customer_proxy_id 作为 node_id
new_node = ServiceNode(id=30, customer_id=30)  # 30 已是现有节点

# ✅ 正确：分配新的 node_id（超出现有范围），但 customer_id 使用代理
new_node = ServiceNode(
    id=149,                        # 新虚拟节点 ID，超出现有 148 的范围
    customer_id=30,                # 用客户 30 的坐标和距离矩阵数据
    demand_weight=800.0,
    demand_volume=2.5,
    is_green_zone=data.customers[30].is_green_zone  # 继承坐标对应的绿区属性
)
```

### Pit 2：冻结节点不能被修改——包括"恰好在路上"的节点

```python
# ❌ 错误：认为"正在前往下一节点"的车辆可以在途中改变目的地
if vehicle_in_transit:
    next_stop = change_destination(...)  # 物理上不可能

# ✅ 正确：正在路上的车辆，其"下一停靠点"视为冻结（因为车辆已经出发）
# 只能修改"下一停靠点之后"的部分
frozen_idx = max(frozen_idx_from_time, current_committed_next_stop_idx)
```

### Pit 3：取消订单后不要自动取消固定成本

```python
# ❌ 错误：客户 50 的节点被取消后，立刻减去该路线的固定成本
fixed_cost -= 400  # 不对！该路线上可能还有其他未取消的节点

# ✅ 正确：只有当某趟次的所有节点都被取消，且该趟次尚未出发时，才能取消该趟次
if all_nodes_cancelled and trip_not_yet_started:
    remove_trip_from_solution()
    fixed_cost -= 400  # 现在才可以减
```

### Pit 4：多事件情景的成本计算要统一口径

```python
# 情景 C 用 P2 为基准，基准成本是 49,239.78
# 情景 A/B 用 P1 为基准，基准成本是 48,644.68
# 不要把不同基准的结果混在一起比较

# 每个情景的输出都要注明使用的基准
result.base_solution_name = "P2_绿区限行_DEFAULT_SPLIT"
result.base_total_cost = 49239.78
```

### Pit 5：地址变更不影响距离矩阵本身，只影响查找 ID

```python
# ❌ 错误：修改全局距离矩阵
data.distance_matrix[6][...] = new_distances  # 会影响其他问题的计算

# ✅ 正确：在 DynamicProblemState 中维护一个局部覆盖映射
state.customer_address_override = {
    6: 40  # 客户 6 的距离查找，临时使用客户 40 的 customer_id
}
# 在 ETA/成本计算时，先查 override，再查原始矩阵
```

### Pit 6：计时精度——快速修复的响应时间要真实测量

```python
import time
start = time.perf_counter()
repaired = fast_repair(...)
repair_time_ms = (time.perf_counter() - start) * 1000

# 必须在输出中报告这个数字，体现"实时性"
# 不要在没有测量的情况下声称"毫秒级响应"
result.fast_repair_time_ms = repair_time_ms
```

---

## 十一、测试规范（最低标准）

```python
# tests/test_problem3.py

def test_order_cancel_removes_nodes():
    """取消订单后，对应节点不再出现在任何路线中"""

def test_order_cancel_does_not_affect_frozen():
    """取消订单时，t_now 之前已完成的节点不受影响"""

def test_new_order_covered_exactly_once():
    """新增订单恰好被服务一次"""

def test_address_change_updates_eta():
    """地址变更后，受影响路线的 ETA 被正确重算"""

def test_time_window_change_updates_penalty():
    """时间窗调整后，受影响节点的惩罚被正确重算"""

def test_no_policy_violation_after_dynamic():
    """动态调整后，若继承 P2 政策，政策冲突仍为 0"""

def test_fast_repair_completes_in_1_second():
    """快速修复在 1 秒内完成"""

def test_total_cost_components_sum_correctly():
    """调整后分项成本之和等于总成本"""
```

---

## 十二、文件变动清单

### 新增文件

| 路径 | 说明 |
|---|---|
| `green_logistics/dynamic.py` | 事件类型、状态管理、快速修复、轻量 ALNS |
| `problems/problem3.py` | 第三问主脚本，三情景演示 |
| `tests/test_problem3.py` | 第三问核心逻辑测试 |
| `tests/test_dynamic.py` | 动态状态管理和冻结逻辑测试 |
| `docs/results/problem3_dynamic_response_summary.md` | 论文收官总结 |
| `docs/design/problem3_dynamic_response_roadmap.md` | 设计文档 |
| `outputs/problem3/` | 第三问所有输出（新建） |

### 修改文件

| 路径 | 修改内容 |
|---|---|
| `green_logistics/output.py` | 新增 `save_dynamic_result()` 和 `compare_dynamic_scenarios()` |
| `green_logistics/operators.py` | 新增 `run_alns_on_subset()` 支持节点子集搜索 |
| `项目文件导航.md` | 更新台账 |
| `README.md` | 更新第三问状态 |
| `task_plan.md` | 更新阶段状态 |
| `progress.md` | 记录进展 |

### 不修改文件

- `problems/problem1.py`、`outputs/problem1/`（第一问正式结果保护）
- `problems/problem2.py`、`outputs/problem2/`（第二问正式结果保护）
- `green_logistics/travel_time.py`、`green_logistics/cost.py`（核心计算层不动）
- `green_logistics/solution.py`（数据结构层不动）

---

*文档结束。基于题目原文、项目现状和物理规律，未引入任何题目外假设。*
