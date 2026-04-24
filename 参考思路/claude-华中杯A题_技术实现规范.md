# 城市绿色物流配送调度 — 完整技术实现规范
> 第十八届"华中杯"A题 · 供 Codex 编码使用
> 问题类型：TD-HFVRPTW（时变异构车队带时间窗车辆路径问题）+ 多次往返（Multi-Trip）

---

## 0. 项目结构

```
green_logistics/
├── data/                    # 原始数据（放置上传的xlsx文件）
│   ├── 订单信息.xlsx
│   ├── 客户坐标信息.xlsx
│   ├── 时间窗.xlsx
│   └── 距离矩阵.xlsx
├── src/
│   ├── data_loader.py       # 数据加载与预处理
│   ├── config.py            # 全局常量与参数
│   ├── travel_time.py       # 时变行程时间计算
│   ├── cost.py              # 所有成本函数
│   ├── solution.py          # Solution 数据结构
│   ├── initial_solution.py  # 初始解构建（Clark-Wright）
│   ├── alns.py              # ALNS主算法
│   ├── operators.py         # 破坏与修复算子
│   └── output.py            # 结果输出与分析
├── problems/
│   ├── problem1.py          # 问题1：静态调度
│   ├── problem2.py          # 问题2：绿色限行
│   └── problem3.py          # 问题3：动态实时
└── main.py
```

---

## 1. 全局常量（config.py）

```python
# ============================================================
# 时间设置（所有时间统一用"距08:00的分钟数"表示）
# 运营时间 08:00 — 22:00，即 0 — 840 分钟
# ============================================================
TIME_ORIGIN_HOUR = 8          # 运营开始时刻（24小时制）
SERVICE_TIME_MIN = 20         # 每次到访的服务时间（分钟）
DAY_END_MIN = 840             # 22:00 = 840 分钟

# ============================================================
# 时变路网：三段速度分布（均值，方差）单位 km/h
# 用均值速度计算行程时间（期望意义下最优）
# ============================================================
# 时间段定义：(开始分钟offset, 结束分钟offset, 均值速度, 方差)
# 注意：题目只给出以下时段，其余时段（如 17:00以后）默认用 一般时段
SPEED_SEGMENTS = [
    (0,   60,  9.8,  4.72),   # 08:00—09:00  拥堵
    (60,  120, 53.3, 0.12),   # 09:00—10:00  顺畅
    (120, 210, 35.4, 5.22),   # 10:00—11:30  一般
    (210, 300, 9.8,  4.72),   # 11:30—13:00  拥堵
    (300, 420, 53.3, 0.12),   # 13:00—15:00  顺畅
    (420, 540, 35.4, 5.22),   # 15:00—17:00  一般
    (540, 840, 35.4, 5.22),   # 17:00—22:00  默认一般（题目未说明，需在论文中声明假设）
]
# ⚠️ 坑：题目表1只给出 09:00-10:00/13:00-15:00 为顺畅，其余时段需合理假设
# 建议：17:00后使用"一般"时段均值35.4，并在论文中标注此假设

# ============================================================
# 车辆配置
# ============================================================
VEHICLES = [
    # (type_id, fuel_type, max_weight_kg, max_volume_m3, count, label)
    ('G1', 'fuel', 3000, 13.5, 60, '燃油大车'),
    ('G2', 'fuel', 1500, 10.8, 50, '燃油中车'),
    ('G3', 'fuel', 1250,  6.5, 50, '燃油小车'),
    ('E1', 'ev',   3000, 15.0, 10, '新能源大车'),
    ('E2', 'ev',   1250,  8.5, 15, '新能源小车'),
]
FIXED_COST_PER_VEHICLE = 400.0   # 元/辆，每辆启用的启动成本

# ============================================================
# 能耗与成本参数（严格来自题目，禁止修改）
# ============================================================
# 油耗公式（每百公里升数）：FPK = 0.0025v² - 0.2554v + 31.75
# 电耗公式（每百公里度数）：EPK = 0.0014v² - 0.12v + 36.19
FUEL_PRICE = 7.61         # 元/升
ELEC_PRICE = 1.64         # 元/度
CARBON_COST_PER_UNIT = 0.65  # 元/单位
ETA_FUEL = 2.547          # kg/L，燃油碳排放转换系数
GAMMA_EV = 0.501          # kg/kW·h，电耗碳排放转换系数

# 满载能耗加成（空载到满载）
FUEL_LOAD_FACTOR = 0.40   # 燃油车满载比空载多消耗40%
EV_LOAD_FACTOR   = 0.35   # 新能源车满载比空载多消耗35%

# ============================================================
# 时间窗惩罚成本
# ============================================================
EARLY_PENALTY = 20.0 / 60  # 元/分钟（题目给的是元/小时，需转换）
LATE_PENALTY  = 50.0 / 60  # 元/分钟

# ============================================================
# 绿色配送区
# ============================================================
GREEN_ZONE_RADIUS_KM = 10.0   # 以城市中心(0,0)为圆心
CITY_CENTER = (0.0, 0.0)
GREEN_ZONE_RESTRICT_START = 0    # 08:00 = 0分钟offset
GREEN_ZONE_RESTRICT_END   = 480  # 16:00 = 8*60分钟offset

# ============================================================
# ALNS 超参数
# ============================================================
ALNS_MAX_ITER = 10000
ALNS_SA_T0 = 100.0          # 初始温度（根据初始解代价的5%设置）
ALNS_SA_COOLING = 0.9995    # 冷却系数
ALNS_DESTROY_MIN = 3        # 最少移除节点数
ALNS_DESTROY_MAX = 10       # 最多移除节点数（可设为 max(3, n*0.1)）
ALNS_WEIGHT_UPDATE_FREQ = 100  # 每100次迭代更新算子权重
ALNS_WEIGHT_DECAY = 0.8     # 旧权重衰减系数
ALNS_SIGMA = (9, 3, 1)      # 得分：新最优/改进/接受
```

---

## 2. 数据加载与预处理（data_loader.py）

### 2.1 加载函数

```python
import pandas as pd
import numpy as np

def load_all_data(data_dir='data/'):
    """
    返回字典包含：
    - customers: dict {id: CustomerNode}
    - dist_matrix: np.ndarray shape (99, 99), index 0=配送中心, 1-98=客户
    - aggregated_demand: dict {customer_id: (total_weight_kg, total_volume_m3)}
    - time_windows: dict {customer_id: (earliest_min, latest_min)}
    - vehicle_types: list of VehicleType
    """
    # ---------- 距离矩阵 ----------
    # ⚠️ 坑1: pd.read_excel会把整数index读成int64，直接用即可
    # ⚠️ 坑2: 距离矩阵的行/列index是0-98，0代表配送中心
    dist_df = pd.read_excel(f'{data_dir}距离矩阵.xlsx', index_col=0)
    assert dist_df.shape == (99, 99), f"期望99x99，实际{dist_df.shape}"
    dist_matrix = dist_df.values.astype(float)  # shape (99,99), dist_matrix[i][j] in km

    # ---------- 客户坐标 ----------
    coord_df = pd.read_excel(f'{data_dir}客户坐标信息.xlsx')
    # 列名：['类型', 'ID', 'X (km)', 'Y (km)']
    depot_row = coord_df[coord_df['类型'] == '配送中心'].iloc[0]
    depot = {'id': 0, 'x': depot_row['X (km)'], 'y': depot_row['Y (km)']}
    # depot坐标 = (20.0, 20.0)，不在绿区内（距(0,0)约28.3km）

    customers_raw = coord_df[coord_df['类型'] == '客户'].copy()
    customers_raw['ID'] = customers_raw['ID'].astype(int)
    customers_raw['r'] = np.sqrt(customers_raw['X (km)']**2 + customers_raw['Y (km)']**2)
    customers_raw['in_green_zone'] = customers_raw['r'] <= GREEN_ZONE_RADIUS_KM

    # ---------- 时间窗 ----------
    # 列名：['客户编号', '开始时间', '结束时间']
    # ⚠️ 坑3: 开始时间/结束时间是字符串"HH:MM"，需手动解析
    tw_df = pd.read_excel(f'{data_dir}时间窗.xlsx')
    tw_df['开始时间'] = tw_df['开始时间'].astype(str)
    tw_df['结束时间'] = tw_df['结束时间'].astype(str)

    def parse_time_to_min(t_str):
        """将 'HH:MM' 转换为相对 08:00 的分钟数"""
        h, m = map(int, t_str.split(':'))
        return (h - TIME_ORIGIN_HOUR) * 60 + m

    time_windows = {}
    for _, row in tw_df.iterrows():
        cid = int(row['客户编号'])
        e = parse_time_to_min(row['开始时间'])
        l = parse_time_to_min(row['结束时间'])
        # ⚠️ 坑4: 部分客户时间窗的结束时间可能接近 840（22:00）
        # 若 e < 0，说明客户要求在08:00之前到达，需要特殊处理
        time_windows[cid] = (e, l)

    # ---------- 订单信息 → 按客户聚合 ----------
    # 列名：['订单编号', '重量', '体积', '目标客户编号']
    order_df = pd.read_excel(f'{data_dir}订单信息.xlsx')
    agg = order_df.groupby('目标客户编号').agg(
        total_weight=('重量', 'sum'),
        total_volume=('体积', 'sum'),
        order_count=('订单编号', 'count')
    ).reset_index()
    aggregated_demand = {
        int(row['目标客户编号']): (row['total_weight'], row['total_volume'])
        for _, row in agg.iterrows()
    }

    return {
        'depot': depot,
        'customers_raw': customers_raw,
        'dist_matrix': dist_matrix,
        'aggregated_demand': aggregated_demand,
        'time_windows': time_windows,
    }
```

### 2.2 超载客户拆分（虚拟节点生成）

```python
def split_overloaded_customers(aggregated_demand, time_windows, vehicle_max_weight=3000):
    """
    将需求超过最大载重的客户拆成多个虚拟子节点。
    
    返回：
    - nodes: list of ServiceNode（真实+虚拟）
    - node_to_customer: dict {node_id: original_customer_id}
    
    ⚠️ 坑5（极重要）：本题有36个客户需求超过3000kg，最高达12197.6kg（客户55）
    若不拆分直接跑VRPTW，会导致大量约束违反，使算法无法找到可行解
    """
    nodes = []
    node_to_customer = {}
    node_id = 1  # 从1开始，0保留给配送中心

    for cid in sorted(aggregated_demand.keys()):
        total_w, total_v = aggregated_demand[cid]
        e, l = time_windows.get(cid, (0, DAY_END_MIN))

        # 计算需要拆分的次数（按重量，体积同比例拆）
        n_trips = int(np.ceil(total_w / vehicle_max_weight))

        for trip_idx in range(n_trips):
            # 每个子节点分配等比例需求
            frac = min(vehicle_max_weight, total_w - trip_idx * vehicle_max_weight)
            frac_v = total_v * (frac / total_w)

            node = {
                'node_id': node_id,
                'customer_id': cid,
                'trip_idx': trip_idx,
                'demand_weight': frac,
                'demand_volume': frac_v,
                'time_window_early': e,
                'time_window_late': l,
                # 所有子节点共享同一时间窗（均受软时间窗约束）
            }
            nodes.append(node)
            node_to_customer[node_id] = cid
            node_id += 1

    return nodes, node_to_customer
```

> **⚠️ 坑5详解**：36个客户总需求超过单车3000kg，其中客户55需要 `ceil(12197.6/3000)=5` 次配送。这意味着实际待调度节点数不是88个，而是约 **150–180个虚拟节点**。此时ALNS的邻域搜索规模相应扩大，需注意性能。

### 2.3 绿区客户识别

```python
# 已验证：绿区客户 ID = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
# 其中 ID=1,14,15 今日无需求订单
# 有需求的绿区客户 = [2,3,4,5,6,7,8,9,10,11,12,13]（共12个）
GREEN_ZONE_CUSTOMER_IDS = {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15}

def is_in_green_zone(customer_id):
    return customer_id in GREEN_ZONE_CUSTOMER_IDS
```

---

## 3. 时变行程时间计算（travel_time.py）

### 3.1 预计算查找表

```python
import numpy as np

# 时间槽：将运营时间 [0, 840] 划分为 84 个 10分钟槽
SLOT_WIDTH_MIN = 10
N_SLOTS = 84  # 840 / 10

def get_speed_at_minute(t_min):
    """返回时刻 t_min（距08:00分钟数）的均值车速 km/h"""
    for (start, end, mean_v, _) in SPEED_SEGMENTS:
        if start <= t_min < end:
            return mean_v
    return 35.4  # 超出时段范围，默认一般速度

def build_travel_time_table(dist_matrix):
    """
    预计算所有 (i,j,slot) 的行程时间（分钟）。
    shape: (99, 99, N_SLOTS)
    调用方式: tt = build_travel_time_table(dist_matrix)
               travel_min = tt[i, j, slot]
    """
    n = dist_matrix.shape[0]
    tt = np.zeros((n, n, N_SLOTS), dtype=float)

    for slot in range(N_SLOTS):
        t_mid = slot * SLOT_WIDTH_MIN + SLOT_WIDTH_MIN / 2  # 槽中点时刻
        v = get_speed_at_minute(t_mid)
        if v <= 0:
            v = 0.1  # 防止除零
        tt[:, :, slot] = dist_matrix / v * 60  # 转换为分钟

    return tt

def get_travel_time(tt_table, i, j, depart_min):
    """
    获取从节点i在depart_min时刻出发到节点j的行程时间（分钟）。
    使用迭代积分确保 FIFO 性质。
    
    ⚠️ 坑6（FIFO悖论）：不能直接用出发时刻的速度乘以距离。
    例如：若在拥堵末期出发，途中进入顺畅时段，则实际行程时间
    短于"全程拥堵速度"的估算。正确做法是分段积分。
    """
    if i == j:
        return 0.0

    dist = tt_table[i, j, 0] * (get_speed_at_minute(5) / 60)  # 反推距离
    # ⚠️ 上面这样反推有误差，建议直接传入dist_matrix
    # 更好的接口：
    # get_travel_time(dist_ij, depart_min) -> float
    pass

def get_travel_time_v2(dist_ij_km, depart_min):
    """
    推荐版本：直接传距离（km）和出发时刻。
    通过分段积分计算行程时间（分钟），保证FIFO。
    """
    if dist_ij_km <= 0:
        return 0.0

    remaining_dist = dist_ij_km
    current_t = depart_min
    total_time = 0.0

    MAX_ITER = 200  # 防止死循环
    for _ in range(MAX_ITER):
        v = get_speed_at_minute(current_t)
        # 当前时段剩余时间
        seg_end = next(
            (end for (start, end, _, _) in SPEED_SEGMENTS if start <= current_t < end),
            current_t + 60  # 默认当前时段剩余60分钟
        )
        seg_remaining_min = seg_end - current_t

        # 当前时段能行驶的最大距离
        dist_in_seg = v * seg_remaining_min / 60  # km

        if dist_in_seg >= remaining_dist:
            # 在当前时段内完成
            total_time += remaining_dist / v * 60
            break
        else:
            # 消耗完当前时段，继续下一段
            remaining_dist -= dist_in_seg
            total_time += seg_remaining_min
            current_t = seg_end

        if current_t >= DAY_END_MIN:
            # 超出运营时间，强制结束
            total_time += remaining_dist / 35.4 * 60  # 用默认速度
            break

    return total_time
```

> **⚠️ 坑6详解（FIFO悖论）**：分段速度下，若简单用"出发时速度×全程距离"会违反FIFO（先出发不一定先到达）。必须用逐段积分。上面的 `get_travel_time_v2` 即为正确实现。

---

## 4. 成本函数（cost.py）

```python
def fpk(v):
    """
    燃油车每百公里油耗（升/百公里）
    ⚠️ 这是题目原公式，禁止更改系数
    """
    return 0.0025 * v**2 - 0.2554 * v + 31.75

def epk(v):
    """新能源车每百公里电耗（度/百公里）"""
    return 0.0014 * v**2 - 0.12 * v + 36.19

def travel_cost(dist_km, v_kmh, fuel_type, load_ratio):
    """
    计算一段行驶的能耗费用（元）
    
    参数：
    - dist_km: 行驶距离（公里）
    - v_kmh: 行驶速度（km/h，使用时段均值速度）
    - fuel_type: 'fuel' 或 'ev'
    - load_ratio: 装载率 [0,1]（当前装载重量/最大载重）
    
    ⚠️ 坑7：满载能耗加成是在"空载能耗"基础上加 load_ratio * factor
    不是简单的"满载才+40%"，而是随装载率线性变化
    题目只说"满载比空载高40%"，建议线性插值：
        actual_fpk = fpk(v) * (1 + load_ratio * FUEL_LOAD_FACTOR)
    """
    if fuel_type == 'fuel':
        base_consumption = fpk(v_kmh)
        actual_consumption = base_consumption * (1 + load_ratio * FUEL_LOAD_FACTOR)
        cost = (dist_km / 100) * actual_consumption * FUEL_PRICE
        carbon = (dist_km / 100) * actual_consumption * ETA_FUEL * CARBON_COST_PER_UNIT
    else:  # ev
        base_consumption = epk(v_kmh)
        actual_consumption = base_consumption * (1 + load_ratio * EV_LOAD_FACTOR)
        cost = (dist_km / 100) * actual_consumption * ELEC_PRICE
        carbon = (dist_km / 100) * actual_consumption * GAMMA_EV * CARBON_COST_PER_UNIT

    return cost, carbon

def time_penalty_cost(arrive_min, early_min, late_min):
    """
    软时间窗惩罚（元）
    arrive_min: 实际到达时刻（相对08:00的分钟数）
    early_min / late_min: 时间窗（相对08:00的分钟数）
    
    ⚠️ 坑8：惩罚基于到达时刻，不含服务时间
    等待时间 = max(0, early_min - arrive_min)  → 等待成本
    延误时间 = max(0, arrive_min - late_min)   → 惩罚成本
    """
    wait = max(0.0, early_min - arrive_min)
    delay = max(0.0, arrive_min - late_min)
    return wait * EARLY_PENALTY + delay * LATE_PENALTY

def route_cost(route, vehicle_type, dist_matrix):
    """
    计算一条完整路线的总成本
    
    route: [0, c1, c2, ..., cn, 0]（节点ID列表，0=配送中心）
    vehicle_type: VehicleType 对象（含 fuel_type, max_weight）
    
    返回：(fixed_cost, travel_cost, carbon_cost, penalty_cost, arrive_times)
    """
    if len(route) <= 2:  # 只有出发和返回
        return 0, 0, 0, 0, []

    fixed = FIXED_COST_PER_VEHICLE
    total_travel = 0.0
    total_carbon = 0.0
    total_penalty = 0.0
    arrive_times = []

    current_time = 0.0  # 从08:00出发
    current_load = sum(node_demand_weight(c) for c in route[1:-1])
    load_ratio = current_load / vehicle_type['max_weight']

    for idx in range(len(route) - 1):
        i, j = route[idx], route[idx+1]
        dist_ij = dist_matrix[i][j]
        v = get_speed_at_minute(current_time)
        tt = get_travel_time_v2(dist_ij, current_time)

        tc, cc = travel_cost(dist_ij, v, vehicle_type['fuel_type'], load_ratio)
        total_travel += tc
        total_carbon += cc

        arrive = current_time + tt
        arrive_times.append(arrive)

        if j != 0:  # 非配送中心
            e, l = time_windows[j]
            total_penalty += time_penalty_cost(arrive, e, l)
            # 更新时间（等待到时间窗开始，或立即服务）
            service_start = max(arrive, e)
            current_time = service_start + SERVICE_TIME_MIN
            # 更新装载率（服务完该客户后卸货）
            current_load -= node_demand_weight(j)
            load_ratio = current_load / vehicle_type['max_weight']
        else:
            current_time = arrive

    return fixed, total_travel, total_carbon, total_penalty, arrive_times
```

---

## 5. Solution 数据结构（solution.py）

```python
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

@dataclass
class Route:
    vehicle_type_id: str           # 'G1','G2','G3','E1','E2'
    vehicle_index: int             # 该类型中的第几辆（从0开始）
    node_sequence: List[int]       # [0, n1, n2, ..., nk, 0]，含首尾配送中心
    arrive_times: List[float]      # 每个节点的到达时刻（分钟offset）
    depart_times: List[float]      # 每个节点的离开时刻
    loads_at_arrival: List[float]  # 每段到达时的装载量（kg）

    # 成本分解
    fixed_cost: float = 0.0
    travel_cost: float = 0.0
    carbon_cost: float = 0.0
    penalty_cost: float = 0.0

    @property
    def total_cost(self):
        return self.fixed_cost + self.travel_cost + self.carbon_cost + self.penalty_cost

@dataclass
class Solution:
    routes: List[Route] = field(default_factory=list)
    unserved_nodes: List[int] = field(default_factory=list)  # 未服务节点（应为空才可行）

    @property
    def total_cost(self):
        return sum(r.total_cost for r in self.routes)

    @property
    def total_carbon(self):
        return sum(r.carbon_cost / CARBON_COST_PER_UNIT for r in self.routes)

    @property
    def n_vehicles_used(self):
        return len(self.routes)

    def copy(self):
        """深拷贝，ALNS中频繁调用"""
        import copy
        return copy.deepcopy(self)
```

---

## 6. 初始解构建（initial_solution.py）

使用 **Clark-Wright 节省算法** 构造初始可行解：

```python
def clark_wright_savings(nodes, dist_matrix, vehicle_types, time_windows):
    """
    Clark-Wright节省算法构造初始解
    
    步骤：
    1. 为每个节点创建单独路线 [0, i, 0]
    2. 计算所有节点对的节省值 s(i,j) = d(0,i) + d(j,0) - d(i,j)
    3. 按节省值降序尝试合并路线
    4. 检查合并是否满足：容量约束 + 时间窗可行性
    
    ⚠️ 坑9：合并时必须检查时间窗可行性，不能只检查容量
    CW算法倾向于生成长路线，可能导致大量时间窗违反
    建议：合并前验证时间窗，违反则跳过合并
    """
    # 1. 为每个节点初始化独立路线，选择最小满足需求的车型
    routes = []
    for node in nodes:
        vtype = select_minimum_vehicle(node['demand_weight'], node['demand_volume'])
        route = Route(
            vehicle_type_id=vtype['type_id'],
            vehicle_index=len(routes),
            node_sequence=[0, node['node_id'], 0],
            ...
        )
        routes.append(route)

    # 2. 计算节省值（使用距离矩阵直接查询）
    savings = []
    for i_idx, n_i in enumerate(nodes):
        for j_idx, n_j in enumerate(nodes):
            if i_idx >= j_idx:
                continue
            i, j = n_i['node_id'], n_j['node_id']
            # ⚠️ 坑10：节点ID和距离矩阵下标的映射关系
            # 虚拟节点共享同一个customer_id对应的距离矩阵行
            ci = node_to_customer[i]  # 原始客户ID
            cj = node_to_customer[j]
            s = dist_matrix[0][ci] + dist_matrix[cj][0] - dist_matrix[ci][cj]
            savings.append((s, i_idx, j_idx))

    savings.sort(reverse=True)

    # 3. 贪心合并
    for (s, i_idx, j_idx) in savings:
        # ...尝试合并，验证约束后合并
        pass

    return Solution(routes=routes)
```

---

## 7. ALNS 主算法（alns.py）

```python
import random
import math

class ALNS:
    def __init__(self, instance, problem_mode='p1'):
        """
        problem_mode: 'p1'=问题1, 'p2'=问题2（激活绿区限行）, 'p3'=问题3（动态）
        """
        self.instance = instance
        self.problem_mode = problem_mode
        self.green_zone_active = (problem_mode == 'p2')

        # 初始化算子权重（均等开始）
        self.destroy_ops = [
            self.destroy_random,
            self.destroy_worst_cost,
            self.destroy_related,
            self.destroy_time_window_violators,
            self.destroy_green_zone,  # 问题2专用
            self.destroy_overloaded_route,
        ]
        self.repair_ops = [
            self.repair_greedy,
            self.repair_regret2,
            self.repair_regret3,
            self.repair_ev_priority,  # 问题2专用
        ]
        self.d_weights = [1.0] * len(self.destroy_ops)
        self.r_weights = [1.0] * len(self.repair_ops)
        self.d_scores  = [0.0] * len(self.destroy_ops)
        self.r_scores  = [0.0] * len(self.repair_ops)
        self.d_counts  = [0]   * len(self.destroy_ops)
        self.r_counts  = [0]   * len(self.repair_ops)

    def run(self, initial_solution, max_iter=ALNS_MAX_ITER):
        current = initial_solution.copy()
        best = initial_solution.copy()
        T = ALNS_SA_T0

        for it in range(max_iter):
            # 选择算子（轮盘赌）
            d_idx = self._roulette(self.d_weights)
            r_idx = self._roulette(self.r_weights)

            # 破坏
            destroyed, removed_nodes = self.destroy_ops[d_idx](current.copy())
            # 修复
            new_sol = self.repair_ops[r_idx](destroyed, removed_nodes)

            # ⚠️ 坑11：修复后必须验证解的合法性
            # 特别是：绿区约束（问题2）、车辆数量上限
            if not self._is_feasible(new_sol):
                continue

            # 模拟退火接受准则
            delta = new_sol.total_cost - current.total_cost
            score = 0
            if new_sol.total_cost < best.total_cost:
                best = new_sol.copy()
                current = new_sol
                score = ALNS_SIGMA[0]  # 新最优 +9
            elif delta < 0:
                current = new_sol
                score = ALNS_SIGMA[1]  # 改进当前解 +3
            elif random.random() < math.exp(-delta / T):
                current = new_sol
                score = ALNS_SIGMA[2]  # 接受较差解 +1

            # 更新算子分数
            self.d_scores[d_idx] += score
            self.r_scores[r_idx] += score
            self.d_counts[d_idx] += 1
            self.r_counts[r_idx] += 1

            # 每 ALNS_WEIGHT_UPDATE_FREQ 次更新权重
            if (it + 1) % ALNS_WEIGHT_UPDATE_FREQ == 0:
                self._update_weights()

            # 降温
            T *= ALNS_SA_COOLING

        return best

    def _roulette(self, weights):
        """轮盘赌选择"""
        total = sum(weights)
        r = random.random() * total
        cumsum = 0
        for i, w in enumerate(weights):
            cumsum += w
            if r <= cumsum:
                return i
        return len(weights) - 1

    def _update_weights(self):
        """更新算子权重（带衰减）"""
        for i in range(len(self.d_weights)):
            if self.d_counts[i] > 0:
                new_w = self.d_scores[i] / self.d_counts[i]
                self.d_weights[i] = (ALNS_WEIGHT_DECAY * self.d_weights[i]
                                     + (1 - ALNS_WEIGHT_DECAY) * new_w)
            self.d_scores[i] = 0.0
            self.d_counts[i] = 0
        # repair同理...

    def _is_feasible(self, solution):
        """
        验证解的合法性
        ⚠️ 坑12：必须检查以下所有约束
        """
        vehicle_count = {}
        for route in solution.routes:
            vt = route.vehicle_type_id
            vehicle_count[vt] = vehicle_count.get(vt, 0) + 1

        for vt_id, count in vehicle_count.items():
            max_count = next(v[4] for v in VEHICLES if v[0] == vt_id)
            if count > max_count:
                return False  # 超过车辆数量上限

        if solution.unserved_nodes:
            return False  # 有未服务节点

        # 问题2：绿区燃油车限行检查
        if self.green_zone_active:
            for route in solution.routes:
                vtype = route.vehicle_type_id
                if vtype in ('G1','G2','G3'):  # 燃油车
                    for idx, node_id in enumerate(route.node_sequence[1:-1], 1):
                        cid = node_to_customer[node_id]
                        if is_in_green_zone(cid):
                            arrive = route.arrive_times[idx]
                            if GREEN_ZONE_RESTRICT_START <= arrive <= GREEN_ZONE_RESTRICT_END:
                                return False

        return True
```

---

## 8. 破坏与修复算子（operators.py）

### 8.1 破坏算子

```python
def destroy_random(solution):
    """随机移除 n 个节点"""
    n = random.randint(ALNS_DESTROY_MIN, ALNS_DESTROY_MAX)
    removed = []
    sol = solution.copy()
    all_nodes = [n for r in sol.routes for n in r.node_sequence[1:-1]]
    if len(all_nodes) < n:
        n = len(all_nodes)
    to_remove = random.sample(all_nodes, n)
    for node_id in to_remove:
        remove_node_from_solution(sol, node_id)
        removed.append(node_id)
    return sol, removed

def destroy_worst_cost(solution):
    """
    移除对总成本贡献最大的节点。
    贡献度 = 移除该节点后路线成本的节省量
    ⚠️ 坑13：计算贡献度时要考虑时间窗效应，
    不能只看移除节点前后的距离变化
    """
    contributions = []
    for route in solution.routes:
        for idx, node_id in enumerate(route.node_sequence[1:-1], 1):
            # 计算移除该节点后的路线成本变化
            test_route = remove_node(route, idx)
            delta = route.total_cost - test_route.total_cost
            contributions.append((delta, node_id))
    contributions.sort(reverse=True)
    # 加入随机噪声，防止每次都移除同一节点
    n = random.randint(ALNS_DESTROY_MIN, ALNS_DESTROY_MAX)
    to_remove = [nid for _, nid in contributions[:n*3]]
    to_remove = random.sample(to_remove, min(n, len(to_remove)))
    # ...执行移除
    pass

def destroy_related(solution):
    """
    相关性移除：移除时空上相近的节点。
    相关性 = 距离 + 时间窗差异的加权组合
    适合打破局部最优，是ALNS中最重要的算子之一
    """
    # 随机选一个种子节点
    all_nodes = [n for r in solution.routes for n in r.node_sequence[1:-1]]
    seed = random.choice(all_nodes)
    seed_cid = node_to_customer[seed]

    # 计算其他节点与种子的相关性
    relatedness = []
    for node_id in all_nodes:
        if node_id == seed:
            continue
        cid = node_to_customer[node_id]
        d = dist_matrix[seed_cid][cid]
        e1, l1 = time_windows[seed_cid]
        e2, l2 = time_windows[cid]
        tw_diff = abs((e1+l1)/2 - (e2+l2)/2)
        rel = d + 0.1 * tw_diff  # 距离权重更大
        relatedness.append((rel, node_id))

    relatedness.sort()
    n = random.randint(ALNS_DESTROY_MIN, ALNS_DESTROY_MAX)
    to_remove = [nid for _, nid in relatedness[:n]]
    # ...执行移除
    pass

def destroy_green_zone(solution):
    """
    专用于问题2：优先移除绿区内被燃油车服务的节点，
    为后续修复算子用新能源车替换提供机会
    """
    candidates = []
    for route in solution.routes:
        if route.vehicle_type_id not in ('G1','G2','G3'):
            continue
        for node_id in route.node_sequence[1:-1]:
            if is_in_green_zone(node_to_customer[node_id]):
                candidates.append(node_id)
    if not candidates:
        return destroy_random(solution)
    n = min(random.randint(1, 5), len(candidates))
    to_remove = random.sample(candidates, n)
    # ...执行移除
    pass
```

### 8.2 修复算子

```python
def repair_greedy(partial_solution, removed_nodes):
    """
    贪心最低成本插入：对每个待插入节点，
    枚举所有（路线，位置）组合，选择成本增量最小的插入点
    
    ⚠️ 坑14：插入后必须重新计算后续节点的到达时刻（时间窗级联效应）
    插入一个节点可能导致后面所有节点都延误，需要完整重算时序
    """
    sol = partial_solution.copy()
    for node_id in sorted(removed_nodes, key=lambda n: time_windows[node_to_customer[n]][0]):
        # 按时间窗最早开始时间排序，优先插入时间窗紧张的节点
        best_cost_delta = float('inf')
        best_route_idx = -1
        best_pos = -1

        for r_idx, route in enumerate(sol.routes):
            # 检查车辆容量
            if route_load(route) + node_demand(node_id) > vehicle_capacity(route.vehicle_type_id):
                continue
            for pos in range(1, len(route.node_sequence)):
                delta = compute_insertion_cost(route, node_id, pos)
                if delta < best_cost_delta:
                    best_cost_delta = delta
                    best_route_idx = r_idx
                    best_pos = pos

        if best_route_idx >= 0:
            insert_node(sol.routes[best_route_idx], node_id, best_pos)
        else:
            # 开新路线
            vtype = select_vehicle_for_node(node_id)
            new_route = create_single_route(node_id, vtype)
            sol.routes.append(new_route)

    return sol

def repair_regret2(partial_solution, removed_nodes):
    """
    Regret-2修复：选择"最优插入成本"与"次优插入成本"差值最大的节点优先插入。
    避免某个节点因被其他节点"占用"位置而只能高代价插入。
    通常比贪心修复效果更好，是ALNS的标准配置。
    """
    pass

def repair_ev_priority(partial_solution, removed_nodes):
    """
    问题2专用：对绿区节点，优先分配新能源车。
    若新能源车数量不足，则将绿区节点安排在限行时段之外（17:00后）由燃油车服务。
    
    ⚠️ 坑15：新能源车只有25辆（E1×10 + E2×15），
    而绿区有12个有需求的客户，部分客户需多次配送，
    25辆EV完全不够覆盖所有绿区需求，需要混合策略
    """
    pass
```

---

## 9. 问题1实现（problems/problem1.py）

```python
def solve_problem1():
    """
    静态调度，无政策限制，最小化总配送成本
    目标函数：min Z = C_fix + C_travel + C_carbon + C_penalty
    """
    # 1. 加载数据
    data = load_all_data()
    nodes, node_map = split_overloaded_customers(
        data['aggregated_demand'],
        data['time_windows']
    )

    # 2. 构造初始解
    init_sol = clark_wright_savings(nodes, data['dist_matrix'], VEHICLES, data['time_windows'])
    print(f"初始解代价: {init_sol.total_cost:.2f} 元")

    # 3. ALNS优化
    alns = ALNS(instance=data, problem_mode='p1')
    best_sol = alns.run(init_sol)

    # 4. 输出
    output_solution(best_sol, mode='p1')
    return best_sol
```

**问题1输出格式要求**：

| 车辆编号 | 车型 | 服务客户序列 | 各节点到达时刻 | 启动成本 | 行驶成本 | 碳排成本 | 时窗惩罚 | 合计 |
|---------|------|------------|--------------|---------|---------|---------|---------|-----|
| 1       | G1   | 0→5→12→0  | 08:00,09:23,10:15,11:02 | 400 | 312.5 | 45.2 | 20.0 | 777.7 |

---

## 10. 问题2实现（problems/problem2.py）

```python
def solve_problem2(p1_solution):
    """
    在问题1基础上激活绿区限行：
    8:00—16:00 禁止燃油车进入绿色配送区（半径10km圆形区域，圆心(0,0)）
    
    策略：
    1. 识别问题1解中违反限行的路线（燃油车+绿区+限行时段）
    2. 对违规路线进行重规划：
       a) 优先将绿区客户转移到新能源车路线
       b) 若EV不足，将服务时间推迟到16:00以后（燃油车在17:00后可进入）
    3. 对非违规路线保持不变（减少重规划范围）
    """
    # 识别违规路线
    violating_routes = find_green_zone_violations(p1_solution)
    print(f"违规路线数: {len(violating_routes)}")

    # 仅对违规路线重规划
    alns = ALNS(instance=data, problem_mode='p2')
    # 将违规路线中的绿区节点提取出来重新分配
    ...

    # 输出对比分析
    compare_p1_p2(p1_solution, p2_solution)
```

**问题2对比输出**：
- 总成本变化：+X元（+Y%）
- 车辆结构变化：燃油车从A辆减至B辆，新能源车从C辆增至D辆
- 碳排放变化：从E kg减至F kg（-G%）
- 新策略：M条路线时间推迟，N条路线改用新能源车

---

## 11. 问题3实现（problems/problem3.py）

```python
def solve_problem3_dynamic(current_solution, event, current_time_min):
    """
    动态事件响应策略（滚动时域重调度）
    
    event 类型：
    - {'type': 'cancel', 'node_id': int}                    # 订单取消
    - {'type': 'new_order', 'customer_id': int, 'demand': (w,v), 'tw': (e,l)}  # 新增订单
    - {'type': 'address_change', 'node_id': int, 'new_customer_id': int}        # 地址变更
    - {'type': 'tw_change', 'node_id': int, 'new_tw': (e,l)}                   # 时窗调整
    
    ⚠️ 坑16：已出发的车辆不能被召回，只能调整未出发路线
    需判断每辆车的"当前状态"：已完成/在途/待发
    """
    # 1. 判断哪些路线已出发（不可更改）
    frozen_routes = [r for r in current_solution.routes if is_vehicle_departed(r, current_time_min)]
    free_routes = [r for r in current_solution.routes if not is_vehicle_departed(r, current_time_min)]

    # 2. 处理事件
    if event['type'] == 'cancel':
        free_routes = remove_node_from_routes(free_routes, event['node_id'])

    elif event['type'] == 'new_order':
        # 将新节点加入待插入队列，用贪心插入快速响应
        new_node = create_node_from_event(event)
        free_routes = greedy_insert_new_node(free_routes, new_node)

    # 3. 仅对 free_routes 运行轻量级ALNS（迭代次数减少为1000次）
    partial_sol = Solution(routes=free_routes)
    alns = ALNS(instance=data, problem_mode='p3')
    optimized_free = alns.run(partial_sol, max_iter=1000)

    # 4. 合并冻结路线和优化后路线
    final_sol = Solution(routes=frozen_routes + optimized_free.routes)
    return final_sol

def is_vehicle_departed(route, current_time_min):
    """
    判断车辆是否已出发（出发时间 < current_time_min 且已服务了至少一个客户）
    ⚠️ 坑17：所有车辆默认08:00出发，current_time_min > 0 时大部分车已在路上
    """
    return len(route.arrive_times) > 0 and route.arrive_times[0] < current_time_min
```

**问题3建议演示场景**：
1. 场景A：09:30，绿区客户8取消订单 + 同时新增非绿区客户新需求
2. 场景B：11:00，在途车辆前方客户地址变更（原客户5改为客户50）
3. 场景C：14:00，客户12时间窗从 [17:00,18:00] 提前到 [15:00,16:00]

---

## 12. 关键坑汇总表

| # | 位置 | 坑的描述 | 解决方案 |
|---|------|---------|---------|
| 1 | 数据加载 | 距离矩阵index是int64，iloc/loc混用会出错 | 统一用`.values[i][j]`按位置索引 |
| 2 | 数据加载 | 距离矩阵节点0=配送中心，1-98=客户 | 明确区分节点ID与矩阵下标 |
| 3 | 时间解析 | 时间窗是字符串"HH:MM"，不是datetime | 用`split(':')`手动解析为分钟offset |
| 4 | 时间解析 | 转换后offset可能为负数（早于08:00） | 检查并clip到0 |
| 5 | 需求聚合 | 36个客户总重超3000kg，必须Multi-Trip拆分 | split_overloaded_customers()函数处理 |
| 6 | 行程时间 | 分段速度导致FIFO悖论 | 用get_travel_time_v2()逐段积分 |
| 7 | 成本计算 | 满载加成是线性的，非二值 | `fpk(v) * (1 + load_ratio * 0.4)` |
| 8 | 成本计算 | 惩罚成本基于到达时刻，非服务完成时刻 | arrive_time确定惩罚，service_start=max(arrive,e) |
| 9 | 初始解 | CW合并不检查时间窗，初始解大量违反 | 合并前先验证时序可行性 |
| 10 | 节点映射 | 虚拟节点ID≠客户ID，距离矩阵用客户ID | 始终通过node_to_customer[node_id]取CID |
| 11 | ALNS | 修复后解未验证合法性，引入非法解 | _is_feasible()每次修复后调用 |
| 12 | ALNS | 未检查车辆数量上限（如G1最多60辆） | 在feasibility check中统计每型用量 |
| 13 | 破坏算子 | 贡献度只算距离，忽略时窗效应 | 完整重算移除后路线成本差 |
| 14 | 修复算子 | 插入新节点后未重算后续节点时序 | recalculate_times()从插入位置往后全部重算 |
| 15 | 问题2 | EV只有25辆，不足以覆盖所有绿区需求 | 混合策略：EV优先+限行外时段燃油车补充 |
| 16 | 问题3 | 已出发车辆被错误重新调度 | 严格判断is_vehicle_departed() |
| 17 | 问题3 | 所有车08:00出发，current_time>0时大多已在途 | 冻结已出发路线，只优化待发路线 |
| 18 | 绿区判断 | 绿区圆心是城市中心(0,0)，非配送中心(20,20) | is_in_green_zone()用客户坐标与(0,0)的距离 |
| 19 | 性能 | 虚拟节点扩展后约150-180个节点，暴力枚举慢 | 候选插入点用近邻列表限制在最近10个节点 |
| 20 | 输出 | 时刻需转回"HH:MM"格式 | offset_to_hhmm(offset_min): h=8+offset//60, m=offset%60 |

---

## 13. 输出函数（output.py）

```python
def offset_to_hhmm(offset_min):
    """
    将相对08:00的分钟数转换为时刻字符串
    ⚠️ 坑20：必须加上TIME_ORIGIN_HOUR=8
    """
    total_min = int(offset_min)
    h = TIME_ORIGIN_HOUR + total_min // 60
    m = total_min % 60
    return f"{h:02d}:{m:02d}"

def output_solution(solution, mode='p1'):
    """输出完整调度方案"""
    print(f"\n{'='*60}")
    print(f"{'问题'+mode[1:]} 最优调度方案")
    print(f"{'='*60}")
    print(f"使用车辆总数: {solution.n_vehicles_used}")
    print(f"总成本: {solution.total_cost:.2f} 元")
    print(f"  - 固定启动成本: {sum(r.fixed_cost for r in solution.routes):.2f}")
    print(f"  - 行驶能耗成本: {sum(r.travel_cost for r in solution.routes):.2f}")
    print(f"  - 碳排放成本:   {sum(r.carbon_cost for r in solution.routes):.2f}")
    print(f"  - 时间窗惩罚:   {sum(r.penalty_cost for r in solution.routes):.2f}")
    print(f"总碳排放: {solution.total_carbon:.2f} kg")

    print(f"\n{'路线详情':}")
    for i, route in enumerate(solution.routes):
        nodes_str = ' → '.join(
            '配送中心' if n == 0 else f'客户{node_to_customer[n]}'
            for n in route.node_sequence
        )
        times_str = ', '.join(
            offset_to_hhmm(t) for t in route.arrive_times
        )
        print(f"路线{i+1} [{route.vehicle_type_id}]: {nodes_str}")
        print(f"  到达时刻: {times_str}")
        print(f"  成本: 固定{route.fixed_cost:.0f} + 行驶{route.travel_cost:.1f}"
              f" + 碳排{route.carbon_cost:.1f} + 惩罚{route.penalty_cost:.1f}"
              f" = {route.total_cost:.1f} 元")
```

---

## 14. 依赖与运行

```bash
# 环境
pip install pandas openpyxl numpy scipy

# 运行
python main.py --problem 1        # 问题1
python main.py --problem 2        # 问题2
python main.py --problem 3 --event cancel --node 15 --time 09:30  # 问题3示例

# main.py 结构
if __name__ == '__main__':
    p1_sol = solve_problem1()                       # 必须先跑，后两问依赖
    p2_sol = solve_problem2(p1_sol)
    solve_problem3_dynamic(p1_sol, event, time)
```

---

## 15. 已知数据事实备查

| 字段 | 值 |
|------|-----|
| 配送中心节点ID | 0 |
| 配送中心坐标 | (20.0, 20.0) |
| 城市中心（绿区圆心）坐标 | (0.0, 0.0) |
| 绿区半径 | 10.0 km |
| 绿区客户ID | 1–15（共15个） |
| 今日有需求的绿区客户 | 2,3,4,5,6,7,8,9,10,11,12,13（共12个） |
| 今日无需求客户 | 1,14,15,17,18,20,21,22,23,96（共10个） |
| 活跃客户数 | 88 |
| 虚拟节点数（拆分后）| 约150–180个 |
| 距离矩阵尺寸 | 99×99（含配送中心） |
| 最大单客户需求 | 客户55：12197.6 kg → 需5次配送 |
| 时间窗最小宽度 | 48分钟 |
| 时间窗最大宽度 | 90分钟 |
| 时间窗均值宽度 | 72.2分钟 |
| 总需求 | 285,122.6 kg，772.4 m³ |
