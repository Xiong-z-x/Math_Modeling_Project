# 第三问子对话四项目汇报与初始化提示词

> 2026-04-26 补充：三份第三问参考思路（Claude/Gemini/GPT）已综合审计，最终工程路线记录在
> `docs/design/problem3_dynamic_response_roadmap.md`。后续实现以该路线图为主，本文保留为初始化提示和题意红线汇总。
>
> 2026-04-26 实现补充：第三问已新增动态响应代码、测试和 `outputs/problem3/` 四情景结果；
> 当前正式摘要见 `docs/results/problem3_dynamic_response_summary.md`，完整论文收官母稿见 `docs/results/problem3_modeling_and_solution_closeout.md`。本文中“第三问尚未开始”的段落是历史交接状态，后续以新摘要、收官母稿和 `progress.md` 为准。

## 1. 给主对话的最快项目汇报

当前项目位于 `c:\Math_Modeling_Project`。第一问和第二问已经完成当前建模轮次的正式求解、结果归档和论文写作向总结。第三问尚未开始实现，后续应在新对话中从现有数据层、成本层、时变行驶层、物理车辆排班层和第二问政策层继续扩展，而不是重写整个项目。

第一问正式结果：

- 输出目录：`outputs/problem1/`
- 论文总结：`docs/results/problem1_static_scheduling_summary.md`
- 命令：`python problems/problem1.py --iterations 40 --remove-count 8 --seed 20260424 --output-dir outputs/problem1`
- 总成本：`48644.68`
- 物理车辆：`E1:10, F1:33`
- 迟到点 / 最大迟到：`4` / `31.60 min`
- 完整覆盖、容量可行、无午夜后返库。

第二问正式结果：

- 输出目录：`outputs/problem2/`
- 简版总结：`docs/results/problem2_green_zone_policy_summary.md`
- 完整收官母稿：`docs/results/problem2_modeling_and_solution_closeout.md`
- 命令：`python problems/problem2.py --iterations 40 --remove-count 16 --seed 20260427 --use-ev-reservation --ev-reservation-penalty 250 --output-dir outputs/problem2`
- 推荐方案：`DEFAULT_SPLIT`
- 总成本：`49239.78`
- 政策冲突：`0`
- 物理车辆：`E1:10, F1:35`
- 迟到点 / 最大迟到：`12` / `129.44 min`
- 对照方案 `policy operators + EV reservation p500` 已保存在 `outputs/problem2_experiments/formal_screen_policy_ev_p500/`，总成本 `50770.72`，迟到点 `2`，最大迟到 `5.93 min`，只作为服务质量灵敏度方案，不作为第二问正式推荐。

输出目录当前已经整理：

| 路径 | 状态 | 用途 |
| --- | --- | --- |
| `outputs/problem1/` | 正式 | 第一问主答案 |
| `outputs/problem2/` | 正式 | 第二问主答案和三候选比较 |
| `outputs/problem2_previous_49888_20260425/` | 历史备份 | 第二问 EV reservation 优化前旧正式结果 |
| `outputs/problem2_experiments/` | 实验账本 | 第二问参数和算子筛选；不可当正式答案 |
| `outputs/problem2_return1440_trial/` | 情景检查 | 24:00 返库场景，不是题面正式约束 |

已清理的中间目录包括 `outputs/problem2_smoke/`、`outputs/problem2_candidate_seed37_r16/`、`outputs/problem2_ev_reservation_p250/`、`outputs/problem2_ev_reservation_p250_full/`。后续第三问不得覆盖 `outputs/problem1/` 或 `outputs/problem2/`，应新建 `outputs/problem3/` 或 `outputs/problem3_experiments/`。

## 2. 第三问接手前必须牢记的题意红线

请新模型进入第三问前重新验读原题和补充说明，尤其不要把前两问的经验机械搬过去。当前已确认的全项目红线如下：

1. 官方成本项仍是固定成本、能源成本、碳排成本、软时间窗罚金。若第三问题面新增动态响应评价项，必须先从题面确认，不能自己发明正式成本项。
2. 时间窗是软约束，迟到通过罚金进入目标；不要把零迟到改成硬目标。
3. 第二问绿色限行若在第三问中继续生效，则它仍是硬约束，正式结果必须 `policy_conflict_count == 0`。
4. 绿色区中心是 `(0,0)`，不是配送中心 `(20,20)`。
5. 没有道路几何，不能声称检测了车辆路径穿越绿色区。
6. 时间使用从 0:00 起的分钟数，`8:00=480`，`16:00=960`。
7. 限行窗口当前实现为 `[480,960)`，燃油车 16:00 准点到达绿色客户合法。
8. 距离矩阵使用原始 `customer_id`；算法内部服务节点是虚拟 `node_id`，不能混用。
9. 行驶时间和能耗必须按时变分段积分/FIFO 计算，不能用“出发速度乘全程距离”粗算。
10. 固定成本按物理车辆计，不按 depot-to-depot 趟次数计。
11. 题面没有 24:00 硬返库约束；除非第三问题面明确新增，否则不要把它作为正式可行性约束。
12. 不要为了让图表或诊断更好看而牺牲官方总成本目标。

## 3. 第三问建议阅读顺序

进入第三问子对话四后，先按以下顺序阅读，不要直接改代码：

1. `项目文件导航.md`
2. `README.md`
3. `task_plan.md`
4. `progress.md`
5. `findings.md`
6. `解题总思路.md`，重点读第 11 节“第三问技术路线”
7. 原题与补充说明：
   - `A题：城市绿色物流配送调度.pdf`
   - `关于第十八届“华中杯”大学生数学建模挑战赛A题的补充说明.pdf`
8. 第一问与第二问总结：
   - `docs/results/problem1_static_scheduling_summary.md`
   - `docs/results/problem2_green_zone_policy_summary.md`
   - `docs/results/problem2_modeling_and_solution_closeout.md`
9. 第二问设计与优化记录：
   - `docs/design/problem2_green_zone_policy_roadmap.md`
   - `docs/design/problem2_subdialogue3_optimization_roadmap.md`
   - `docs/design/problem2_subdialogue3_optimization_handoff.md`
10. 正式输出与对照输出：
    - `outputs/problem1/summary.json`
    - `outputs/problem2/recommendation.json`
    - `outputs/problem2/variant_comparison.csv`
    - `outputs/problem2/default_split/summary.json`
    - `outputs/problem2/default_split/route_summary.csv`
    - `outputs/problem2/default_split/stop_schedule.csv`
    - `outputs/problem2/default_split/problem2_policy_conflicts.csv`
    - `outputs/problem2/default_split/late_stop_diagnosis.csv`
    - `outputs/problem2_experiments/formal_screen_policy_ev_p500/summary.csv`
11. 核心代码：
    - `green_logistics/constants.py`
    - `green_logistics/data_processing/loader.py`
    - `green_logistics/travel_time.py`
    - `green_logistics/cost.py`
    - `green_logistics/solution.py`
    - `green_logistics/scheduler.py`
    - `green_logistics/problem_variants.py`
    - `green_logistics/problem2_engine.py`
    - `green_logistics/policies.py`
    - `green_logistics/diagnostics.py`
    - `green_logistics/operators.py`
    - `green_logistics/alns.py`
    - `green_logistics/output.py`
    - `problems/problem1.py`
    - `problems/problem2.py`
12. 测试：
    - `tests/test_data_loader.py`
    - `tests/test_travel_time.py`
    - `tests/test_cost.py`
    - `tests/test_solution.py`
    - `tests/test_scheduler.py`
    - `tests/test_problem_variants.py`
    - `tests/test_problem2_policy.py`
    - `tests/test_problem2_engine.py`
    - `tests/test_diagnostics.py`
    - `tests/test_alns_smoke.py`
    - `tests/test_output.py`

当前仓库中还没有 `problems/problem3.py` 和 `tests/test_problem3.py` 的正式实现；`项目文件导航.md` 中它们是规划项。第三问应新增这些入口，并同步更新台账。

## 4. 第三问推荐技术路线

第三问应理解为动态事件响应问题。不要从零开始重跑一套完全独立的静态 VRP；更合理的路线是基于第一问/第二问正式方案做滚动时域局部重优化。

推荐分阶段执行：

1. **题意复核**  
   先从原题 PDF 精确确认第三问给出的动态事件类型、事件时刻、是否继承绿色限行、是否新增评价指标。若题面没有明确事件数据，需要构造有代表性的情景，也必须说明是假设情景。

2. **基准方案选择**  
   若第三问继承第二问绿色限行，则以 `outputs/problem2/` 的 `DEFAULT_SPLIT` 为基准。若第三问不含绿色限行，则以 `outputs/problem1/` 为基准。不要混用。

3. **动态状态建模**  
   在事件时刻 `t_now`：
   - 已完成服务节点冻结；
   - 已经出发的车辆，其当前位置、已服务节点、剩余载重和后续承诺需要明确处理；
   - 未出发趟次和未服务节点进入可重排集合；
   - 若无法精确定位“正在路上”的车辆位置，必须说明近似规则，不能假装拥有实时轨迹数据。

4. **事件处理层**  
   建议新增 `green_logistics/dynamic.py` 或类似模块，定义：
   - `DynamicEvent`
   - `FrozenRoutePrefix`
   - `DynamicProblemState`
   - `DynamicReoptimizationResult`
   事件类型可先覆盖 `订单取消`、`新增订单`、`地址变更`、`时间窗调整`。实际类型以题面为准。

5. **局部子问题构造**  
   对动态事件影响的节点、车辆和时间窗构造局部子问题。不要动已经完成的服务；不要让同一节点重复服务；不要让取消订单仍留在路线中。

6. **快速修复 + 轻量 ALNS**  
   首先实现确定性插入/删除/重排 repair，保证能产出可行方案；再在局部未服务节点上使用轻量 ALNS 提升成本。不要一开始就做大规模重构。

7. **动态目标解释**  
   动态方案至少报告：
   - 调整后官方总成本；
   - 相对基准的成本变化；
   - 政策冲突数；
   - 完整覆盖和容量可行性；
   - 车辆使用变化；
   - 迟到点数和最大迟到；
   - 路线变动规模。
   若加入“扰动惩罚”或“方案稳定性惩罚”，必须声明它是动态响应辅助指标，不能冒充题面官方成本，除非第三问题面明确要求。

8. **输出封装**  
   新增 `outputs/problem3/` 作为正式第三问输出目录，建议结构：
   - `outputs/problem3/recommendation.json`
   - `outputs/problem3/scenario_comparison.csv`
   - `outputs/problem3/<scenario_name>/summary.json`
   - `outputs/problem3/<scenario_name>/route_summary.csv`
   - `outputs/problem3/<scenario_name>/stop_schedule.csv`
   - `outputs/problem3/<scenario_name>/route_changes.csv`
   - `outputs/problem3/<scenario_name>/policy_conflicts.csv`
   - `outputs/problem3/<scenario_name>/dynamic_diagnosis.csv`

9. **论文总结**  
   第三问结束时新增 `docs/results/problem3_dynamic_response_summary.md` 和 `docs/results/problem3_modeling_and_solution_closeout.md`，结构参考第二问完整收官文档，但要突出动态事件、冻结规则、局部重优化和响应效果。

## 5. 第三问实现时的理性要求

第三问实现必须遵守以下工程与建模纪律：

1. 先读代码和输出，再改代码。
2. 不覆盖 `outputs/problem1/` 和 `outputs/problem2/`。
3. 每个实质改动都要有测试；至少新增 `tests/test_problem3.py`，并按风险补充 `tests/test_dynamic.py`。
4. 结果不好就记录“不好”，不要包装成成功。
5. 不要盲信参考材料或旧代码；凡是与题面、补充说明、数据事实冲突的建议都要修正。
6. 任何新增假设都必须写入文档和输出摘要。
7. 动态事件如果需要新距离、新坐标或新订单，而题面没有给出完整数据，必须明确数据来源或近似方式。
8. 检查 `node_id` 和 `customer_id`，尤其在新增订单或地址变更时更容易混淆。
9. 检查物理车辆多趟链条，不能让同一物理车在时间上重叠执行多个趟次。
10. 检查能耗和碳排，不要把电动车写成零碳。
11. 不要为了降低迟到数而让官方总成本大幅恶化，除非题面第三问明确改了目标。
12. 长实验要写增量账本，避免超时后丢失结果。
13. 如果命令失败或发现流程性错误，写入 `.learnings/`，并同步更新 `progress.md` 或相关设计文档。

## 6. 第三问结果验证清单

任何第三问正式结果都必须逐项验证：

- 原始题意和补充说明已复核；
- 动态事件数据被准确转化；
- 已完成服务没有被重新安排；
- 取消订单不再服务；
- 新增订单被覆盖一次；
- 地址或时间窗变更后，输出表与 JSON 一致；
- 未服务节点覆盖完整，无缺失、无重复；
- 所有趟次容量可行；
- 物理车辆数量不超过题面车队数量；
- 同一物理车辆时间链不重叠；
- 若继承第二问政策，则政策冲突为 0；
- 时间窗迟到通过罚金计入，不被误写为硬约束；
- 行驶时间使用时变分段积分；
- 成本分项相加等于总成本；
- `route_summary.csv`、`stop_schedule.csv`、`summary.json`、`recommendation.json` 一致；
- 可视化不声称道路几何穿越绿色区；
- 与第一问/第二问基准对比解释合理；
- `pytest -q` 通过。

## 7. 可直接复制给第三问子对话四的初始化提示词

```markdown
你现在接手 `c:\Math_Modeling_Project` 项目，任务是开始求解第三问：动态事件响应下的城市绿色物流配送调度。请先完整理解当前项目状态，再提出或实现方案。不要从头推翻第一问和第二问已验证的结果，也不要盲信当前结果已经足够好。

### 你的核心职责

1. 重新验读原题 `A题：城市绿色物流配送调度.pdf` 和补充说明，精确确认第三问要求、动态事件类型、事件时刻、是否继承绿色区限行、是否新增评价指标。
2. 在第一问/第二问现有架构上构建第三问动态响应模型。默认方向是“冻结已执行部分 + 局部重优化未执行部分 + 输出调整前后对比”，不是完全重写静态求解器。
3. 若第三问继承绿色限行，则以第二问正式结果 `outputs/problem2/` 为基准，并保持政策冲突为 0；若第三问不继承绿色限行，则以第一问正式结果 `outputs/problem1/` 为基准。先从题面确认，不要猜。
4. 目标仍以题面官方总成本和第三问明确指标为准。时间窗是软约束，迟到通过罚金进入成本；不要把迟到数或最大迟到擅自改成主目标。
5. 产出可复现代码、输出和论文写作向总结，并为所有关键结果做一致性验证。

### 必须先阅读的文件

请按顺序阅读：

1. `项目文件导航.md`
2. `README.md`
3. `task_plan.md`
4. `progress.md`
5. `findings.md`
6. `解题总思路.md`，重点读第 11 节“第三问技术路线”
7. 原题与补充说明：
   - `A题：城市绿色物流配送调度.pdf`
   - `关于第十八届“华中杯”大学生数学建模挑战赛A题的补充说明.pdf`
8. 第一问与第二问总结：
   - `docs/results/problem1_static_scheduling_summary.md`
   - `docs/results/problem2_green_zone_policy_summary.md`
   - `docs/results/problem2_modeling_and_solution_closeout.md`
9. 第二问技术记录：
   - `docs/design/problem2_green_zone_policy_roadmap.md`
   - `docs/design/problem2_subdialogue3_optimization_roadmap.md`
   - `docs/design/problem2_subdialogue3_optimization_handoff.md`
10. 当前正式输出：
    - `outputs/problem1/summary.json`
    - `outputs/problem2/recommendation.json`
    - `outputs/problem2/variant_comparison.csv`
    - `outputs/problem2/default_split/summary.json`
    - `outputs/problem2/default_split/route_summary.csv`
    - `outputs/problem2/default_split/stop_schedule.csv`
    - `outputs/problem2/default_split/problem2_policy_conflicts.csv`
    - `outputs/problem2/default_split/late_stop_diagnosis.csv`
    - `outputs/problem2_experiments/formal_screen_policy_ev_p500/summary.csv`
11. 核心代码：
    - `green_logistics/constants.py`
    - `green_logistics/data_processing/loader.py`
    - `green_logistics/travel_time.py`
    - `green_logistics/cost.py`
    - `green_logistics/solution.py`
    - `green_logistics/scheduler.py`
    - `green_logistics/problem_variants.py`
    - `green_logistics/problem2_engine.py`
    - `green_logistics/policies.py`
    - `green_logistics/diagnostics.py`
    - `green_logistics/operators.py`
    - `green_logistics/alns.py`
    - `green_logistics/output.py`
    - `problems/problem1.py`
    - `problems/problem2.py`
12. 测试：
    - `tests/test_data_loader.py`
    - `tests/test_travel_time.py`
    - `tests/test_cost.py`
    - `tests/test_solution.py`
    - `tests/test_scheduler.py`
    - `tests/test_problem_variants.py`
    - `tests/test_problem2_policy.py`
    - `tests/test_problem2_engine.py`
    - `tests/test_diagnostics.py`
    - `tests/test_alns_smoke.py`
    - `tests/test_output.py`

### 当前正式状态

第一问：
- 正式输出：`outputs/problem1/`
- 总成本：`48644.68`
- 物理车辆：`E1:10, F1:33`
- 迟到点 / 最大迟到：`4` / `31.60 min`

第二问：
- 正式输出：`outputs/problem2/`
- 推荐方案：`DEFAULT_SPLIT`
- 总成本：`49239.78`
- 政策冲突：`0`
- 物理车辆：`E1:10, F1:35`
- 迟到点 / 最大迟到：`12` / `129.44 min`
- 服务质量对照方案保存在 `outputs/problem2_experiments/formal_screen_policy_ev_p500/`，总成本 `50770.72`，迟到点 `2`，最大迟到 `5.93 min`，只能作为论文灵敏度讨论，不是正式推荐。

### 必须牢记的建模原则

- 官方目标不能偏题。除非第三问题面明确修改目标，否则仍以题面总成本为核心。
- 时间窗是软约束，不是硬约束。
- 若绿色限行在第三问中生效，它是硬约束，正式结果必须零政策冲突。
- 绿色区中心是 `(0,0)`，配送中心是 `(20,20)`。
- 没有道路几何，不能声称检测路径穿越绿色区。
- 距离矩阵用原始 `customer_id`，虚拟服务节点用 `node_id`，不能混用。
- 行驶时间和能耗必须时变分段积分。
- 固定成本按物理车辆计，不按趟次计。
- 题面没有 24:00 硬返库，不要擅自加。
- 电动车有电力碳排因子，不是零碳。

### 推荐实施路线

1. 先写 `docs/design/problem3_dynamic_response_roadmap.md`，明确第三问题意、事件数据、基准方案、冻结规则、动态目标和输出格式。
2. 新增动态事件数据结构，建议放在 `green_logistics/dynamic.py`：
   - `DynamicEvent`
   - `FrozenRoutePrefix`
   - `DynamicProblemState`
   - `DynamicReoptimizationResult`
3. 新增 `problems/problem3.py`，默认输出到 `outputs/problem3/`，不要覆盖 `outputs/problem1/` 或 `outputs/problem2/`。
4. 先做确定性局部 repair，保证取消、新增、时间窗变化等事件能产出可行解。
5. 再对未执行/未服务部分做轻量 ALNS，提高官方总成本表现。
6. 若需要方案稳定性或变动惩罚，只能作为动态响应辅助指标；是否进入正式目标必须以题面为准。
7. 新增 `tests/test_problem3.py`，必要时新增 `tests/test_dynamic.py`。
8. 正式结果输出：
   - `outputs/problem3/recommendation.json`
   - `outputs/problem3/scenario_comparison.csv`
   - `outputs/problem3/<scenario>/summary.json`
   - `outputs/problem3/<scenario>/route_summary.csv`
   - `outputs/problem3/<scenario>/stop_schedule.csv`
   - `outputs/problem3/<scenario>/route_changes.csv`
   - `outputs/problem3/<scenario>/dynamic_diagnosis.csv`
9. 第三问收官时新增 `docs/results/problem3_dynamic_response_summary.md` 和 `docs/results/problem3_modeling_and_solution_closeout.md`。

### 验证要求

所有第三问正式结果必须验证：

- 已完成服务不被重排；
- 取消订单不再服务；
- 新增订单被服务一次；
- 未取消服务节点覆盖完整、无重复；
- 容量可行；
- 车辆数不超过车队数量；
- 同一物理车时间链不重叠；
- 若继承第二问政策，则政策冲突为 0；
- 成本分项相加等于总成本；
- route/stop/summary/recommendation 输出一致；
- `node_id` 和 `customer_id` 没有混用；
- 结果解释符合物理现实和题意；
- `pytest -q` 通过。

### 工作态度要求

保持理性客观，不要自欺欺人。如果结果不好，就记录为不好，然后诊断为什么不好。不要把辅助评分写成官方目标，不要为了漂亮指标牺牲题面总成本。任何命令失败、工具误用或建模假设修正，都要写入 `.learnings/` 或 `progress.md`，提醒后续模型。长时间实验要使用增量账本，避免超时丢失结果。

现在开始第三问前，先完成题意复核和现状对齐，然后再给出最小可落地方案；如果方案足够明确，就直接实现、验证、记录并输出结果。
```
