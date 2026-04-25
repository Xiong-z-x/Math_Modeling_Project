
# Problem 2 改进方案与诊断报告（城市绿色物流配送调度）

## 1. 当前问题诊断

1. **政策可行性 vs 服务质量冲突**  
   - default_split 已消除政策冲突，但服务质量明显退化。
   - 迟到数量从第一问的 4 个增加到 26 个，最大迟到 147.75 分钟。
   - 绿区节点通过延后燃油车或拆分生成虚拟节点来解决，导致整体路线延迟。

2. **数据结构耦合**  
   - service_nodes 同时充当需求原子、一次服务停靠、ALNS 搜索节点。  
   - 第二问引入绿区限行 + EV 替代 + 16:00 后燃油服务时，这种耦合造成混合路线的延迟和结构性迟到。
   - green_e2_adaptive 变体通过预拆分绿区节点，成本和服务质量恶化。

3. **RouteSpec 语义不明确**  
   - 当前 vehicle_type_id 只是偏好而非严格绑定，无法表达 EV 必须服务绿区或燃油车延后 16:00 的约束。

4. **算子与 Scheduler 的局限**  
   - Scheduler 通过延后燃油车消除冲突，但非绿区节点被迫延迟。
   - ALNS 缺少第二问专用算子：policy_conflict_remove、green_fuel_route_split、ev_priority_repair、post_16_fuel_repair。

5. **诊断不足**  
   - 当前 late_stop_diagnosis 没有区分“政策引发迟到”与原有 B/C 类型迟到。
   - 缺少 Type D 分类（政策引发延迟）以指导结构优化。

## 2. 改进思路

1. **增强诊断**  
   - 新增 `diagnose_policy_induced_lateness()` 输出每个迟到停靠的政策延迟信息。
   - 分类至少包括 Type D1–D4：政策引发的延迟、混合路线延迟、EV 容量级联、拆分粒度过大。

2. **数据结构优化**  
   - 引入四层结构：
     1. `DemandAtom`：稳定需求原子
     2. `ServiceVisit`：一次实际停靠，可包含多个 demand atoms
     3. `RouteSpec`：一次 depot-to-depot trip，包括 visit_ids
     4. `ScheduledRoute`：排班后的路线
   - RouteSpec 增加字段：`allowed_vehicle_type_ids`、`policy_service_mode`

3. **算法改进**  
   - ALNS 增加第二问专用算子：
     - `policy_conflict_remove`：移除燃油+绿区冲突节点或混合后缀
     - `green_fuel_route_split`：拆分混合路线以避免延迟
     - `ev_priority_repair`：优先插入 E1/E2
     - `post_16_fuel_repair`：显式构造 16:00 后燃油服务候选
   - Scheduler 保留延后机制作为边界调整，而非主策略。
   - rescue_late_routes 调整优先级：优先解决政策引发的结构性迟到。

4. **目标与指标**  
   - 多目标优化而非仅零政策冲突：
     - policy_conflict_count = 0
     - is_complete = True
     - is_capacity_feasible = True
     - late_stop_count <= 10
     - max_late_min <= 60
     - total_cost 不高于 default_split

5. **创新点**  
   - 政策感知 ALNS：在搜索阶段主动避免冲突，而非仅靠后处理
   - 多粒度数据结构（atom → visit → RouteSpec → ScheduledRoute），增强可解释性
   - Type D 政策引发迟到诊断，为算法优化提供直接反馈
   - EV 优先调度和混合路线拆分，实现成本、碳排、时间窗的平衡

## 3. 可落地的技术路线

1. 数据预处理：按 DemandAtom 粒度初始化 ServiceVisit，标记绿区节点。
2. 生成 RouteSpec：每个 visit 赋予 allowed_vehicle_type_ids 和 policy_service_mode。
3. 初始排班：scheduler 避免直接燃油冲突节点提前服务。
4. ALNS 搜索：使用新增专用算子重组路线和 vehicle 类型。
5. 后处理：rescue_late_routes 修复剩余迟到，优先处理政策引发迟到。
6. 输出与诊断：policy-induced lateness、绿色容量、路线/停靠、成本分解、服务质量指标。
7. 多目标评价：选择总成本最低、迟到最少、零政策冲突方案作为推荐解。

## 4. 结论

- 当前瓶颈是数据结构耦合和算法仅依赖延后处理政策冲突。
- 通过数据结构重构、RouteSpec 语义明确化、ALNS 专用算子和政策感知优化，可在消除政策冲突的同时显著降低迟到和成本。
- Type D 政策引发迟到诊断确保优化结果可解释、符合物理规律。
- 该方案兼顾创新性、前沿性和可落地性，是第二问的最优解候选技术路线。
