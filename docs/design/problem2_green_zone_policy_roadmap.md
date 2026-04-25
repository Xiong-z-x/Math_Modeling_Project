# 第二问绿色配送区限行技术路线综合方案

## 1. 题意与现状基准

第二问在第一问基础上加入一条硬政策：`8:00-16:00` 期间燃油车不得进入绿色配送区。绿色配送区按补充说明由客户坐标相对城市中心 `(0, 0)` 的欧氏距离判定，半径为 `10 km`；配送中心坐标为 `(20, 20)`，不能作为绿区圆心。第二问仍以题面总配送成本最小为目标：

```text
fixed_cost + energy_cost + carbon_cost + soft_time_window_penalty
```

其中时间窗继续是软约束，绿色限行是硬约束。当前附件没有道路折线或 GIS 轨迹，无法判断车辆在两点之间是否穿越绿区。因此正式代码应将限行落地为：燃油车不得在限行时段到达并服务绿区客户。若后续要研究路径穿越，只能作为额外情景分析，不能作为主模型硬约束。

第一问正式结果为 `48644.68` 元、`116` 趟、物理车辆 `E1:10, F1:33`。第一问解在第二问政策下有 `12` 个燃油车限行冲突停靠，集中在绿区客户 `3, 6, 7, 8, 11, 12`。绿区共有 `19` 个虚拟节点，总需求 `35970.65 kg / 103.96 m3`；当前大颗粒拆分下仅 `4` 个绿区节点适合 E2，`15` 个节点需要 E1 级容量。若只对绿区客户按 E2 容量 `(1250 kg, 8.5 m3)` 重新拆分，绿区服务节点精确增至 `37` 个，整体服务节点由 `148` 增至 `166` 个，可显著释放 E2 运力。因此 `GREEN_E2_ADAPTIVE` 在本路线中提升为第二问正式候选主线，而不是附录式可选情景。

## 2. 三份参考方案审计

### Claude 方案

可取之处：

- 准确抓住题意边界：不能添加充电桩、续航、22:00 硬返库等题外约束。
- 明确第二问目标函数不变，限行作为硬约束。
- 强调问题二需要独立 `problems/problem2.py`，并输出与问题一的成本、车辆结构、碳排对比。
- 提出的 `GreenZoneViolationDestroy`、EV 优先插入、16:00 后燃油兜底，和现有 ALNS 架构匹配。

局限：

- 部分伪代码假设 `RouteSpec` 有 `preferred_depart` 或 route 可原地增删节点，但当前代码中的 `RouteSpec` 只有 `vehicle_type_id` 与 `service_node_ids`，算子必须返回新的 spec 元组，不能直接修改 `Route`。
- 说“不需要修改 scheduler.py”偏乐观。燃油车 16:00 后兜底需要在 scheduler 的发车候选或局部修复中体现，否则 RouteSpec 无法表达“这趟必须晚到绿区”。
- “绿区内碳排放为 0”不严谨。新能源车仍有电力碳排因子，题面给出 `0.501 kg/kWh`，只能说局部尾气排放为 0，不能说模型碳排为 0。

### Gemini 方案

可取之处：

- 一针见血指出当前按 `(3000 kg, 15 m3)` 拆分，会让大量绿区节点超过 E2 能力，导致 15 辆 E2 难以参与绿区服务。
- “Wait-or-Switch” 思路符合题意：绿区节点优先换 EV，必要时燃油车延后到 16:00 后，以时间窗罚金换政策合规。
- 强调绿区专用破坏算子和 EV 优先修复，方向正确。

局限与更新判断：

- 直接覆盖默认数据层不合适，但“只对绿区按 E2 重新拆分”可以作为第二问的正式候选主线，因为虚拟服务节点本来就是求解器为容量可行性引入的建模颗粒度，不是题目固定附件。只要保留总需求、客户坐标、时间窗和距离矩阵不变，它可以解释为政策感知的需求批次划分。
- 绿区细拆会把绿区节点从 `19` 增加到约 `37`，增加停靠数、服务时间和固定调度难度，不一定降低总成本。
- “政策惩罚写入 metrics.py”不合适。正式目标函数不能加入题外成本；可在搜索 score 中使用大罚项，但最终输出必须按官方总成本且政策冲突为 0。

### GPT 方案

可取之处：

- 最贴近当前代码实际：承认 Problem 2 还只有接口、诊断和预检，没有真正求解器。
- 推荐“低改动可插拔修正先交付，trip-based 两阶段重构再拔高”，投入产出比理性。
- 准确指出 `RouteSpec -> scheduler -> Solution` 架构是当前最稳入口，`scheduler_local_search.py` 是做 retime/reassign 的自然位置。
- 强调 17:00 后速度延拓和路径穿越绿区均是模型边界，必须论文说明。

局限：

- 对“是否需要改数据拆分”较保守，没有充分利用 Gemini 对 E2 运力释放的洞察。
- 若只做低改动局部修复，可能得到合规但非高质量的第二问解，尤其是重绿区客户早时间窗高度集中时。

## 3. 融合后的最终路线

推荐升级为 `Problem2Engine` 双候选路线：第二问独立求解，不硬塞进第一问脚本；同时运行 `DEFAULT_SPLIT` 和 `GREEN_E2_ADAPTIVE` 两条正式候选主线，在政策合规、覆盖完整、容量可行、车辆数合法的前提下，按官方总成本选择推荐方案。

两条候选如下：

- `DEFAULT_SPLIT`：沿用第一问 148 个服务节点，在同一服务颗粒度下加入绿色限行硬约束。这条线用于最干净地衡量“只加入政策约束”的影响。
- `GREEN_E2_ADAPTIVE`：非绿区客户保持第一问拆分；绿区客户按 E2 容量重新拆分，使 E2 可参与限行期绿区配送。这条线是第二问的正式候选主线，不再只是附录情景。如果它胜出，论文中将其表述为“绿色限行政策下的需求批次重构与新能源小车协同调度”。

理由：

1. 符合题意：目标函数不变，绿色限行为硬约束。
2. 符合题目开放性：第二问要求重新规划路径，没有要求使用第一问完全相同的服务节点拆分。
3. 符合代码现状：现有 `Route`, `Solution`, `RouteSpec`, `schedule_route_specs`, `diagnostics` 可复用；但应新增独立 `Problem2Engine` 和数据变体构造层。
4. 符合物理规律：绿区冲突处理发生在真实到达时间和物理车辆多趟排班之后，不用静态估计替代时变 ETA。
5. 可解释性强：政策影响可拆为 EV 替换、16:00 后延后服务、绿区批次重构、车辆结构变化和碳排变化。

解释第二问相对第一问的成本变化时要保持谨慎：在同一服务节点口径、同一成本模型且求到全局最优的理论条件下，第二问增加硬约束后最优值不应低于第一问最优值。但 `GREEN_E2_ADAPTIVE` 改变了服务批次颗粒度，若它比第一问正式基线更低，不能简单说政策降低成本，而应解释为“政策触发了更细粒度新能源协同配送方案”。为公平分解效果，建议额外运行一个 `problem1_green_e2_adaptive_baseline`，即在无政策条件下使用同样的绿区细拆口径，区分“拆分颗粒度收益”和“限行政策代价”。

## 4. 工程优先级

### P0：Problem2Engine 与数据变体红线

- 新增 `green_logistics/problem_variants.py`：
  - 定义 `SplitMode.DEFAULT` 与 `SplitMode.GREEN_E2_ADAPTIVE`。
  - 提供 `load_problem_variant(data_dir, split_mode)`。
  - `DEFAULT` 必须与当前 `load_problem_data` 输出一致。
  - `GREEN_E2_ADAPTIVE` 只改变绿区客户拆分数；客户总需求、坐标、时间窗、距离矩阵和绿区客户集合必须不变。
  - 生成 `variant_name` 与 `service_node` 映射摘要，便于输出解释。
- 新增 `tests/test_problem_variants.py`：
  - 验证 default 仍为 `148` 个服务节点。
  - 验证 green adaptive 总重量/总体积与 default 完全一致。
  - 验证 green adaptive 中所有绿区节点均可被 E2 或 E1 单趟服务。
  - 验证非绿区客户拆分数不变。

### P1：固定政策边界与测试红线

- 完善 `GreenZonePolicyEvaluator`：
  - 使用 `vehicle.energy_type == "fuel"`，不要只靠字符串前缀。
  - 限行区间建议实现为 `[480, 960)`；`16:00` 到达视为限行结束后。
  - 提供 `route_violation_count`、`violating_stops`、`solution_violation_count`。
- 新增 `tests/test_problem2_policy.py`：
  - 燃油车绿区 480 分钟违规。
  - 燃油车绿区 959.9 分钟违规。
  - 燃油车绿区 960 分钟不违规。
  - EV 任何时刻服务绿区不违规。
  - 非绿区燃油停靠不违规。

### P2：最小可交付 Problem2Engine

- 新增 `green_logistics/problem2_engine.py`：
  - 输入 `ProblemData`、`split_mode`、`PolicyEvaluator`、ALNS 参数和 scheduler 参数。
  - 输出 `Problem2RunResult`，包含 variant、best_solution、policy_conflict_count、cost_breakdown、quality_metrics。
  - 负责运行 initial specs、policy-aware ALNS、scheduler conflict rescue 和最终合规检查。
- 新增 `problems/problem2.py`：
  - 复用 `load_problem_data`、`construct_initial_route_specs`、`run_alns`、`write_solution_outputs`。
  - 默认运行 `DEFAULT_SPLIT` 和 `GREEN_E2_ADAPTIVE` 两个 variant。
  - 输出到 `outputs/problem2/default_split/` 与 `outputs/problem2/green_e2_adaptive/`。
  - 在 `outputs/problem2/recommendation.json` 中记录按官方总成本选择的推荐方案。
  - 最终 assert：推荐方案完整覆盖、容量可行、政策冲突数为 0。
  - 读取第一问基线摘要，用于生成对比表。
- 修改 `green_logistics/alns.py`：
  - 接收可选 `policy_evaluator`。
  - 候选解若政策冲突不为 0，可在搜索 score 中加大罚项，但不能成为最终 best。
  - `_is_better_formal_solution` 对 Problem 2 应先比较可行性：完整、容量、政策均可行，再比较官方总成本。
- 修改 `green_logistics/diagnostics.py`：
  - 新增 Problem 2 合规输出，正式结果必须 `policy_conflict_count == 0`。

### P3：政策感知算子与排班局部修复

- 修改 `green_logistics/operators.py`：
  - 新增 `policy_conflict_remove`：从当前 `Solution` 中移除燃油限行冲突节点。
  - 新增 `green_related_remove`：移除同客户拆分绿区节点及同路线邻近节点。
  - 新增 `ev_priority_insert`：绿区节点优先尝试插入 E1/E2 可行路线，新开 EV trip 次之，最后留给 scheduler 16:00 后燃油兜底。
- 修改 `green_logistics/scheduler.py`：
  - `choose_departure_min` 增加 policy-aware 候选发车时刻。
  - 对触达绿区的燃油 trip，枚举能使第一个绿区停靠到达不早于 960 的发车候选。
  - 保持时变 ETA 分段积分，不允许用“出发速度 × 距离”近似。
- 修改 `green_logistics/scheduler_local_search.py`：
  - 新增 `rescue_policy_conflicts`：尝试 F1->E1/E2 retype、split、delay-to-16:00，选择官方成本最小且合规的替代 specs。

### P4：公平对比与创新展示

- 新增 `problems/problem1_variant_baseline.py` 或在 `problems/problem2.py` 中提供 `--run-p1-adaptive-baseline`：
  - 使用 `GREEN_E2_ADAPTIVE` 服务节点口径。
  - 不启用绿区限行政策。
  - 输出 `outputs/problem1_green_e2_adaptive_baseline/`。
  - 用于拆分“细粒度需求重构收益”和“政策硬约束代价”。
- 修改 `green_logistics/output.py`：
  - 新增 `write_problem2_comparison_outputs`。
  - 输出 `problem1_vs_problem2.csv`、`variant_comparison.csv`、`policy_effect_summary.md`。
  - 若存在自适应第一问基线，输出三方分解：
    - 原第一问默认拆分；
    - 自适应拆分无政策；
    - 自适应拆分有政策。

- 新增 `problems/experiments/problem2_scenarios.py`：
  - 多 seed 重复求解。
  - 限行时段敏感性：`8-13`, `8-16`, `8-17`, 全天等。
  - EV 规模敏感性：E1/E2 数量变化。
- 新增 `docs/results/problem2_green_zone_policy_summary.md`：
  - 题意、模型、算法、结果、政策影响对比。

## 5. 不建议立即做的事

- 不建议直接覆盖 `load_problem_data` 的默认行为。绿区 E2 细拆应通过 `problem_variants.py` 显式选择，保证第一问和历史输出可复现。
- 不建议把政策惩罚加入官方 `total_cost`。政策违规应是硬不可行，不是题面成本项。
- 不建议直接重写成精确 MILP/branch-price。148 个节点、时变 ETA、能耗积分、多趟复用下，开发风险过高。
- 不建议把道路穿越绿区做成硬约束。当前数据没有道路几何，不能自造约束。

## 6. 参考依据

- Pisinger and Ropke 的 ALNS 体系支持以 destroy/repair 扩展复杂 VRP 变体。
- Ichoua, Gendreau and Potvin 的 time-dependent VRP 工作支持 FIFO 与时变速度建模。
- Demir, Bektas and Laporte 的 pollution-routing ALNS 支持路径、速度、能耗与排放联合优化。
- 多趟 time-dependent VRPTW 文献支持将 trip 构造与物理车辆排班分层处理。
- PyVRP 与 OR-Tools 可作为外部基线参考，但不能直接替代本项目的 Jensen 能耗、绿区政策和自定义多趟排班逻辑。

本文件只确定技术路线和实现优先级，尚未修改求解代码或重新生成 Problem 2 结果。

## 7. 2026-04-26 路线校准说明

本文件是第二问第一轮路线设计，仍可用于理解 `Problem2Engine`、硬政策门控和双候选输出的来龙去脉。但经过正式输出和三份第二轮参考材料复核后，继续优化路线已更新：

- `GREEN_E2_ADAPTIVE` 已被正式结果证明成本过高：当前总成本 `57109.67`，明显高于 `DEFAULT_SPLIT` 的 `49888.84`。因此它保留为对照，不再作为下一轮重点深挖主线。
- 下一轮主线不是全量绿区 E2 细拆，而是在 `DEFAULT_SPLIT` 上修复 EV 多趟复用级联：增强迟到诊断、参数搜索、EV 资源保留评分、阻塞链算子和调度层局部换车。
- 若需要新的服务节点变体，应采用受限的 `GREEN_HOTSPOT_PARTIAL`：只对客户 `6, 7, 8, 11` 等证据明确的绿区早窗热点做局部温和拆分，并限制新增节点数量。
- 最终路线以 `docs/design/problem2_subdialogue3_optimization_roadmap.md` 的 2026-04-26 校准版为准。

这不是推翻本文件，而是基于实测结果对候选主线作出的收敛：第一轮路线负责把第二问跑通并零冲突，下一轮路线负责在不改变题面目标的前提下继续降低官方总成本。

## 8. 2026-04-26 执行后正式结果更新

校准路线的首轮实现已经完成。正式 `outputs/problem2/` 已更新为：

```powershell
python problems/problem2.py --iterations 40 --remove-count 16 --seed 20260427 --use-ev-reservation --ev-reservation-penalty 250 --output-dir outputs/problem2
```

推荐结果仍为 `DEFAULT_SPLIT`，但总成本从 `49888.84` 降至 `49239.78`，政策冲突保持 `0`。本次实现新增了 EV reservation 搜索评分、EV 级联诊断、阻塞链实验算子和 `GREEN_HOTSPOT_PARTIAL` 对照变体。

`GREEN_E2_ADAPTIVE` 和 `GREEN_HOTSPOT_PARTIAL` 在新正式对比中仍不推荐：

- `GREEN_E2_ADAPTIVE`: `57504.49`
- `GREEN_HOTSPOT_PARTIAL`: `52312.11`

旧正式结果已保存到 `outputs/problem2_previous_49888_20260425/`。

## 9. 2026-04-26 收官说明

第二问当前建模轮次已经收官。完整论文写作母稿为：

`docs/results/problem2_modeling_and_solution_closeout.md`

该文档汇总了题意边界、模型假设、符号、成本公式、约束、求解算法、正式结果、服务质量灵敏度方案、可视化建议和第三问接口。正式输出仍为 `outputs/problem2/`；已并入正式结果的中间候选目录已清理，旧 `49888.84` 结果和 `policy operators + EV reservation p500` 服务质量对照均已保留并注明用途。
