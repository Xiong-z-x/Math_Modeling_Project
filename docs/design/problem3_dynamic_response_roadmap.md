# 第三问动态事件响应综合路线图

> 状态：2026-04-26 已进入实现并生成正式情景输出。第三问实现见
> `green_logistics/dynamic.py`、`green_logistics/problem3_engine.py` 和
> `problems/problem3.py`；正式情景输出见 `outputs/problem3/`，论文写作摘要见
> `docs/results/problem3_dynamic_response_summary.md`。

## 1. 题意复核

原题第三问为“动态事件下的实时车辆调度策略”：配送过程中可能出现订单取消、新增订单、配送地址变更或时间窗调整等突发事件，要求设计能实时响应并调整路径的动态调度策略，并给出一个或几个突发事件下的车辆调度策略。

已经确认的边界如下：

- 题面列明的事件类型只有四类：订单取消、新增订单、配送地址变更、时间窗调整。
- 题面没有给出具体事件时刻、订单编号、客户编号、新增订单坐标、需求量或新时间窗。
- 题面没有新增官方成本项。正式目标仍应以固定成本、能源成本、碳排成本、软时间窗罚金为核心；路线扰动、响应时间和稳定性只能作为辅助评价指标，除非论文中明确写作“情景辅助指标”。
- 第三问没有明写“在问题二基础上”，但全题背景是绿色物流，且第二问绿色配送区政策是核心情境。正式主线建议继承第二问政策，以 `outputs/problem2/` 的 `DEFAULT_SPLIT` 为动态基准；如果论文需要解释歧义，可补充一个“不继承限行时以 `outputs/problem1/` 为基准”的敏感性说明。
- 新增订单或地址变更若没有新距离矩阵，不能凭空生成真实道路距离。可行做法是使用既有客户点作为代理情景，或把新增订单合并到已有客户的额外需求中，并明确标注为“情景假设”。

## 2. 三份参考方案审计

| 来源 | 一针见血的洞察 | 局限与需修正处 | 采纳方式 |
| --- | --- | --- | --- |
| Claude 第三问完整方案 | 题意边界稳，强调“无官方动态数据时构造 2-3 个情景”；提出冻结已完成服务、局部重插入、轻量 ALNS 和输出对比表，适合作为论文叙事骨架。 | 伪代码假设存在 `route.id`、可变路线对象、`load_solution` 等当前代码没有的接口；部分新订单节点示例若用全新 node_id，必须同步距离和需求映射，否则会破坏 `customer_id`/`node_id` 规则。 | 采用其情景假设和输出结构，但工程实现必须改成当前 `Solution.routes`、CSV 输出和 `RouteSpec` 可承载的形式。 |
| GPT deep-research report | 最贴近现有代码：指出 `evaluate_route()` 目前只能 depot-to-depot，`scheduler.py` 没有 warm start，`RouteSpec` 没有物理车辆链，距离矩阵只覆盖 depot+98 客户；推荐事件触发滚动重优化和服务完成锚点。 | 偏保守，若只做未发车趟次重排，动态响应的展示张力不足；后续应逐步支持在途车辆“当前弧锁定 + 必达锚点”。 | 作为主工程路线：先最小侵入扩展动态状态和 warm-start scheduler，再做局部 ALNS。 |
| Gemini 绿色物流调度项目审计 | 强调 DVRP-TW、事件驱动 rolling horizon、冻结轨迹、在途状态锁定、节点/边稳定性惩罚，且提醒轻量 ALNS 不能碰冻结前缀。 | “重构 Solution 状态机”成本偏高；稳定性惩罚不能写成题面官方成本；没有道路几何，不能检测燃油车“路径穿越”绿色区，只能检测服务绿色客户；“毫秒级”响应表述不现实。 | 采用其状态分区、稳定性指标和动态算子思想，但作为辅助评分与分阶段增强，不推翻前两问架构。 |

综合判断：三份文件最强的共同点是“事件驱动滚动时域 + 冻结已执行事实 + 局部重优化”。最终路线不应全量重写，而是在当前数据层、成本层、时变行驶层、物理车辆排班层和第二问政策层上增加动态外壳。

## 3. 当前代码约束

后续实现必须承认以下代码事实：

- `ProblemData` 使用虚拟 `service_node_id` 承载拆分节点，距离矩阵使用原始 `customer_id`，两者不能混用。
- `green_logistics/solution.py` 的 `evaluate_route()` 默认从 depot 出发并回 depot，适合静态趟次，不直接支持“从当前客户/当前时间继续行驶”。
- `green_logistics/scheduler.py` 从 `DAY_START_MIN` 开始给物理车辆排班，没有 `initial_vehicle_states` 或锁定路线段接口。
- 物理车辆链只在已排程的 `Solution.routes` 和输出 CSV 中可见，`RouteSpec` 本身没有 predecessor/successor 信息。
- `policies.py` 检测的是燃油车在 `[480, 960)` 服务绿色区客户；项目没有道路几何，不能判断车辆行驶轨迹是否穿越绿色区。
- `route_summary.csv` 和 `stop_schedule.csv` 已包含 `trip_id`、`physical_vehicle_id`、`depart_min`、`return_min`、`arrival_min`、`departure_min`、`load_before_service_kg`、`load_after_service_kg`，足以构建动态快照和冻结前缀。

## 4. 动态状态建模

动态事件时刻记为 `t_event`。第三问核心不是重跑静态 VRP，而是把当前方案切分为“已不可逆事实”和“可调整未来”。

推荐状态集合如下：

- `completed_visits`：`departure_min <= t_event` 的服务点，固定为已完成，不得删除、重排或重复服务。
- `active_trip_locks`：`depart_min <= t_event < return_min` 的在途趟次。若车辆位于某条客户间弧上，当前弧的下一计划节点应作为必达锚点；MVP 阶段可退化为“以最近已完成服务点或 depot 为锚点，整条在途趟次剩余部分不跨车转移”。
- `pending_unstarted_visits`：所在趟次 `depart_min > t_event` 的未装车节点，可重新分配、合并、拆分或插入新需求。
- `onboard_pending_visits`：所在趟次已出发但尚未服务的节点。这些货物已经在车上，原则上不能转移给其他车辆；最多在同一物理车辆后续序列中重排，且需要保留当前载重链。
- `cancelled_visits`：取消订单对应节点。若取消发生在趟次出发前，可从待装载需求中删除；若取消发生在车辆出发后，不能默认立刻降低车载重量，除非显式建模中途卸货或回库。
- `new_requests`：新增订单。若事件发生后车辆未回 depot，新增货物不能凭空装上在途车辆；应优先分配给未发车趟次、可回库后再发车的物理车辆，或新增 depot-to-depot 趟次。
- `changed_requests`：地址变更或时间窗调整。地址变更只能映射到现有客户点或情景代理点；时间窗调整可直接覆盖对应服务节点的 `time_windows`。

这个分层比三份参考文件更保守，但更符合配送物理事实：路线可以重排，货物不能瞬移。

## 5. 候选算法路线比较

| 路线 | 投入 | 产出 | 适用阶段 | 结论 |
| --- | --- | --- | --- | --- |
| A. 规则驱动快速修复 | 低：删除取消节点、单点最小成本插入、时间窗局部提前。 | 响应快、易解释、测试简单，但容易陷入局部次优。 | MVP 和兜底策略。 | 必做，作为所有事件的初始可行解生成器。 |
| B. 局部重插入 + 轻量 ALNS | 中：需要冻结保护、动态候选池、局部 destroy/repair、短预算迭代。 | 能在有限时间内改善成本和迟到，复用现有 ALNS 思想。 | 正式主求解器。 | 推荐作为第三问核心求解器。 |
| C. 滚动时域重优化 | 中高：需要动态状态、warm-start scheduler、事件日志和多轮状态推进。 | 最贴合题意，可处理多事件并保持物理连续性。 | 第三问总体框架。 | 必做框架，内部求解用 A+B。 |
| D. 多情景响应评估 | 低到中：主要是事件脚本和输出对比。 | 解决题面未给动态数据的问题，论文可解释性强。 | 正式展示层。 | 必做，至少 3 个代表性情景。 |

最终组合：`C` 做外层事件驱动滚动框架，`A` 生成快速可行修复，`B` 在短预算内优化，`D` 负责输出和论文解释。

## 6. 推荐技术路线

### P0：文档、测试和情景定义先行

- 新增 `tests/test_dynamic.py`，先覆盖冻结规则、未服务集合、取消/新增/时间窗调整的 ledger 行为。
- 在 `docs/design/problem3_dynamic_response_roadmap.md` 固化题意边界、政策继承假设和场景数据来源。
- 情景不硬编码神秘节点，优先从基准 `stop_schedule.csv` 自动选取满足条件的代表节点，保证可复现。

### P1：最小可行动态调度

新增 `green_logistics/dynamic.py`：

- `DynamicEvent`
- `DynamicScenario`
- `VisitSnapshot`
- `VehicleSnapshot`
- `FrozenPlan`
- `ResidualRequestPool`
- `DynamicScenarioResult`

先支持三类物理干净事件：

1. 未发车趟次中的订单取消。
2. 新增订单合并到既有客户点，分配给未发车或回库后车辆。
3. 未服务节点时间窗提前/延后。

此阶段不允许把已出发车辆上的货物转移给别的车。

### P2：调度器 warm start

扩展 `green_logistics/scheduler.py`，但保持默认行为兼容：

- 增加 `initial_vehicle_states`，描述物理车辆在 `t_event` 后何时、何地可用。
- 增加 `locked_routes` 或 `frozen_routes`，用于把已经执行和锁定的趟次作为常量带入总结果。
- 固定成本仍按物理车辆唯一编号计，不按新增趟次数计。

### P3：动态路线评估

优先新增独立函数而不是立即重写 `evaluate_route()`：

- `evaluate_residual_route(...)`：支持从 depot 或指定锚点、指定出发时间开始评估后续序列。
- 对 depot-to-depot 未发车趟次仍复用现有 `evaluate_route()`。
- 对在途高级场景，必须显式传入当前载重，避免取消订单后错误享受“瞬间卸重”收益。

### P4：Problem 3 引擎和命令入口

新增：

- `green_logistics/problem3_engine.py`
- `problems/problem3.py`
- `tests/test_problem3.py`

默认输入为 `outputs/problem2/default_split/`，默认输出为 `outputs/problem3/`。如用户选择不继承绿色限行，则切换到 `outputs/problem1/`。

### P5：轻量 ALNS 与稳定性辅助指标

在 `green_logistics/operators.py` 或动态专用模块中增加：

- 冻结保护 remove：只移除 `ResidualRequestPool` 中的可调整节点。
- 动态 relatedness remove：同时考虑客户距离、时间窗接近度、同一物理车辆链和绿色政策紧迫性。
- Green-aware regret insertion：绿色客户在 `[480,960)` 优先 E1，或推迟到 16:00 后燃油车。
- 稳定性辅助评分：`vehicle_reassignment_count`、`broken_old_edges_count`、`changed_stop_count`、`changed_vehicle_count`。这些指标用于解释和搜索 tie-break，不写进官方成本。

### P6：高级在途响应

在 P1-P5 验证稳定后，再支持：

- 事件发生在客户间弧上的当前弧锁定和下一节点必达锚点。
- 同一物理车辆的在途剩余序列重排。
- 地址变更代理点的距离映射。
- 多事件滚动推进和短预算重优化。

## 7. 建议正式情景

由于题面没有给官方动态事件数据，建议构造以下 3 个“情景假设”，并在论文中明确标注：

1. **订单取消情景**：在 `t_event = 10:30`，取消一个尚未发车趟次中的服务节点。展示删除后是否能合并趟次、减少固定/能耗/碳排成本。
2. **新增绿区订单情景**：在 `t_event = 13:30`，向一个既有绿区客户增加一笔订单。若在 `[480,960)` 服务，燃油车禁止；优先 E1 或 16:00 后燃油车，并报告政策冲突为 0。
3. **时间窗提前情景**：在 `t_event = 15:00`，将一个尚未服务节点的 latest 提前 30 分钟。展示规则修复和轻量 ALNS 对迟到罚金的改善。

地址变更可作为第四个扩展情景，但必须使用既有客户点作为代理目的地，否则缺少距离矩阵。

## 8. 输出与可视化设计

第三问正式输出建议为：

- `outputs/problem3/recommendation.json`
- `outputs/problem3/scenario_comparison.csv`
- `outputs/problem3/<scenario>/summary.json`
- `outputs/problem3/<scenario>/event_log.csv`
- `outputs/problem3/<scenario>/route_summary.csv`
- `outputs/problem3/<scenario>/stop_schedule.csv`
- `outputs/problem3/<scenario>/route_changes.csv`
- `outputs/problem3/<scenario>/frozen_segments.csv`
- `outputs/problem3/<scenario>/dynamic_diagnosis.csv`
- `outputs/problem3/<scenario>/policy_conflicts.csv`

论文图表建议：

- 情景对比表：基准成本、动态后成本、增量成本、迟到点、最大迟到、政策冲突、调整节点数。
- 调整前后路线变化表：节点是否换车、是否换顺序、是否取消、新增来源。
- 成本变化堆叠图：固定、能源、碳排、时间窗罚金。
- 车辆时间轴/Gantt：冻结段、重优化段、新增服务段分色。
- 动态事件响应流程图：事件输入、状态快照、冻结、残余池、快速修复、轻量 ALNS、验证输出。

## 9. 风险清单与验证计划

风险：

- 题面未给事件数据，所有事件必须是情景假设。
- 绿色限行是否继承存在措辞歧义，主线继承第二问政策时必须写明建模选择。
- 已出发车辆的货物不能跨车转移；新增订单不能插入未回库车辆。
- 地址变更缺少新距离矩阵，只能用既有客户代理。
- `evaluate_route()` 和 `scheduler.py` 当前都不是动态 warm-start 结构，直接复用会产生物理断链。
- 稳定性惩罚不是官方成本，不能包装成题面目标。

验证：

- 覆盖性：动态后每个未取消服务节点恰好服务一次，新增节点按情景定义服务一次。
- 容量：每趟重量和体积不超过车辆上限。
- 物理车辆链：同一 `physical_vehicle_id` 的趟次时间不重叠，warm start 后不能早于车辆可用时间。
- 政策：继承第二问时 `policy_conflict_count == 0`。
- 成本：官方四项成本合计与 summary 一致，稳定性指标单列。
- 时间：时变行驶和能耗仍走分段积分，不用单一速度粗算。
- 输出隔离：第三问只写 `outputs/problem3/` 或 `outputs/problem3_experiments/`。

## 10. 外部方法依据

- Pillac, Gendreau, Gueret and Medaglia (2013), *A review of dynamic vehicle routing problems*, European Journal of Operational Research, DOI `10.1016/j.ejor.2012.08.015`。
- Ichoua, Gendreau and Potvin (2003), *Vehicle dispatching with time-dependent travel times*, European Journal of Operational Research, DOI `10.1016/S0377-2217(02)00147-9`。
- Ropke and Pisinger (2006), *An Adaptive Large Neighborhood Search Heuristic for the Pickup and Delivery Problem with Time Windows*, Transportation Science, DOI `10.1287/trsc.1050.0135`。
- Bent and Van Hentenryck (2004), *Scenario-Based Planning for Partially Dynamic Vehicle Routing with Stochastic Customers*, Operations Research, DOI `10.1287/opre.1040.0124`。

## 11. 后续纪律

- 先写测试，再改核心逻辑。
- 每个动态事件都验证覆盖、容量、物理车辆时间链、政策冲突和成本一致性。
- 若结果不好，必须如实记录，不包装成成功。
- 命令失败、建模错误或关键假设修正，应写入 `.learnings/`、`progress.md` 或相关设计文档。
- 长实验必须写增量账本，避免超时后丢失结论。

本文件最初用于第三问理解、审计与方案设计；截至 2026-04-26，动态响应代码、代表性情景输出和论文写作摘要已经生成。后续若继续改进，应优先做短预算、可复现、逐情景的增量优化，不再启动无账本的长时间全量重跑。
