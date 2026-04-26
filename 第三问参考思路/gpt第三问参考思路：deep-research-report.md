# 第三问项目审计与改进方案

## 下载文档

[下载 Markdown 文档](sandbox:/mnt/data/problem3_audit_and_plan_2026-04-25.md)

## 题意与仓库现状

我先核读了题面 PDF 与补充说明，再对 GitHub 仓库的项目文档、结果文件与核心源码做了审计。当前项目对题目的正式理解是稳定的：官方目标始终是总配送成本最小，即固定成本、能耗成本、碳排成本与软时间窗罚金之和；绿色配送区按城市中心 `(0,0)`、半径 `10 km` 判定；补充说明只给出 `08:00–17:00` 的速度分布，因此仓库把 `17:00` 之后延续为“一般时段”并明确写成建模假设。数据层已经把 `2169` 条订单聚合为 `88` 个有效客户、`148` 个虚拟服务节点；默认拆分下有 `12` 个有效绿区客户、`19` 个绿区服务节点。fileciteturn31file0 fileciteturn25file0 fileciteturn27file0

当前正式结果也很清晰。第一问正式输出为 `outputs/problem1/`，总成本 `48644.68`，`116` 趟、物理车辆 `E1:10, F1:33`，迟到点 `4`、最大迟到 `31.60 min`。第二问正式输出为 `outputs/problem2/`，推荐 `DEFAULT_SPLIT`，总成本 `49239.78`，政策冲突 `0`，`115` 趟、物理车辆 `E1:10, F1:35`，迟到点 `12`、最大迟到 `129.44 min`。候选比较中，`GREEN_E2_ADAPTIVE` 成本 `57504.49`，`GREEN_HOTSPOT_PARTIAL` 成本 `52312.11`；而服务质量更好的 `policy operators + EV reservation p500` 虽把迟到压到 `2` 个、最大迟到压到 `5.93 min`，但总成本上升到 `50770.72`，因此没有被推荐为正式答案。fileciteturn33file0 fileciteturn12file0 fileciteturn32file0 fileciteturn34file0

工程层面，仓库已经形成较完整的静态与政策约束求解栈：`data_processing`、`travel_time`、`cost`、`solution`、`scheduler`、`operators`、`alns`、`problem_variants`、`problem2_engine`、`policies`、`diagnostics` 与输出模块均已落地，并且最新进度日志记录了 `pytest -q` 通过 `60` 个测试。但第三问的正式入口与测试尚未实现：当前仓库没有正式的 `problems/problem3.py`、`green_logistics/dynamic.py`、`tests/test_problem3.py`。仓库自己的第三问交接文档也明确把第三问定位为“在现有第一问/第二问架构上扩展”，而不是重新推翻前两问。fileciteturn30file0 fileciteturn28file0 fileciteturn29file0 fileciteturn8file0

## 基于代码的关键诊断

从代码视角看，当前仓库其实已经具备第三问的大部分“静态底座”，但还缺少“动态状态层”。首先，`problem_variants.py` 已经证明项目可以在不改动原始 Excel 读取规则的前提下，显式构造一个工作中的 `ProblemData` 变体；这对第三问处理“取消、新增、改址、改时间窗”非常重要。其次，`policies.py` 已经把 `NoPolicyEvaluator` 和 `GreenZonePolicyEvaluator` 分离出来，因此第三问完全可以做成“是否继承第二问绿区限行”可切换，而不必为政策继承争议重写一套求解器。再次，`alns.py` 已明确把正式最优解的选择规则锁定为“完整覆盖 + 容量可行 + 政策可行前提下的最低 `total_cost`”，只有在总成本完全相同时才用更低迟到作并列打破，因此第三问继续沿用这一纪律是自然的。fileciteturn13file0 fileciteturn16file0 fileciteturn19file0 fileciteturn14file0

真正卡第三问的，不是静态成本模型，而是动态 warm start 能力。`solution.py` 里的 `evaluate_route()` 仍然把一次路线评价写成“从配送中心 `0` 出发、服务若干节点、最后回到配送中心”的 depot-to-depot trip；代码里 `current_customer_id = 0`、`current_time = depart_min`，这说明它默认求解的是“一天开始时”的静态 trip。`scheduler.py` 里的 `schedule_route_specs()` 则从 `DAY_START_MIN` 重建可用车辆池，并没有接受“某辆物理车此刻已经在客户节点 X、最早可继续服务时间为 t”的输入。因此，现有引擎适合静态日初排程，也适合第二问那种从头重排，但还不支持第三问真正需要的“冻结已执行部分后再继续排”。这是我基于当前代码结构做出的直接诊断。fileciteturn21file0 fileciteturn15file0

还有两个约束必须正视。其一，物理车链信息只在 `schedule_route_specs()` 产出的 `Solution.routes` 里才完整出现，因此第三问任何“受影响车辆链重排”“阻塞链调整”都必须在已调度解的层面做，而不能只在 `RouteSpec` 层假装自己知道前后继。其二，数据层的权威距离来源是固定的 `99×99` 距离矩阵，覆盖配送中心与既有 `98` 个客户节点；这意味着第三问如果要展示“新增订单”或“地址变更”，最稳妥的正式场景应优先落在现有节点集上，否则就需要额外声明如何为新坐标估计距离。fileciteturn17file0 fileciteturn25file0 fileciteturn31file0

## 第三问最合适的主线

我认为最合适的第三问主线，不是“再求一次更大的静态 VRP”，而是**事件驱动的滚动时域局部重优化**：以当前正式基准解为母方案，在事件时刻冻结已执行部分，只对受影响的未执行部分做局部 repair + 轻量 ALNS，再调用调度器重排物理车辆。这个方向与仓库自己的第三问交接文档一致，也与动态 VRP 的经典研究脉络一致：动态 VRP 通常不是一次性全局重建，而是随事件反复重优化；同时，时变路网仍应保持 FIFO 与时间相关行程时间，而不是退回静态路网近似。fileciteturn8file0 fileciteturn31file0 citeturn3search4turn6search5turn5search4turn4search10

基准解选择不应写死，而应参数化。因为第三问题面并没有像第二问那样明确写“在问题二基础上”，仓库交接文档也专门提醒不要先验假定是否继承绿区限行，所以最稳妥的工程写法是：`problem3.py` 接受一个显式开关，若按“继承问题二”解释就从 `outputs/problem2/default_split` 启动并套用 `GreenZonePolicyEvaluator`；若按“独立动态调度”解释就从 `outputs/problem1` 启动并使用 `NoPolicyEvaluator`。这样做不会偏题，也能避免以后因为题意解释变化而推翻第三问实现。fileciteturn8file0 fileciteturn16file0 fileciteturn30file0

我更推荐把第一次第三问决策时点限定在**服务完成节点**，而不是车辆正在一条边中途行驶的任意时刻。原因不是保守，而是数据与代码现实：当前仓库没有道路几何，也没有“从边中点到任意客户”的距离；如果你在弧中点重排，马上会遇到剩余路程无权威距离来源的问题。相反，如果在客户服务完成之后再触发重优化，车辆就位于一个真实客户节点上，当前位置、时间、剩余载重都可精确描述，且仍与当前 `distance_matrix + customer_id` 体系一致。这种“服务完成触发的事件驱动滚动优化”既保持物理解释，也能最大限度复用现有代码。这个取舍和文献里常见的 event-based dispatching 思路是一致的。fileciteturn8file0 fileciteturn21file0 fileciteturn15file0 citeturn6search5turn3search4

在这条主线上，第三问的完整流程应该是：先从基准解抽取当前时刻 `t_now` 的动态快照；冻结已服务节点与当前正在执行的前缀；把事件影响到的未服务节点、同一物理车后续链、空间或时间窗邻近节点以及若政策有效时的绿区关键节点一起纳入受影响子问题；先做确定性删除、插入、改址、改窗 repair，确保迅速产出可行解；再在这部分节点上跑轻量 ALNS；最后仍以官方总成本为第一排序标准，完整覆盖、容量可行和政策零冲突作为硬门槛，迟到、最大迟到与路径变动幅度只做辅助解释或并列 tie-break。这样既不偏离题意，也与当前仓库在第一问、第二问中已经建立的“官方目标优先、辅助评分只用于搜索”的纪律完全一致。fileciteturn19file0 fileciteturn20file0 fileciteturn12file0 fileciteturn8file0

## 可选技术路线比较

下面三条路线都能落在当前仓库上，但优先级不同。

| 路线 | 主要内容 | 预期收益 | 实现成本 | 主要风险 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 服务完成触发的局部滚动重优化 | 在服务完成时刻冻结前缀，重排受影响后缀，支持政策开关与 warm-start 调度 | 现实感、可解释性与现有架构兼容性最好 | 中等 | 需要扩展 evaluator 与 scheduler 的起点、车辆状态接口 | **主推** |
| 仅对未出发 trip 重优化 | 已出发 trip 完全冻结，只重排尚未出发的 trip 与新事件 | 最快落地，几乎不改静态 evaluator | 最低 | 响应能力偏弱，更像“半动态”而不是真正实时 | 可作备份 MVP |
| 加入轻量 anticipatory waiting 或 EV slack 策略 | 在主线稳定后，对部分车辆保留机动时间或 EV 容量 | 论文创新性更强，可解释“为未来事件留余量” | 中高 | 若直接做成主线，会引入额外事件分布假设 | 适合第二阶段增强 |

第一条路线最值得先做，因为它正好填补当前代码缺的 dynamic-state 能力，同时不需要推翻静态成本模型。第二条路线只在时间特别紧时才值得退而求其次，因为它能快速交出“能运行的第三问”，但对地址变更、时间窗调整这类真正发生在配送中的事件，响应力度偏弱。第三条路线是很好的论文创新点：动态 VRP 研究中，等待策略、时间预算与 offline-online ADP 都说明“为未来请求保留机动性”是有价值的；但这些方法通常需要未来请求的概率分布或在线交通信息，而本题数据并没有给出这类分布，所以它更适合作为第一条路线稳定后的增强项，而不应一开始就喧宾夺主。citeturn6search1turn6search2turn3search3turn3search1

## 最小可落地改造

如果目标是“尽快把第三问做成一个可信的、可复现的 Python 工程”，我建议只做**局部增强**，不要立即重写第一问架构。仓库当前的静态底座已经稳定、文档齐全、测试通过，而且第二问关闭时的明确结论也是“第三问应复用 Problem2Engine、scheduler、policy evaluator、diagnostics 和 experiment-ledger 接口”。因此，真正合理的改造不是重写第一问，而是新增动态层、轻微泛化 evaluator 和 scheduler、补第三问入口与测试。fileciteturn29file0 fileciteturn8file0 fileciteturn12file0

| 模块 | 最小改造建议 | 为什么是必要且足够的 |
| --- | --- | --- |
| `green_logistics/dynamic.py` | 新增 `DynamicEvent`、`VehicleSnapshot`、`FrozenPrefix`、`DynamicProblemState`、`AffectedSubproblem`、`DynamicScenarioResult` | 当前仓库缺的就是动态状态表达，不是静态成本公式 |
| `green_logistics/solution.py` | 把 `evaluate_route()` 泛化为可选 `origin_customer_id`、`origin_depart_min`、`fixed_cost` 复用；默认值保持现状 | 第三问需要从“当前客户节点、当前时刻”继续评估后缀，不应强迫每次都从 depot 重新开始 |
| `green_logistics/scheduler.py` | 支持 `initial_vehicle_states`、`locked_routes` 或等价 warm-start 接口 | 现有 scheduler 从 `DAY_START_MIN` 重建车辆池，不足以表达“这辆车现在几点后可继续干活” |
| `green_logistics/problem3_engine.py` | 统一快照、事件应用、受影响子问题构造、repair、局部 ALNS、重排与结果选择 | 让第三问保持与第二问类似的可审计 orchestrator 风格 |
| `problems/problem3.py` | 作为正式入口，允许选择基准解、是否继承政策、事件脚本、输出目录 | 避免把第三问逻辑塞进 Problem1 或 Problem2 runner |
| `tests/test_dynamic.py` 与 `tests/test_problem3.py` | 先测取消、新增、时间窗变更、地址变更、冻结规则、政策延续与输出一致性 | 第三问最容易在状态迁移上出错，必须测试先行 |
| `green_logistics/output.py` | 增加 `route_changes.csv`、`scenario_comparison.csv`、`dynamic_diagnosis.csv` | 第三问必须展示“调整前后发生了什么”，而不是只给一张最终表 |

如果你还想提高第三问中“新增订单、改址”表达的清晰度，我赞成引入一个**最小版 `ServiceVisit` 或 `PendingVisit` 抽象**，但我不建议现在就做完整的 `DemandAtom -> ServiceVisit -> RouteSpec -> ScheduledRoute` 四层大重构。原因很直接：`problem_variants.py` 已经证明现有 `ProblemData.service_nodes` 足以承载显式变体；第三问当前真正缺的是“状态快照”和“warm-start 调度”，不是静态 demand atom 无法表达。除非后面你们决定把第三问扩展到大量新订单流、复杂改址与中途分流，否则四层大重构的收益还不足以覆盖回归风险。fileciteturn13file0 fileciteturn26file0

## 场景设计与结果呈现

第三问最大的现实约束，是题面给了“动态事件类型”，但没有给一套官方的事件流数据。因此你们要做的是**场景化动态策略**，而不是伪装成有实时平台数据。这里最重要的落地原则是：正式展示场景优先选在**现有 `98` 个客户节点内部**，这样新增订单、地址变更和时间窗调整都可以继续使用权威距离矩阵；如果你们想展示“新增到一个全新坐标点”，那就必须明确说明距离是如何近似生成的，否则就会脱离附件给定的主数据体系。fileciteturn25file0 fileciteturn31file0 fileciteturn8file0

基于当前仓库，我建议第三问至少展示三类场景。第一类是**订单取消**：在某个尚未服务的非绿区或普通客户节点上取消一个 pending visit，观察是否能压缩后续 trip、减少固定或能耗成本。第二类是**新增订单**：优先把新增订单放在一个现有客户节点，尤其可以设计一个绿区客户新增需求场景，以检验在政策有效时 EV 资源如何被重新分配。第三类是**地址变更或时间窗收紧**：把一个尚未服务节点从客户 A 改到已有的客户 B，或者把其时间窗上界前移，观察局部后缀是否需要换车、换序或拆链。若你们选择“继承问题二政策”的解释，至少应包含一个绿区事件场景，否则第三问就没有真正验证动态下的绿色配送约束。fileciteturn8file0 fileciteturn12file0

结果呈现上，正式指标应继续把**官方总成本**放在第一位，然后依次报告：与基准方案相比的成本变化、完整覆盖、容量可行、政策冲突数、车辆使用变化、迟到点数、最大迟到，以及“方案扰动规模”，例如改动了多少条 trip、多少个 service node 被重分配、多少辆物理车的后续链被改写。这里的“扰动规模”很适合做第三问新增亮点，但只能作为辅助指标或管理解释，不能伪装成官方新目标。仓库自己的第三问交接文档已经明确要求如此，而动态 VRP 文献中关于 partial reoptimization 与 waiting strategy 的研究，也正是把“响应能力”和“额外扰动”视作策略价值的一部分，而非简单改写主目标。fileciteturn8file0 citeturn6search0turn6search1

## 开放问题与限制

第三问题面没有提供官方事件数据流，也没有明示是否继承第二问绿区限行；这意味着你们必须在论文里把第三问的事件场景与政策继承规则写成**明确假设**，而不是把某种解释包装成唯一正确答案。fileciteturn8file0

当前仓库和附件都没有道路几何，也没有“从弧中点到任意节点”的距离，因此真正的 mid-arc 重规划不是当前数据体系下的首选。若后续你们一定要展示这种能力，就需要额外说明距离近似规则，这会比“服务完成节点触发的动态重优化”更依赖额外假设。fileciteturn21file0 fileciteturn25file0

## 结论

基于题面、补充说明、当前 GitHub 仓库、正式输出与相关文献，我的结论很明确：**第三问最优先要做的，不是重写第一问，而是给现有静态求解栈补上一层动态状态与 warm-start 调度能力。** 最合适的主线是“服务完成触发的事件驱动滚动重优化”，并把是否继承第二问政策做成显式可选项。若时间极其紧张，可以先交付“仅重排未出发 trip”的低配版；若主线稳定，再把轻量 anticipatory waiting 或 EV slack 作为论文创新增强。这样做既延续了仓库已经验证的官方成本目标、时变速度积分、Jensen 能耗修正与政策硬约束，又能在第三问中给出物理一致、可解释、可复现的动态调度方案。fileciteturn30file0 fileciteturn31file0 fileciteturn8file0 citeturn4search0turn3search0turn5search4turn3search4