# 第二问绿色配送区限行政策下车辆路径调度收官总结

## 1. 问题定位与建模边界

第十八届“华中杯”大学生数学建模挑战赛 A 题第二问在第一问静态配送调度模型的基础上，加入绿色配送区限行政策：燃油车在绿色配送区限行时段内不能服务绿色区客户。第二问的正式目标仍然是题面给出的总配送成本最小：

$$
\min C=C_{\mathrm{fixed}}+C_{\mathrm{energy}}+C_{\mathrm{carbon}}+C_{\mathrm{tw}}.
$$

其中时间窗为软约束，早到等待和迟到均通过罚金计入 \(C_{\mathrm{tw}}\)。绿色配送区限行是硬约束，正式可行解必须满足政策冲突数为 0。政策违规不能作为第五个官方成本项，只能用于搜索过程中的可行性过滤或辅助评分。

本项目采用的政策解释如下：

1. 绿色配送区为以城市中心 \((0,0)\) 为圆心、半径 \(10\,\mathrm{km}\) 的圆形区域。
2. 配送中心在坐标文件中为 \((20,20)\)，不是绿色区圆心。
3. 时间统一用从 0:00 起的分钟数表示，08:00 为 480，16:00 为 960。
4. 限行窗口按 \([480,960)\) 处理，因此燃油车在 16:00 准点到达绿色客户视为合法。
5. 题面没有道路几何数据，因此只能检测车辆“服务绿色区客户”的政策合法性，不能声称检测了道路穿越绿色区。
6. 题面没有给出 24:00 硬返库约束，返库时间只作为诊断指标，不作为第二问正式可行性筛选条件。

## 2. 数据事实与预处理

第二问沿用第一问的数据处理入口：

```python
from green_logistics.data_processing import load_problem_data
```

关键数据事实如下。

| 指标 | 数值 |
| --- | ---: |
| 原始订单数 | 2169 |
| 坐标节点数 | 99，含配送中心和 98 个客户 |
| 有订单客户数 | 88 |
| 默认拆分后服务节点数 | 148 |
| 有订单绿色区客户数 | 12 |
| 默认拆分后绿色区服务节点数 | 19 |
| 总重量需求 | 285122.647 kg |
| 总体积需求 | 772.431 m3 |
| 绿色区总重量需求 | 35970.65 kg |
| 绿色区总体积需求 | 103.96 m3 |

由于数据中存在单个原始订单重量超过最大车辆载重的情况，如果坚持订单不可拆分会导致数据本身不可行。因此本项目将客户总需求拆分为虚拟服务节点。算法内部服务节点使用 `node_id`，距离矩阵和坐标查询仍使用原始 `customer_id`，两者不能混用。

第二问比较了三种显式服务节点方案：

| 方案 | 服务节点数 | 绿色服务节点数 | 用途 |
| --- | ---: | ---: | --- |
| `DEFAULT_SPLIT` | 148 | 19 | 沿用第一问默认拆分，作为正式推荐主线 |
| `GREEN_E2_ADAPTIVE` | 166 | 37 | 全量绿色客户按 E2 容量细拆，检验小电车释放潜力 |
| `GREEN_HOTSPOT_PARTIAL` | 153 | 24 | 只对少数高风险绿色客户做局部 E2 细拆 |

最终结果表明，全量 E2 细拆和局部热点细拆目前均没有降低官方总成本，因此正式答案采用 `DEFAULT_SPLIT`。

## 3. 模型假设

为保持题意、物理规律和当前数据一致，第二问采用以下假设：

1. 客户需求可拆分为多个虚拟服务节点，每个虚拟节点必须完整服务一次。
2. 每条 `Route` 表示一次从配送中心出发并返回配送中心的 depot-to-depot 趟次。
3. 物理车辆可以连续执行多个同车型趟次，固定成本按启用的物理车辆计，而不是按趟次计。
4. 车辆到达早于时间窗下界时等待至下界后服务，到达晚于时间窗上界时产生迟到罚金；服务时间固定为 20 分钟。
5. 行驶时间按时变速度分段积分，满足 FIFO 逻辑，不使用“出发时速度乘全程距离”的粗略近似。
6. 能耗随时段速度和车辆当前剩余载重变化。速度服从补充说明给出的正态分布，能耗二次函数使用 \(E[v^2]=\mu^2+\sigma^2\) 的 Jensen 修正。
7. 17:00 后题面没有继续给出速度分布，本实现延用普通时段速度 \(N(35.4,5.2^2)\)，论文中需说明为延拓假设。
8. 电动车也按题面给定的电力碳排因子计入碳排成本，不把电动车视为零碳。

## 4. 符号说明

| 符号 | 含义 |
| --- | --- |
| \(0\) | 配送中心 |
| \(V\) | 原始客户集合 |
| \(S\) | 虚拟服务节点集合 |
| \(G\subseteq V\) | 绿色配送区客户集合 |
| \(K\) | 车辆类型集合，含 F1、F2、F3、E1、E2 |
| \(M_k\) | 车型 \(k\) 的物理车辆集合 |
| \(R\) | depot-to-depot 趟次集合 |
| \(c(i)\) | 虚拟服务节点 \(i\) 对应的原始客户 |
| \(q_i,u_i\) | 服务节点 \(i\) 的重量和体积需求 |
| \([e_i,l_i]\) | 服务节点 \(i\) 的软时间窗 |
| \(Q_k,U_k\) | 车型 \(k\) 的载重和容积上限 |
| \(N_k\) | 车型 \(k\) 的可用物理车辆数 |
| \(d_{ab}\) | 原始节点 \(a,b\) 之间路网距离 |
| \(a_i\) | 车辆到达服务节点 \(i\) 的时间 |
| \(b_i\) | 服务节点 \(i\) 的开始服务时间 |
| \(W_i,L_i\) | 早到等待分钟数和迟到分钟数 |
| \(s\) | 单点服务时间，取 20 min |
| \(\tau_{ab}(t)\) | 时刻 \(t\) 从原始节点 \(a\) 到 \(b\) 的时变行驶时间 |

可用如下决策变量描述论文中的数学模型：

| 变量 | 含义 |
| --- | --- |
| \(x_{ijr}\in\{0,1\}\) | 趟次 \(r\) 是否从服务节点 \(i\) 直接到服务节点 \(j\) |
| \(y_{rk}\in\{0,1\}\) | 趟次 \(r\) 是否使用车型 \(k\) |
| \(z_{mr}\in\{0,1\}\) | 物理车辆 \(m\) 是否执行趟次 \(r\) |
| \(u_m\in\{0,1\}\) | 物理车辆 \(m\) 是否被启用 |
| \(T_r\) | 趟次 \(r\) 的出发时间 |

代码实现中，ALNS 搜索的是尚未分配物理车辆的 `RouteSpec`，调度器将其转化为带车型、出发时间和物理车辆编号的 `Route`，再汇总为 `Solution`。

## 5. 成本模型

### 5.1 固定成本

固定成本按启用物理车辆数计算：

$$
C_{\mathrm{fixed}}=400\sum_{m}u_m.
$$

第二问推荐方案启用 45 辆物理车，因此

$$
C_{\mathrm{fixed}}=45\times 400=18000.
$$

### 5.2 时变行驶时间

补充说明给出的速度分布如下。

| 时段 | 状态 | 速度分布 |
| --- | --- | --- |
| 08:00-09:00 | 拥堵 | \(N(9.8,4.7^2)\) |
| 09:00-10:00 | 畅通 | \(N(55.3,0.1^2)\) |
| 10:00-11:30 | 普通 | \(N(35.4,5.2^2)\) |
| 11:30-13:00 | 拥堵 | \(N(9.8,4.7^2)\) |
| 13:00-15:00 | 畅通 | \(N(55.3,0.1^2)\) |
| 15:00-17:00 | 普通 | \(N(35.4,5.2^2)\) |
| 17:00-24:00 | 延拓普通 | \(N(35.4,5.2^2)\) |

若车辆在时刻 \(t\) 从原始节点 \(a\) 行驶到 \(b\)，路段可能跨越多个速度时段。设跨越的子时段集合为 \(P_{ab}(t)\)，子时段距离为 \(\Delta d_p\)，速度均值为 \(\mu_p\)，则：

$$
\tau_{ab}(t)=\sum_{p\in P_{ab}(t)}\frac{60\Delta d_p}{\mu_p}.
$$

到达时间递推为：

$$
a_j=t_i+\tau_{c(i),c(j)}(t_i),
$$

其中 \(t_i=b_i+s\) 为离开上一服务节点的时间。

### 5.3 时间窗罚金

时间窗为软约束：

$$
W_i=\max(e_i-a_i,0),
$$

$$
L_i=\max(a_i-l_i,0).
$$

早到等待成本为 20 元/小时，迟到成本为 50 元/小时，因此：

$$
C_{\mathrm{tw}}=\sum_{i\in S}\left(\frac{20}{60}W_i+\frac{50}{60}L_i\right).
$$

服务开始时间为：

$$
b_i=\max(a_i,e_i).
$$

### 5.4 能耗成本

燃油车和电动车的基准能耗函数分别为：

$$
g_F(v)=0.0025v^2-0.2554v+31.75,
$$

$$
g_E(v)=0.0014v^2-0.12v+36.19.
$$

速度服从正态分布，因此期望能耗使用二阶矩：

$$
E[g_F(v)]=0.0025(\mu_p^2+\sigma_p^2)-0.2554\mu_p+31.75,
$$

$$
E[g_E(v)]=0.0014(\mu_p^2+\sigma_p^2)-0.12\mu_p+36.19.
$$

设车辆进入弧段前剩余载重为 \(w\)，车型载重上限为 \(Q_k\)，载重比例为 \(\lambda=w/Q_k\)。燃油车载重修正系数取 \(1+0.40\lambda\)，电动车取 \(1+0.35\lambda\)。跨时段弧段的燃油消耗和电耗为：

$$
E^F_{ab}=(1+0.40\lambda)\sum_{p\in P_{ab}(t)}\frac{\Delta d_p}{100}E[g_F(v_p)],
$$

$$
E^E_{ab}=(1+0.35\lambda)\sum_{p\in P_{ab}(t)}\frac{\Delta d_p}{100}E[g_E(v_p)].
$$

燃油价格为 7.61 元/L，电价为 1.64 元/kWh：

$$
C_{\mathrm{energy}}=7.61\sum E^F_{ab}+1.64\sum E^E_{ab}.
$$

### 5.5 碳排成本

燃油碳排因子为 2.547 kg/L，电力碳排因子为 0.501 kg/kWh，碳价为 0.65 元/kg：

$$
G=2.547\sum E^F_{ab}+0.501\sum E^E_{ab},
$$

$$
C_{\mathrm{carbon}}=0.65G.
$$

## 6. 约束条件

### 6.1 服务覆盖约束

每个虚拟服务节点必须且只能被服务一次：

$$
\sum_{r\in R}\sum_j x_{ijr}=1,\quad \forall i\in S.
$$

正式结果中 `missing_node_ids=[]` 且 `duplicate_node_ids=[]`，说明覆盖完整且无重复服务。

### 6.2 容量约束

每个趟次的重量和体积不得超过所用车型容量：

$$
\sum_{i\in r}q_i\le Q_k,\quad \sum_{i\in r}u_i\le U_k,\quad \forall r,k.
$$

正式结果 `is_capacity_feasible=True`。

### 6.3 车辆数量与多趟复用约束

每类车型启用物理车辆数不得超过车队给定数量：

$$
\sum_{m\in M_k}u_m\le N_k,\quad \forall k\in K.
$$

同一物理车辆执行多个趟次时，后一趟出发时间不得早于前一趟返库时间：

$$
T_{r_2}\ge \mathrm{return}_{r_1},\quad \text{if }z_{mr_1}=z_{mr_2}=1\text{ and }r_2\text{ follows }r_1.
$$

正式推荐方案启用 `E1:10, F1:35`，不超过题面车队数量。

### 6.4 绿色配送区硬约束

定义绿色客户集合：

$$
G=\left\{i\in V:\sqrt{x_i^2+y_i^2}\le 10\right\}.
$$

若车型 \(k\) 为燃油车，且服务节点 \(i\) 对应客户 \(c(i)\in G\)，则限行时段内不得服务：

$$
\neg\left(480\le a_i<960\right),\quad \forall i\in S,\ c(i)\in G,\ k\in K_F.
$$

该约束是硬约束，正式解必须满足 `policy_conflict_count=0`。

### 6.5 时间递推与软时间窗约束

服务时间、等待时间和迟到时间由到达时间递推得到：

$$
b_i=\max(a_i,e_i),\quad t_i=b_i+s,
$$

$$
W_i\ge e_i-a_i,\quad W_i\ge0,
$$

$$
L_i\ge a_i-l_i,\quad L_i\ge0.
$$

时间窗不作为硬约束强制全部准时，而是通过 \(C_{\mathrm{tw}}\) 进入目标函数。

## 7. 求解算法与工程实现

第二问求解框架没有推翻第一问已验证的数据层和代价层，而是在其上新增政策层、变体层和政策感知搜索层。

### 7.1 核心模块

| 模块 | 作用 |
| --- | --- |
| `green_logistics/problem_variants.py` | 构造 `DEFAULT_SPLIT`、`GREEN_E2_ADAPTIVE`、`GREEN_HOTSPOT_PARTIAL` |
| `green_logistics/policies.py` | 绿色区限行政策检查和搜索辅助罚项 |
| `green_logistics/problem2_engine.py` | 第二问独立求解引擎，统一 ALNS、scheduler 和推荐规则 |
| `green_logistics/scheduler.py` | 物理车辆多趟排班，含 EV reservation 搜索辅助 |
| `green_logistics/operators.py` | ALNS 破坏/修复算子，含 EV blocking-chain 实验算子 |
| `green_logistics/diagnostics.py` | 迟到诊断、政策冲突诊断、EV 级联诊断 |
| `problems/problem2.py` | 第二问正式运行入口 |
| `problems/experiments/problem2_parameter_sweep.py` | 多参数实验账本 |

### 7.2 ALNS 主流程

求解过程可概括为：

1. 读取并构造显式服务节点变体。
2. 用启发式方法构造初始 `RouteSpec` 集合。
3. 通过 ALNS 迭代执行破坏和修复，生成候选趟次集合。
4. 调用 `schedule_route_specs()` 将趟次分配给物理车辆并确定出发时间。
5. 用 `GreenZonePolicyEvaluator` 检查政策硬约束。
6. 对完整、容量可行且政策冲突为 0 的解，按官方总成本比较。
7. 输出推荐解、候选变体比较、政策冲突表、路线表、停靠表、迟到诊断和可视化图表。

### 7.3 EV reservation 搜索辅助

旧正式解的最大迟到来自电动车多趟复用级联：部分非绿色、燃油车也可完成的任务占用了稀缺 E1 车辆，使绿色区早时间窗任务被推迟。为此，本轮加入 EV reservation 辅助评分。

该机制只影响调度候选选择，不进入官方成本公式。其逻辑为：

1. 当前问题存在绿色区早时间窗节点。
2. 某候选趟次使用电动车。
3. 该趟次不含绿色区服务节点。
4. 该趟次容量上可由至少一种燃油车完成。

满足上述条件时，在 scheduler 的搜索评分中加入机会成本罚项。本次正式结果使用：

```powershell
--use-ev-reservation --ev-reservation-penalty 250
```

这使算法倾向于把稀缺 E1 留给确实受政策约束影响的绿色区服务，而不是随意用于可由燃油车承担的非绿色任务。需要强调，该罚项不是第五个成本项，最终推荐仍按官方总成本筛选。

### 7.4 政策专用算子与服务质量对照

实验中还测试了 `--use-policy-operators` 和 `ev_blocking_chain_remove`。这一路线能显著改善服务质量，但在当前参数下总成本较高，因此不作为正式答案。

最值得保留的服务质量对照方案为：

```powershell
python problems/experiments/problem2_parameter_sweep.py --iterations 40 --remove-counts 16 --seeds 20260427 --variants default_split --use-policy-operators --use-ev-reservation --ev-reservation-penalties 500 --output-dir outputs/problem2_experiments/formal_screen_policy_ev_p500
```

该方案结果为：总成本 `50770.72`，政策冲突 `0`，迟到点 `2`，最大迟到 `5.93 min`。它不满足最低官方总成本目标，但可在论文中作为“服务质量优先倾向的灵敏度方案”说明成本和准时性之间的权衡。

## 8. 正式结果

第二问正式命令为：

```powershell
python problems/problem2.py --iterations 40 --remove-count 16 --seed 20260427 --use-ev-reservation --ev-reservation-penalty 250 --output-dir outputs/problem2
```

推荐方案：`DEFAULT_SPLIT`。

| 指标 | 数值 |
| --- | ---: |
| 总成本 | 49239.78 |
| 固定成本 | 18000.00 |
| 能源成本 | 24551.90 |
| 碳排成本 | 5301.72 |
| 时间窗罚金 | 1386.17 |
| 总距离 | 13093.90 km |
| 碳排放 | 8156.49 kg |
| depot-to-depot 趟次数 | 115 |
| 物理车辆使用 | E1:10, F1:35 |
| 政策冲突数 | 0 |
| 服务覆盖完整 | True |
| 容量可行 | True |
| 迟到点数 | 12 |
| 最大迟到 | 129.44 min |
| 午夜后返库 | 0 |

正式输出文件包括：

- `outputs/problem2/recommendation.json`
- `outputs/problem2/variant_comparison.csv`
- `outputs/problem2/default_split/summary.json`
- `outputs/problem2/default_split/route_summary.csv`
- `outputs/problem2/default_split/stop_schedule.csv`
- `outputs/problem2/default_split/problem2_policy_conflicts.csv`
- `outputs/problem2/default_split/late_stop_diagnosis.csv`

## 9. 候选方案比较

| 方案 | 总成本 | 政策冲突 | 服务节点 | 绿色节点 | 物理车辆 | 迟到点 | 最大迟到 |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `DEFAULT_SPLIT` | 49239.78 | 0 | 148 | 19 | E1:10, F1:35 | 12 | 129.44 |
| `GREEN_E2_ADAPTIVE` | 57504.49 | 0 | 166 | 37 | E1:10, E2:3, F1:44 | 24 | 253.00 |
| `GREEN_HOTSPOT_PARTIAL` | 52312.11 | 0 | 153 | 24 | E1:10, E2:1, F1:35 | 22 | 119.21 |
| `POLICY_OPS + EV_RESERVATION_P500` | 50770.72 | 0 | 148 | 19 | E1:10, F1:36 | 2 | 5.93 |

解释：

1. `DEFAULT_SPLIT` 的官方总成本最低，因此作为正式推荐。
2. `GREEN_E2_ADAPTIVE` 全量绿色细拆释放了 E2 参与可能，但服务节点数增加后引入更多趟次与排班复杂度，当前总成本显著上升。
3. `GREEN_HOTSPOT_PARTIAL` 是更温和的局部细拆，但仍未超过默认拆分的成本表现。
4. `POLICY_OPS + EV_RESERVATION_P500` 服务质量最好，但总成本高于正式推荐 `1530.94`，只能作为灵敏度或服务质量对照方案。

## 10. 与第一问结果比较

第一问正式结果总成本为 `48644.68`。第二问推荐方案总成本为 `49239.78`，增加：

$$
49239.78-48644.68=595.10.
$$

成本分项变化如下。

| 成本项 | 第一问 | 第二问 | 变化 |
| --- | ---: | ---: | ---: |
| 固定成本 | 17200.00 | 18000.00 | +800.00 |
| 能源成本 | 25091.79 | 24551.90 | -539.89 |
| 碳排成本 | 5419.37 | 5301.72 | -117.65 |
| 时间窗罚金 | 933.53 | 1386.17 | +452.64 |
| 总成本 | 48644.68 | 49239.78 | +595.10 |

这符合建模逻辑：在相同数据和目标下，加入绿色区硬约束会压缩可行域，理论最优成本不应低于无政策约束的同一模型。当前第二问启发式解比第一问高 595.10，主要代价来自启用车辆数增加和时间窗罚金增加；同时路线重排降低了部分能源和碳排成本。

## 11. 诊断与解释性

正式结果仍有 12 个迟到服务点，迟到来自两类原因：

| 类型 | 数量 | 含义 |
| --- | ---: | --- |
| Type B | 9 | 同一趟次若从 08:00 新车出发可准时，但物理车辆多趟复用导致级联迟到 |
| Type C | 3 | 路线内部顺序或趟次组合导致即使新车出发也仍有迟到 |

最大迟到出现在绿色区客户 7 的某个拆分节点，迟到 `129.44 min`，主要属于 EV 资源级联问题。与旧正式解相比，本轮 EV reservation 降低了总成本，但最大迟到没有同步下降。因此论文中应表述为：正式模型以总成本最小为主目标，服务质量指标用于解释和灵敏度比较，而不是改变目标函数。

若论文需要展示“准时性改善潜力”，可引用 `POLICY_OPS + EV_RESERVATION_P500` 对照方案。该方案把最大迟到降至 `5.93 min`，但总成本增加至 `50770.72`，说明准时性改善需要付出更高固定、能源和碳排成本。

## 12. 可视化与论文呈现建议

当前正式输出已经包含以下图表：

| 文件 | 论文用途 |
| --- | --- |
| `outputs/problem2/default_split/cost_breakdown.png` | 展示第二问推荐方案成本构成 |
| `outputs/problem2/default_split/vehicle_usage.png` | 展示启用车辆结构 |
| `outputs/problem2/default_split/time_windows.png` | 展示到达时间、等待和迟到情况 |
| `outputs/problem2/default_split/route_map.png` | 展示客户空间分布和路线结构 |

建议论文第二问部分补充以下表图：

1. 第一问与第二问成本分项堆叠柱状图，突出政策约束带来的成本变化。
2. 三个正式候选方案的总成本、政策冲突和迟到指标对比表。
3. `DEFAULT_SPLIT` 与 `POLICY_OPS + EV_RESERVATION_P500` 的成本和服务质量权衡图。
4. 绿色配送区客户空间分布图，标出以 \((0,0)\) 为圆心、半径 10 km 的绿色区边界。
5. 迟到诊断表，说明剩余迟到主要来自多趟物理车辆复用级联，而不是政策违规。

论文中使用路线图时要注意：该图只能说明客户点和配送访问顺序，不能解释为真实道路穿越绿色区检测。

## 13. 创新性与合理性说明

第二问方案的主要特点如下：

1. 政策约束与官方目标严格分离。绿色限行作为硬约束，搜索辅助罚项不进入官方成本。
2. 使用时变分段积分计算行驶时间和能耗，避免用单一速度粗算跨时段行驶。
3. 保持 `node_id` 与 `customer_id` 映射清晰，避免虚拟服务节点误用于距离矩阵。
4. 固定成本按物理车辆计，并允许物理车辆多趟复用，符合题面车队规模与大批量需求数据。
5. 通过显式数据变体比较 `DEFAULT_SPLIT`、全量绿色 E2 细拆和局部热点细拆，避免只凭直觉改拆分规则。
6. 引入 EV reservation 作为搜索层机会成本，解释性强：稀缺大电车优先保留给政策限制更强的绿色区任务。
7. 保留服务质量优先对照方案，展示总成本最优与准时性改善之间的可量化权衡。

## 14. 局限性与后续第三问接口

本解法为启发式算法结果，不提供全局最优证明。后续若有更多计算时间，可继续做多 seed、多 remove-count 和更长迭代的参数搜索，但必须继续以官方总成本作为推荐标准。

当前模型仍有以下局限：

1. 没有道路几何，不能约束车辆路径穿越绿色区，只能约束绿色区客户服务行为。
2. 题面未给出充电、续航、装卸排队等约束，因此没有额外引入电动车续航或充电调度。
3. 17:00 后速度分布为模型延拓假设，需要在论文假设中说明。
4. 当前 `GREEN_HOTSPOT_PARTIAL` 只是基于诊断的有限候选，不代表所有局部拆分方案都已穷尽。

第三问可以复用第二问封装出的接口：

| 可复用模块 | 第三问用途 |
| --- | --- |
| `ProblemVariant` | 在动态事件后重建受影响服务节点集 |
| `Problem2Engine` | 作为带政策硬约束的静态重优化内核 |
| `schedule_route_specs()` | 对新增或扰动趟次重新排班 |
| `GreenZonePolicyEvaluator` | 保证动态调整后仍满足绿色区限行 |
| `diagnostics.py` | 输出动态扰动后的延误、政策冲突和车辆级联诊断 |
| `problem2_parameter_sweep.py` | 为第三问场景实验保留可复现账本格式 |

第三问如果涉及订单新增、车辆故障或道路扰动，应在第二问模型上增加“已执行部分冻结”和“未执行部分重优化”机制，而不是推翻现有成本、政策和排班基础。

## 15. 文件归档状态

第二问当前正式文件归档如下：

| 路径 | 状态 | 用途 |
| --- | --- | --- |
| `outputs/problem2/` | 正式结果 | 第二问主答案和三候选比较 |
| `outputs/problem2_previous_49888_20260425/` | 历史备份 | EV reservation 优化前的旧正式结果 |
| `outputs/problem2_experiments/formal_screen_policy_ev_p500/` | 服务质量对照 | 2 个迟到点、最大迟到 5.93 min 的非推荐方案 |
| `docs/results/problem2_green_zone_policy_summary.md` | 简版结果摘要 | 快速查看第二问正式结果 |
| `docs/results/problem2_modeling_and_solution_closeout.md` | 完整收官总结 | 论文写作母稿 |
| `docs/design/problem2_subdialogue3_optimization_roadmap.md` | 技术路线记录 | 记录本轮优化判断和实验路线 |

已并入正式输出的中间候选目录 `outputs/problem2_ev_reservation_p250/` 和 `outputs/problem2_ev_reservation_p250_full/` 已清理，避免后续会话误认多个正式答案。

## 16. 可复现实验命令

正式第二问：

```powershell
python problems/problem2.py --iterations 40 --remove-count 16 --seed 20260427 --use-ev-reservation --ev-reservation-penalty 250 --output-dir outputs/problem2
```

服务质量对照：

```powershell
python problems/experiments/problem2_parameter_sweep.py --iterations 40 --remove-counts 16 --seeds 20260427 --variants default_split --use-policy-operators --use-ev-reservation --ev-reservation-penalties 500 --output-dir outputs/problem2_experiments/formal_screen_policy_ev_p500
```

回归测试：

```powershell
pytest -q
```

## 17. 外部方法参考

为保证论文结构和算法叙述符合常见数学建模与车辆路径问题写法，本轮收官参考了以下公开材料的写作和方法背景，但最终模型、公式和结论均以题面、补充说明、本项目代码和输出文件为准：

1. [全国大学生数学建模竞赛论文格式规范](https://www.mcm.edu.cn/upload_cn/node/775/cQMeL0YY905244c8bd4b9af832f1699446d8385e.pdf)，用于校准论文中“模型假设、符号说明、模型建立、求解与结果分析”的组织方式。
2. [The time-dependent vehicle routing problem with soft time windows and stochastic travel times](https://www.sciencedirect.com/science/article/pii/S0968090X1400223X)，用于支持采用软时间窗罚金和时变行驶时间建模。
3. [Ropke and Pisinger 的 ALNS with pickup and delivery time windows 论文条目](https://www.scirp.org/reference/ReferencesPapers?ReferenceID=1429174)，用于说明 ALNS 在含时间窗车辆路径问题中的经典来源。
4. [An adaptive large neighborhood search heuristic for the Pollution-Routing Problem](https://dblp.org/rec/journals/eor/DemirBL12)，用于支持把燃料、碳排和路径调度联合考虑的绿色物流建模背景。
5. [Adaptive Large Neighborhood Search Metaheuristic for Vehicle Routing Problem with Multiple Synchronization Constraints and Multiple Trips](https://arxiv.org/abs/2312.09414)，用于说明多趟车辆路径问题中采用 ALNS 处理复杂调度约束的合理性。
