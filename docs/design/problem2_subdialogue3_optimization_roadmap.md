# 第二问子对话三优化路线图

日期：2026-04-25

本文记录子对话三对第二问“绿色配送区限行政策下的车辆路径调度”的现状对齐、参考材料审计、瓶颈定位和下一步代码优化路线。它不是新的正式结果，正式推荐仍以 `outputs/problem2/` 和 `docs/results/problem2_green_zone_policy_summary.md` 为准。

## 0. 2026-04-26 最终路线校准

再次验读题面、补充说明、三份第二轮参考文件、当前输出和核心代码后，本轮路线作出一个关键修正：

> `GREEN_E2_ADAPTIVE` 不再作为继续深挖的主线，只保留为“全量绿区细拆为何过重”的负面对照。下一轮主线应是 `DEFAULT_SPLIT` 上的 EV 级联感知搜索，再增加一个受限的 `GREEN_HOTSPOT_PARTIAL` 候选，而不是继续扩大 E2 全量细拆。

理由有三条：

1. 当前正式结果已经证明全量细拆代价过高：`GREEN_E2_ADAPTIVE` 总成本 `57109.67`，比 `DEFAULT_SPLIT` 高 `7220.83`；它不是路程明显变差，而是固定成本和时间窗罚金一起恶化。
2. 12 个迟到点全部是多趟级联，其中主灾点是 E1 物理车链。最坏的 `T0021 / E1-009 / 客户8` fresh route 可零迟到，却被前序非绿区任务压晚。因此主因是 EV 资源错配，不是“所有绿区节点都需要 E2 细拆”。
3. 当前代码已经具备低风险改进入口：`RouteSpec.allowed_vehicle_type_ids`、`policy_service_mode`、`schedule_route_specs()`、`actual_late_remove`、`scheduler_local_search.py` 都能承载小步改造；没有必要先做全仓四层重构。

### 三份参考文件的最终取舍

| 来源 | 最应吸收的洞察 | 必须修正或降级的部分 |
| --- | --- | --- |
| Claude 第二轮 | 成本差主要来自固定成本和罚金；先做系统 seed/remove_count 搜索，成本优先；不要把迟到指标当主目标 | “等到 09:00 顺畅时段再发绿区 EV”只能作为候选发车时间，由真实时变 ETA 和官方成本评分决定，不能硬编码为普适规则 |
| GPT 第二轮 | 当前核心是 EV-cascade；应做 EV 资源保留、阻塞链 destroy/local-search、成本优先近成本精英池 | 阻塞链算子必须从已调度 `Solution` 读取 `physical_vehicle_id` 和前后 trip，不能假装 `RouteSpec` 自带物理车链 |
| Gemini 第二轮 | 全量 E2 拆分过重；应转为局部温和细拆、HIP 启发式隔离、成本优先迟到感知接受 | 它对 F1 被动等待的描述不能直接套用当前正式解；当前最大迟到主要是 E1 被非绿区/低关键任务提前占用 |

### 最终融合框架

下一轮工程实现采用“证据驱动的三层优化栈”：

1. **实验层**：建立参数搜索账本，先不改算法就系统尝试 seed、remove_count、iterations，保留 `49888.84` 正式结果不覆盖。
2. **排班层**：在 `scheduler.py` 中加入 EV opportunity cost。它不是官方成本，而是候选调度评分：当非绿区或非关键任务使用 E1/E2、且可由燃油车合法服务时，对 EV 候选加小额启发式惩罚，把 E1/E2 留给 16:00 前必须由 EV 服务的绿区早窗任务。
3. **搜索层**：在 `operators.py` 与 `scheduler_local_search.py` 中加入 `ev_blocking_chain_remove` 和窄范围 retype/swap，直接拆掉造成 Type B 迟到的前序阻塞 trip，而不是只移除迟到节点本身。

局部拆分只作为第四步补强：新增 `GREEN_HOTSPOT_PARTIAL`，只处理客户 `6, 7, 8, 11` 等证据链明确的绿区热点，且限制新增节点数，避免复刻 `GREEN_E2_ADAPTIVE` 的固定成本爆炸。

### 代码层最终优先级

1. `problems/experiments/problem2_parameter_sweep.py`：新增实验账本，逐个输出 run 结果，不覆盖正式目录。
2. `green_logistics/diagnostics.py`、`green_logistics/output.py`：给 `late_stop_diagnosis.csv` 增加 `ev_cascade_blocked`、`blocking_previous_trip_id`、`blocking_trip_fuel_feasible`、`policy_wait_late`、`direct_late_minutes`、`fresh_route_late_minutes`。
3. `green_logistics/scheduler.py`：扩展 `SchedulingConfig`，加入默认关闭的 `ev_reservation_enabled`、`ev_reservation_penalty`、`green_critical_latest_min=960`；在 `scheduling_selection_score()` 附加 EV opportunity cost。
4. `green_logistics/operators.py`：新增 `ev_blocking_chain_remove`，从 `Solution.routes` 里按 `physical_vehicle_id` 回溯前序 trip，移除可迁移阻塞链。
5. `green_logistics/scheduler_local_search.py`：新增阻塞前序 trip 的 F1/F2/F3 retype 尝试，完整重排后只接受官方总成本改善或近成本服务质量显著改善的搜索候选。
6. `green_logistics/alns.py`：新增可选近成本 elite pool；formal best 仍严格按完整覆盖、容量可行、政策冲突为 0、官方总成本最低选择。
7. `green_logistics/problem_variants.py`：新增 `GREEN_HOTSPOT_PARTIAL`，只做证据驱动的热点局部拆分，并用测试证明总需求守恒、非热点节点不变。

### 不再推荐的方向

- 不继续优化全量 `GREEN_E2_ADAPTIVE`，除非它在新一轮实验中真实低于 `DEFAULT_SPLIT`。
- 不把 09:00 顺畅出发写死为绿区 EV 规则；它只能作为发车候选，接受真实成本评价。
- 不用 exact MILP/branch-price 重写全问题。若需要 exact 方法，只可作为小规模局部重排验证器，而不是替代当前 ALNS 主线。
- 不做完整 `DemandAtom -> ServiceVisit -> RouteSpec -> ScheduledRoute` 大重构。若热点局部拆分需要更清晰表达，只做最小 `ServiceVisit` MVP。

### 2026-04-26 执行结果

已完成本路线图的首轮实现与验证：

- `late_stop_diagnosis.csv` 增加 EV 级联、前序阻塞 trip、燃油可接管和 policy-wait 字段。
- `SchedulingConfig` 增加默认关闭的 EV reservation scoring；正式采用 `--use-ev-reservation --ev-reservation-penalty 250`。
- `operators.py` 增加 `ev_blocking_chain_remove`，用于实验性 policy-operator 组合。
- `problem_variants.py` 增加 `GREEN_HOTSPOT_PARTIAL`，正式输出现在比较三条候选线。
- `problems/experiments/problem2_parameter_sweep.py` 增加增量实验账本。

新正式结果已晋升到 `outputs/problem2/`：

- 推荐：`DEFAULT_SPLIT`
- 总成本：`49239.78`
- 政策冲突：`0`
- 完整覆盖/容量可行：`True` / `True`
- 物理车辆：`E1:10, F1:35`
- 迟到点/最大迟到：`12` / `129.44 min`
- 旧结果 `49888.84` 备份：`outputs/problem2_previous_49888_20260425/`

重要负面结果也已记录：

- EV reservation penalty `500` 把最大迟到压到 `21.21 min`，但总成本 `50010.53`，不推荐。
- policy operators + EV reservation penalty `500` 只剩 `2` 个迟到点、最大迟到 `5.93 min`，但总成本 `50770.72`，不推荐。
- `GREEN_HOTSPOT_PARTIAL` 成本 `52312.11`，目前只保留为对照。

## 1. 不变的题意边界

- 第二问目标仍是题面官方总成本最小：固定成本、能耗成本、碳排放成本、软时间窗罚金。
- 绿色限行是硬约束：燃油车在 `[480, 960)` 内到达绿区客户不可行；16:00 准点到达视为合法。
- 时间窗是软约束，迟到只能通过罚金进入官方目标，不应被替换成硬约束或主目标。
- 绿色客户按客户坐标到 `(0, 0)` 的欧氏距离判断，不按配送中心 `(20, 20)`。
- 没有道路几何，不能声称检测了车辆路径穿越绿区。
- 距离矩阵索引用原始 `customer_id`，算法内部虚拟节点用 `node_id`，两者不能混用。
- 行驶时间必须保留时变分段积分和 FIFO 思路，不能改回“出发速度乘全程距离”的粗算。
- 固定成本按被启用的物理车辆计，不按 depot-to-depot 行程计。
- 题面没有 24:00 硬返库；跨午夜只能作为诊断或情景分析。

## 2. 当前正式结果

正式命令：

```powershell
python problems/problem2.py --iterations 40 --remove-count 16 --seed 20260427 --output-dir outputs/problem2
```

推荐方案是 `DEFAULT_SPLIT`：

- 总成本：`49888.84`
- 政策冲突：`0`
- 完整覆盖：`True`
- 容量可行：`True`
- 物理车辆：`E1:10, E2:1, F1:35`
- 迟到点：`12`
- 最大迟到：`124.92 min`
- 午夜后返库：`0`

对照方案 `GREEN_E2_ADAPTIVE` 当前总成本 `57109.67`，虽然零政策冲突，但固定成本和迟到罚金显著更高，不能按官方目标推荐。

## 3. 最大迟到定位

对 `outputs/problem2/default_split/stop_schedule.csv` 和 `late_stop_diagnosis.csv` 的复核结论：

- 12 个迟到点全部被现有诊断标为 `Type B multi-trip cascade`。
- 最大迟到发生在 `T0021`：
  - 物理车：`E1-009`
  - 客户：`8`
  - 服务节点：`13`
  - 到达：`831.92`
  - 时间窗：`649-707`
  - 迟到：`124.92 min`
  - 是否绿区：`True`
- 该节点从仓库 08:00 直达可在时间窗内到达；现有 `late_stop_diagnosis.csv` 中的 fresh route 也显示可零迟到。因此它不是原始时间窗/距离导致的直达不可行，也不是单条路线内部排序问题。
- `T0021` 前序同车任务是 `T0009`，客户 `42`，非绿区，且从载重/体积看可由 `F1` 承担。该任务占用了 `E1-009` 直到 `796.09`，导致后续客户 8 迟到。
- 类似模式也出现在 `E1-005`、`E1-010`、`E1-002`、`E1-003` 等车辆链上：一批非绿区或低政策关键性任务先占用 E1，随后早时间窗绿区任务被迫排队。

核心判断：当前瓶颈不是燃油车违规冲突本身，而是政策诱发的 EV 稀缺资源级联。第一版 `--use-policy-operators` 主要修复燃油车绿区冲突和 16:00 后燃油服务，方向过窄，解释了它为何可能抬高成本而没有解决最大迟到。

## 4. 三份新增参考材料审计

### 4.1 Claude 第二轮建议

可取之处：

- 把注意力放在总成本差额、额外车辆和罚金上，符合官方目标。
- 强调先做多 seed / remove-count 搜索，避免过早大改架构。
- 对全量绿区 E2 细拆保持谨慎，和当前 `GREEN_E2_ADAPTIVE` 成本偏高一致。

局限：

- “等待到更顺畅时段再发车”的建议需要逐路线验证。客户 6、7、8、11 等绿区早窗任务已经被迟到主导，不能把延后出发当作通用规则。
- 没有充分解释 E1 被非绿区任务抢占后的物理车辆复用级联。

### 4.2 GPT 第二轮建议

可取之处：

- 准确抓住 `Type B multi-trip cascade` 和 `EV-cascade` 是当前主瓶颈。
- 建议加入 EV 资源保留、阻塞链 destroy/local-search、热点局部拆分和成本优先辅助精英档案，和现有 `RouteSpec -> schedule_route_specs -> Solution` 架构可衔接。
- 明确区分搜索辅助评分和正式推荐标准，避免把服务质量指标误当成目标函数。

局限：

- 阻塞链算子不能只看 `RouteSpec`，必须从已调度 `Solution` 中读取同一物理车的前后任务；工程实现要小心匹配 `node_id` 集合和原始 `RouteSpec`。
- 近成本精英档案只能作为重启/候选池机制，不能改变最终 `total_cost` 排序。

### 4.3 Gemini 第二轮建议

可取之处：

- 指出全量 E2 拆分造成固定成本膨胀，建议只处理高冲突热点绿区客户，这是比 `GREEN_E2_ADAPTIVE` 更温和的路线。
- 强调在低改动条件下加入政策关键性/稀缺资源意识，而不是立即重写完整多层架构。
- 建议保留可解释性：哪些客户被拆、为什么拆、成本是否下降，都要能从输出表追溯。

局限：

- 它对“燃油车等到 16:00 后服务”的强调不足以解释当前最大迟到；现有最严重迟到主要在 E1 车辆链内部发生。
- 若直接把某些启发式惩罚塞进官方成本，会偏题；只能放在 scheduler/ALNS 搜索评分或候选生成中。

## 5. 方法边界的外部校准

联网核对后的方法边界：

- ALNS 作为 VRPTW/PDPTW 类问题的主启发式是合理路线，可继续围绕 destroy/repair 和自适应权重做局部增强。
- 时变 VRP 必须保持 FIFO 和分段行驶时间，不能用静态速度近似替代。
- 绿色/污染路由研究通常把排放、速度、时间窗和路径构造耦合处理；本项目当前没有道路几何，因此只能在服务节点到达、车型选择和出发时间上建模绿色限行。
- 多趟 VRPTW 的难点在物理车复用，当前 E1 级联正是多趟排班层的问题，单纯改客户插入顺序不够。

参考入口：

- Ropke and Pisinger, ALNS for pickup and delivery with time windows: https://pubsonline.informs.org/doi/10.1287/trsc.1050.0135
- Pisinger and Ropke, general ALNS heuristic for vehicle routing: https://doi.org/10.1016/j.cor.2005.09.012
- Ichoua, Gendreau and Potvin, time-dependent VRP with time-dependent travel speeds: https://doi.org/10.1016/S0191-2615(02)00017-5
- Demir, Bektas and Laporte, pollution-routing problem with ALNS: https://doi.org/10.1016/j.ejor.2012.06.044

## 6. 终极落地路线

### P0：保护正式结果并建立实验账本

目标：任何搜索或新变体都不能覆盖已验证的 `49888.84` 正式结果。

动作：

- 新增或使用独立输出目录，例如 `outputs/problem2_experiments/...`。
- 每次实验记录 seed、remove_count、iterations、是否启用政策算子、变体、总成本、政策冲突、车辆使用、迟到点、最大迟到。
- 长实验分批运行，避免一个长命令超时后丢失中间结果。

涉及模块：

- 可新增 `problems/experiments/problem2_parameter_sweep.py`
- 可更新 `outputs/README.md`

验收：

- 正式 `outputs/problem2/recommendation.json` 不被覆盖。
- 实验 CSV 能复现实验排序。

### P1：增强迟到诊断，先把 EV 级联自动标出来

目标：让 `late_stop_diagnosis.csv` 区分普通多趟级联、EV 资源阻塞、政策诱发迟到和直达不可行。

建议新增字段：

- `policy_induced_late`
- `ev_cascade_blocked`
- `same_vehicle_previous_route_id`
- `previous_route_green_stop_count`
- `previous_route_fuel_feasible`
- `previous_route_arrive_before_restricted_end`
- `direct_arrival_late_minutes`
- `fresh_route_late_minutes`

判断逻辑：

- 若迟到点是绿区、当前车型是 EV、直达或 fresh route 可不迟到，但同物理车前序任务导致发车晚，则标 `ev_cascade_blocked=True`。
- 若前序任务无绿区客户，且载重体积可由 F1/F2/F3 服务，并且不会引入政策冲突，则标为可迁移阻塞任务。
- 若燃油车因绿区限行被推迟到 16:00 后服务而迟到，则标 `policy_wait_late=True`。

涉及模块：

- `green_logistics/diagnostics.py`
- `green_logistics/output.py`
- `tests/test_diagnostics.py` 或 `tests/test_output.py`

验收：

- 当前最大迟到 `T0021` 被自动识别为 EV 级联阻塞。
- 诊断仍使用 `node_id` 查服务节点、用 `customer_id` 查距离，不混用。

### P2：轻量参数搜索，先吃掉免费改进

目标：在不改核心架构前，寻找低于 `49888.84` 的零冲突方案。

建议第一批网格：

- `remove_count`: `8, 12, 16, 20`
- `seed`: `20260427, 20260430, 20260431, 20260432, 20260433, 20260434`
- `iterations`: 先 `40`，只对前 3 名再跑 `80` 或 `120`
- 默认不启用 `--use-policy-operators`

验收：

- 以官方总成本排序，政策冲突必须为 `0`。
- 若找到更低成本，再用正式验证清单复核完整覆盖、容量、物理车数量、成本分项和输出一致性。

### P3：调度器加入 EV 稀缺资源保留评分

目标：防止早期非绿区、F1 可服务任务抢占 E1，造成后续绿区早窗任务迟到。

低风险实现：

- 在 `SchedulingConfig` 增加可关闭参数，例如 `ev_reservation_enabled`、`ev_reservation_penalty`。
- 在 `schedule_route_specs()` 的候选评分中，如果一个候选路线：
  - 使用 E1/E2；
  - 没有绿区服务节点，或绿区服务不在限制期内必须由 EV 完成；
  - 载重/体积可由可用燃油车型承担；
  - 使用燃油车型不会产生政策冲突；
  则给该候选一个搜索评分惩罚，而不是改变官方成本。
- 对有早时间窗绿区节点的 E1/E2 路线，不加该惩罚。

涉及模块：

- `green_logistics/scheduler.py`
- `green_logistics/problem2_engine.py`
- `tests/test_scheduler.py`
- `tests/test_problem2_engine.py`

验收：

- 构造测试中，非绿区 F1 可服务任务优先分给 F1，绿区早窗任务保留 E1。
- 正式推荐仍由 `Problem2Engine` 按总成本选择，不按惩罚后的搜索分选择。

### P4：阻塞链 destroy 和 scheduler local search

目标：直接针对 `T0021` 这类“前序任务占用 E1”的结构做邻域搜索。

算子路线：

- 在 `operators.py` 增加 `ev_blocking_chain_remove`：
  - 找出当前 `Solution` 中迟到最大的绿区 EV 停靠；
  - 回溯同一物理车上它之前的 1-2 条路线；
  - 若前序路线非绿区或可由燃油车服务，则移除这些前序路线的节点和迟到节点附近节点，交给 repair 重插。
- 在 `scheduler_local_search.py` 增加局部换车尝试：
  - 将阻塞前序 E1/E2 路线尝试改为 F1；
  - 重排对应物理车链；
  - 只在官方总成本改善，或总成本基本持平且迟到显著改善时作为搜索候选保留。

涉及模块：

- `green_logistics/operators.py`
- `green_logistics/scheduler_local_search.py`
- `green_logistics/alns.py`
- `tests/test_alns_smoke.py`
- `tests/test_scheduler_local_search.py`

技术障碍和变通：

- `RouteSpec` 本身不知道物理车前后链，必须从 `Solution.routes` 读取 `physical_vehicle_id` 和 route order。
- 当前 repair 的局部成本不完全等价于最终 schedule 成本，因此算子只负责打开结构，最终接受仍交给完整排班和正式评价。

### P5：成本优先的近成本精英池

目标：改善同成本或近成本区域里的服务质量，但不改变官方目标。

建议：

- 在 `ALNSConfig` 中加入可选精英池，保存政策可行、覆盖完整、容量可行的候选。
- 主 best 仍由 `_is_better_formal_solution()` 决定。
- 精英池只用于周期性重启或 tie-break，例如在 `total_cost` 差距极小的候选中优先保留总迟到更低者。

涉及模块：

- `green_logistics/alns.py`
- `green_logistics/metrics.py`
- `tests/test_alns_smoke.py`

验收：

- 单元测试证明更高官方总成本不会覆盖更低官方总成本的 formal best。

### P6：热点局部绿区拆分，而非全量 E2 拆分

目标：吸收 `GREEN_E2_ADAPTIVE` 的洞察，但避免 148 到 166 节点的全量膨胀。

候选策略：

- 新增 `GREEN_HOTSPOT_PARTIAL` 变体。
- 第一批热点只考虑当前迟到和政策冲突高度相关的绿区客户，例如 `6, 7, 8, 11`，必要时再评估 `3, 12`。
- 对热点客户只拆出少量 E2 可服务子节点，剩余需求保留 E1 可服务块，避免固定成本和路线数暴涨。
- 增加拆分上限，例如总服务节点只允许比 `DEFAULT_SPLIT` 多 `4-8` 个。

涉及模块：

- `green_logistics/problem_variants.py`
- `green_logistics/problem2_engine.py`
- `tests/test_problem_variants.py`
- `docs/results/problem2_green_zone_policy_summary.md`

验收：

- 变体服务节点数量、绿区节点数量和总需求守恒可测。
- 与 `DEFAULT_SPLIT`、`GREEN_E2_ADAPTIVE` 同表比较，并按官方总成本推荐。

### P7：仅在必要时做更大架构升级

如果 P1-P6 后仍无法稳定降低成本，再考虑最小化的 `DemandAtom / ServiceVisit` 抽象或两阶段 trip-pool/scheduler 架构。当前不建议一上来重写，因为：

- 现有虚拟节点已经能表达可分需求；
- 当前瓶颈主要是排班层 EV 稀缺分配，不是数据层完全不可表达；
- 大改会增加 `node_id/customer_id` 混用、输出不一致和测试失效风险。

## 7. 明确不推荐的路线

- 不把政策违规作为第五项官方成本。
- 不把最大迟到改成主目标。
- 不把 24:00 返库改成正式硬约束。
- 不声称有道路穿越绿区检测。
- 不继续扩大 `GREEN_E2_ADAPTIVE` 全量拆分，除非它在实验中真实降低官方总成本。
- 不盲目启用当前 `--use-policy-operators`，应先改成针对 EV 级联的算子。

## 8. 推荐实施顺序

1. 备份正式结果并建立参数搜索账本。
2. 增强 `late_stop_diagnosis.csv`，自动识别 EV 级联和阻塞前序任务。
3. 跑轻量多 seed/remove-count 搜索，先找无代码风险的低成本候选。
4. 加入调度器 EV 保留评分，做小规模 smoke 和正式候选对比。
5. 实现 `ev_blocking_chain_remove` 和局部换车搜索。
6. 尝试 `GREEN_HOTSPOT_PARTIAL` 局部拆分变体。
7. 只有上述路线不够时，再评估更深层数据/排班架构升级。

这一路线的核心原则是：先承认当前零冲突方案已经可行，再用诊断证据精确打击 E1/E2 稀缺资源错配；所有改动都服务于降低官方总成本，服务质量只做解释、辅助搜索和近成本 tie-break。

## 9. 2026-04-26 收官状态

本路线图的第一轮执行已经完成，正式第二问结果晋升为 EV reservation p250 方案：

- 正式输出：`outputs/problem2/`
- 正式命令：`python problems/problem2.py --iterations 40 --remove-count 16 --seed 20260427 --use-ev-reservation --ev-reservation-penalty 250 --output-dir outputs/problem2`
- 推荐方案：`DEFAULT_SPLIT`
- 总成本：`49239.78`
- 政策冲突：`0`
- 论文写作母稿：`docs/results/problem2_modeling_and_solution_closeout.md`

`policy operators + EV reservation p500` 保留为服务质量灵敏度方案，结果为总成本 `50770.72`、迟到点 `2`、最大迟到 `5.93 min`。它不替代正式答案，因为第二问仍以官方总成本最小为目标。

第二问在当前建模轮次暂时关闭，后续应转入第三问，并复用本轮沉淀的 `Problem2Engine`、scheduler、policy evaluator、diagnostics 和实验账本接口。
