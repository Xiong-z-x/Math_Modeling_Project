# 子对话三：第二问进一步优化交接报告与初始化提示词

## 一页式项目进展报告

当前项目位于 `c:\Math_Modeling_Project`。第一问已经完成，正式结果在
`outputs/problem1/`。第二问已经完成第一版可运行求解器和正式结果，正式
结果在 `outputs/problem2/`。

第二问题意边界已经重新核对：

- 第二问是在第一问基础上加入绿色配送区限行政策。
- 绿色配送区是以市中心 `(0,0)` 为圆心、半径 `10 km` 的圆形区域。
- 配送中心坐标是 `(20,20)`，不是绿区圆心。
- `8:00-16:00` 期间燃油车不得进入绿色配送区。
- 目前附件没有道路几何，不能判断两点之间是否穿越绿区；正式代码只检测
  “燃油车在限行时段服务绿区客户”。
- 第二问目标仍是题面官方总成本最小：
  `fixed_cost + energy_cost + carbon_cost + soft_time_window_penalty`。
- 时间窗是软约束，绿色限行是硬约束。
- 题面没有 24:00 硬返库要求，午夜返库只能作为诊断或情景分析，不能作为
  正式可行性筛选标准。

当前技术路线：

- 新增独立 `Problem2Engine`，不把第二问硬塞进 `problems/problem1.py`。
- 同时求解两条正式候选主线：
  - `DEFAULT_SPLIT`：沿用第一问 148 个服务节点；
  - `GREEN_E2_ADAPTIVE`：非绿区保持默认拆分，绿区按 E2 容量细拆，形成
    166 个服务节点、37 个绿区服务节点。
- 推荐规则：完整覆盖、容量可行、政策冲突为 `0`，然后按官方总成本最低
  选择。
- `GREEN_E2_ADAPTIVE` 是正式候选，不是附录情景；但当前结果成本更高，故
  不推荐。

当前正式第二问命令：

```powershell
python problems/problem2.py --iterations 40 --remove-count 16 --seed 20260427 --output-dir outputs/problem2
```

当前正式推荐结果：

| 指标 | 值 |
| --- | ---: |
| 推荐 variant | `DEFAULT_SPLIT` |
| 总成本 | `49888.84` |
| 固定成本 | `18400.00` |
| 能耗成本 | `24688.13` |
| 碳排成本 | `5327.28` |
| 时间窗惩罚 | `1473.43` |
| 总距离 | `13377.44 km` |
| 碳排放 | `8195.81 kg` |
| 行程数 | `116` |
| 物理车辆 | `E1:10, E2:1, F1:35` |
| 政策冲突 | `0` |
| 完整覆盖 | `True` |
| 容量可行 | `True` |
| 迟到点 | `12` |
| 最大迟到 | `124.92 min` |
| 午夜后返库 | `0` |

当前主要不足：

- 总成本已从上一版 `50650.47` 降到 `49888.84`，但最大迟到仍有
  `124.92 min`。
- 不能把最大迟到当硬目标，因为题面时间窗是软约束；但最大迟到过大会影响
  现实解释性，因此下一轮优化应在“成本优先”的前提下寻找更好的服务质量。
- GPT Pro 建议的政策专用算子已做第一版实验，包括 `policy_conflict_remove`、
  `green_fuel_route_split`、`ev_priority_insert`、`post_16_fuel_repair`，但
  第一版实测提高成本，因此目前通过 `--use-policy-operators` 作为实验开关，
  不作为正式默认。
- 一次性重写为 `DemandAtom -> ServiceVisit -> RouteSpec -> ScheduledRoute`
  四层结构可能有理论价值，但当前风险高。子对话三应先做可验证的小步优化。

已经清理的临时输出：

- `outputs/problem2_smoke/`
- `outputs/problem2_candidate_seed37_r16/`

保留的输出：

- `outputs/problem2/`：正式第二问结果；
- `outputs/problem2_return1440_trial/`：24:00 返库场景试验，已在
  `outputs/README.md` 标明不是正式目标；
- `outputs/problem1/`：正式第一问结果；
- 其他第一问备份/实验目录按 `outputs/README.md` 说明使用。

## 子对话三初始化提示词

你现在接手 `c:\Math_Modeling_Project` 项目，任务是继续优化第二问：绿色配送
区限行政策下的车辆路径调度。请先完整理解当前项目状态，再开始提出或实现
改进。不要从头推翻已验证的结果，也不要盲信当前结果已经足够好。

### 你必须先阅读的文件

请按顺序阅读：

1. `项目文件导航.md`
2. `README.md`
3. `task_plan.md`
4. `progress.md`
5. `findings.md`
6. `解题总思路.md`
7. 原题与补充说明：
   - `A题：城市绿色物流配送调度.pdf`
   - `关于第十八届“华中杯”大学生数学建模挑战赛A题的补充说明.pdf`
8. 第二问设计与结果：
   - `docs/design/problem2_green_zone_policy_roadmap.md`
   - `docs/results/problem2_green_zone_policy_summary.md`
   - `docs/design/problem2_subdialogue3_optimization_handoff.md`
9. 第二问参考与改进思路：
   - `第二问参考思路/claude第二问参考思路：问题二完整方案.md`
   - `第二问参考思路/gemini第二问参考思路：Problem2_Improvement_Plan.md`
   - `第二问参考思路/gpt第二问参考思路：deep-research-report.md`
   - `第二问改进思路/GPT：问题二第一轮优化：Problem2_Improvement_Plan.md`
10. 当前第二问输出：
    - `outputs/problem2/recommendation.json`
    - `outputs/problem2/variant_comparison.csv`
    - `outputs/problem2/default_split/summary.json`
    - `outputs/problem2/default_split/route_summary.csv`
    - `outputs/problem2/default_split/stop_schedule.csv`
    - `outputs/problem2/default_split/problem2_policy_conflicts.csv`
    - `outputs/problem2/default_split/late_stop_diagnosis.csv`
11. 核心代码：
    - `green_logistics/problem_variants.py`
    - `green_logistics/problem2_engine.py`
    - `green_logistics/policies.py`
    - `green_logistics/scheduler.py`
    - `green_logistics/alns.py`
    - `green_logistics/operators.py`
    - `green_logistics/scheduler_local_search.py`
    - `green_logistics/solution.py`
    - `green_logistics/output.py`
    - `problems/problem2.py`
12. 测试：
    - `tests/test_problem_variants.py`
    - `tests/test_problem2_policy.py`
    - `tests/test_problem2_engine.py`
    - `tests/test_scheduler.py`
    - `tests/test_alns_smoke.py`
    - `tests/test_output.py`

### 必须牢记的题意和建模原则

- 第二问目标始终是题面官方总成本最小，不是迟到数最小、不是最大迟到最小、
  也不是碳排最低。
- 时间窗是软约束，迟到通过罚金进入官方目标函数。
- 绿色限行是硬约束，正式结果必须 `policy_conflict_count == 0`。
- 不能把政策违规作为第五个官方成本项；只能作为硬不可行或搜索辅助罚项。
- 没有道路几何，不要声称检测了车辆路径穿越绿区。
- 绿色客户判定使用坐标到 `(0,0)` 的欧氏距离，不能用配送中心 `(20,20)`。
- 时间使用从 0:00 起的分钟数：`8:00=480`，`16:00=960`。
- 限行窗口当前实现为 `[480, 960)`，燃油车 16:00 准点到达绿区客户视为合法。
- 距离矩阵使用原始 `customer_id`，算法内部服务节点是虚拟 `node_id`，不能混用。
- 行驶时间必须使用时变分段积分/FIFO，不能用“出发速度 × 距离”粗算。
- 固定成本按物理车辆计，不按 depot-to-depot 行程计。
- 题面没有 24:00 硬返库，不要为了消除午夜诊断牺牲题面总成本目标。

### 当前正式第二问状态

正式命令：

```powershell
python problems/problem2.py --iterations 40 --remove-count 16 --seed 20260427 --output-dir outputs/problem2
```

推荐结果：`DEFAULT_SPLIT`

- 总成本：`49888.84`
- 政策冲突：`0`
- 完整覆盖：`True`
- 容量可行：`True`
- 物理车辆：`E1:10, E2:1, F1:35`
- 迟到点：`12`
- 最大迟到：`124.92 min`
- 午夜后返库：`0`

对照候选：`GREEN_E2_ADAPTIVE`

- 总成本：`57109.67`
- 政策冲突：`0`
- 服务节点数：`166`
- 绿区服务节点数：`37`
- 当前不推荐，原因是总成本明显更高。

### 子对话三的职责

你的目标是继续优化第二问结果，重点寻找比 `49888.84` 更低的零冲突总成本
方案。如果能在不显著增加总成本、最好同时降低总成本的情况下减少最大迟到，
也可以作为改进方向。但不要本末倒置地把最大迟到当成硬目标。

请优先考虑这些方向：

1. 多 seed / 轻量邻域参数搜索  
   当前 `seed=20260427, remove_count=16` 是已验证最优候选。请尝试更系统但
   不失控的 seed 和 remove_count 组合。昂贵实验要分批、实时输出，避免一个
   长命令超时隐藏结果。

2. 成本优先的 tie-break/service-quality 辅助  
   不改变官方目标，但可以在搜索 score 或同成本近邻选择中更好地处理最大迟到。
   注意：最终推荐仍必须按官方总成本。

3. 更温和的局部绿区拆分  
   `GREEN_E2_ADAPTIVE` 全量绿区 E2 细拆成本太高。可以考虑第三条候选主线：
   只对早时间窗、高冲突风险或 E2 真有成本收益的绿区客户局部细拆，而不是全
   绿区细拆。

4. 政策诱发迟到诊断  
   增强 `late_stop_diagnosis.csv`，区分普通路由/排班迟到与政策诱发迟到。
   诊断必须服务于降低成本或改善合理性，不要做空泛标签。

5. 政策专用算子改进  
   当前 `--use-policy-operators` 第一版效果不好。不要盲目启用；应先定位它
   为什么抬高成本，再决定是否重写。

### 实现要求

- 先读代码和输出，再改代码。
- 每个实质改动都要有测试或至少有小规模 smoke 验证。
- 如果实验结果不好，要如实记录，不要把坏结果包装成成功。
- 如果发现现有方案或参考建议不符合题意，必须指出并修正。
- 新增/修改关键文件后同步更新：
  - `项目文件导航.md`
  - `README.md`
  - `task_plan.md`
  - `progress.md`
  - `findings.md`
  - 相关 `docs/results/` 或 `docs/design/` 文档
- 长时间优化前先保存当前正式结果，不要覆盖后找不回。
- 所有正式结果都要验证：
  - 完整覆盖；
  - 容量可行；
  - 政策冲突为 0；
  - 车辆使用不超过物理车队数量；
  - 总成本各分项合理；
  - `node_id` / `customer_id` 没有混用；
  - 输出表、JSON、诊断 CSV 一致。

### 建议的第一步

先读取 `outputs/problem2/default_split/stop_schedule.csv` 和
`late_stop_diagnosis.csv`，找出造成最大迟到 `124.92 min` 的客户、路线、车辆
和前后停靠结构。然后判断它是：

- 原始时间窗/距离导致的 direct infeasible；
- 多趟物理车辆复用导致的级联；
- 路线内部顺序不佳；
- 绿色政策诱发；
- 或 ALNS 没搜到更好结构。

只有定位清楚后，再决定是调参、改算子、局部拆分，还是增强 scheduler。

