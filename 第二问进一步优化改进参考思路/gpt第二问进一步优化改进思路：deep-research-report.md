# 第二问优化瓶颈审计与下一步建议

## 审计基线

基于仓库当前 `Problem2Engine`、调度/ALNS 代码、正式输出和交接文档，第二问的正式建模边界已经很清楚：目标仍是题面官方总配送成本最小，即固定成本、能耗成本、碳排成本和软时间窗惩罚之和；绿色限行是硬约束，时间窗仍是软约束；当前正式推荐解是 `DEFAULT_SPLIT`，总成本 `49888.84`，政策冲突 `0`，完整覆盖与容量可行都为 `True`。fileciteturn8file0fileciteturn12file0fileciteturn10file0

我先给出总判断：你们现在的主要瓶颈，不是题意理解错，也不是“必须大改架构才有救”；更像是**第二问的关键稀缺资源其实是限行时段内可用的 EV 运力，而这件事在当前搜索阶段没有被足够早地表达出来，最后在 scheduler 的多趟复用层面集中爆成 Type B 级联迟到**。这也是为什么当前结果“政策冲突为 0，但最大迟到仍大”，而且第一版政策专用算子没有转化成更低总成本。fileciteturn10file0fileciteturn14file0fileciteturn17file0

## 主要瓶颈

从 `late_stop_diagnosis.csv` 和诊断代码看，当前 12 个晚点点位**全部**被归类为 `Type B multi-trip cascade`；而这类分类的定义恰恰是：从仓库 08:00 直发并不晚、同一趟若“fresh start”也不晚，但在真实物理车多趟排班后晚了。换句话说，当前最大迟到 `124.92 min` 的直接成因，不是“原始距离+时间窗就不可行”，也不是“单趟内部 route order 先天错误”，而是**物理车辆复用顺序把本来可准时的 trip 压晚了**。fileciteturn14file0fileciteturn17file0

更重要的是，这个级联迟到不是随机的。诊断表里的 12 个晚点中，**11 个发生在 E1 trip 上，只有 1 个发生在 F1 trip 上**；同时，**9 个晚点点位位于绿区**，而绿区晚点分钟数合计约占总晚点分钟数的 `94.76%`。这说明当前迟到的主导来源并不是“燃油车剩余政策冲突”，而是**硬政策下绿区早窗任务对 EV 的争抢**。换句话说，scheduler 的多趟复用是表层症状，深层原因是“政策诱发的 EV 稀缺”没有在 route-spec 构造与 repair 评分里被前置感知。fileciteturn14file0fileciteturn12file0citeturn6calculator0

这个判断还能被具体 trip 例子验证。比如客户 8 的四个晚点节点 `T0018-T0021` 都是**单停靠 E1 trip**，其 `fresh_route_late_min` 都是 `0`，但它们分别在物理车 `E1-002/E1-007/E1-005/E1-009` 完成更早 trip 后，才在 `11:23、11:46、13:07、13:16` 发车，最终形成 `88.23、95.78、116.23、124.92` 分钟晚点。这种结构非常像“本该保留给绿区早窗节点的 E1，被前序更灵活的任务先占掉了”。fileciteturn14file0fileciteturn33file0

反过来看，当前第一版政策算子为什么效果一般，也就不难解释了。现有政策算子重点围绕 `policy_conflict_remove`、`green_fuel_route_split`、`post_16_fuel_repair` 这类“燃油-绿区冲突”或“16:00 后燃油兜底”思路展开；但当前 12 个晚点里，真正属于“燃油延后到 16:00 才合法”的典型只看到一个：`T0059` 的 F1 在客户 3 处 `16:00` 到达，合法但晚了 `39` 分钟。也就是说，**当前主导迟到的不是 fuel-conflict，而是 EV-cascade**，所以把主要算子预算放在 fuel-conflict 上，命中率天然不高。fileciteturn14file0fileciteturn15file0fileciteturn29file0

代码侧也支持这个结论。`schedule_route_specs()` 会对每个 `RouteSpec` 在所有可行车型里选当前得分最低者，但这个得分本质上还是**单条 candidate route 的局部评分**；它并没有显式计入“未来绿区早窗节点对 EV 的机会成本”。而 repair 阶段的 `_local_route_cost()` 又是把 route 固定在 `DAY_START_MIN` 直接评估，`_retyped_spec()` 也以局部容量可行为先，repair 插入成本因此并不知道后面 scheduler 会因为 EV 紧张而把某些绿区 trip 压晚。你们现在有 `allowed_vehicle_type_ids` 和 `policy_service_mode` 这类元数据，但我在当前 scheduler 路径里没有看到 `policy_service_mode` 被真正消费，所以“策略意图”并没有被完整传到物理排班层。fileciteturn20file0fileciteturn25file0fileciteturn22file0fileciteturn34file0fileciteturn34file1fileciteturn34file3

## 对关键问题的判断

先回答你问得最关键的一个：`DEFAULT_SPLIT` 明显优于 `GREEN_E2_ADAPTIVE`，**是的，这很大程度上说明“全量绿区按 E2 细拆”在这组数据上拆得过头了；但问题不只是固定成本过高，而是固定成本和时间协调一起恶化了**。从正式结果看，两条主线的总成本差 `7220.83` 中，固定成本增加了 `3600`，时间窗惩罚再增加了 `2928.51`；反而总里程是下降的，`13377.44 km -> 13260.82 km`。这说明 `GREEN_E2_ADAPTIVE` 并不是“路更差”，而是**节点碎片化以后，物理车复用和时间协同明显更差**。fileciteturn13file0fileciteturn31file0fileciteturn32file0citeturn7calculator0turn7calculator1turn7calculator4

这个判断还可以从“趟数与物理车数背离”看出来。`GREEN_E2_ADAPTIVE` 的 depot-to-depot trips 其实从 `116` 降到了 `114`，但物理车辆却从 `46` 辆提高到 `55` 辆，平均每辆物理车承担的 trip 数从 `2.52` 掉到 `2.07`。这不是“跑得更多”造成的，而是**更细的绿区拆分把同时段的资源冲突放大了，导致复用效率下降**。所以我不建议再沿着“所有绿区客户都按 E2 粒度细拆”继续往前推。fileciteturn31file0fileciteturn32file0citeturn8calculator0turn8calculator1

再回答“最大迟到更像 ALNS 组合不好，还是 scheduler 多趟复用，还是政策强制 EV/16:00 后燃油，还是 RouteSpec 粒度与车型耦合过强”。我的判断是：**近因是 scheduler 多趟复用；根因是政策诱发的 EV 稀缺；再上一层是 RouteSpec/repair 对车型机会成本感知过弱；而纯粹的 route-order 问题目前不是主因。** 因为当前没有 Type A，也没有 Type C；与此同时，`RouteSpec` 在默认线路里对车型大多是“完全灵活”，repair 插入又按局部 route 成本近似，导致“本来应该让给燃油车的灵活任务”可能被 E1 先拿走。fileciteturn14file0fileciteturn17file0fileciteturn20file0fileciteturn25file0

至于“ALNS 是否应该更早感知绿色限行”，我的答案也是**是，但不是简单地更早感知‘燃油绿区冲突’就够了，而是要更早感知‘谁是必须抢 EV 的绿区关键任务，谁只是可以让给燃油车的灵活任务’**。这点和近年的 rich VRP / mixed-fleet 文献是吻合的：ALNS 的优势本来就来自问题专用 destroy/repair，而不是把所有复杂性都留给最后调度；在 time-dependent multi-trip 场景下，文献也强调“高频调用的 trip 评价”和“问题专用移除/局部搜索”才是效率关键。混合车队文献则反复证明，EV/燃油的 fleet-mix 不是纯后处理问题，而要与路由一起优化。citeturn11search0turn13search0turn11search1turn11search13

## 最值得尝试的路线

### EV 资源保留与阻塞链重排

这是我最推荐先做的一条，因为它最直接命中当前主瓶颈，而且不改题意、不加题外硬约束。核心思路不是“追零迟到”，而是：**在不改变正式目标函数的前提下，让搜索更早知道 EV 是 Problem 2 里的稀缺资源，并且在出现 Type B 晚点时，优先拆掉阻塞它的前序 trip 链，而不是只拆晚点节点本身。** 这比现有 `actual_late_remove` 更贴因果，因为你们现在的晚点不是节点本身坏，而是前序占车坏。fileciteturn14file0fileciteturn17file0fileciteturn25file0

落地上，我建议做三个小改动，而不是一口气大修。第一，在 `scheduler.py` 里给 EV 候选增加一个**仅用于搜索评分的稀缺保留项**：如果某个 spec 是非绿区、或绿区但 `latest_min >= 960` 且可接受 post-16 fuel，而当前仍有“必须在 16:00 前由 EV 服务的绿区关键节点”未排，那么让 E1/E2 去执行这条 spec 时，在 `scheduling_selection_score` 里加一个小的 heuristic surcharge；F1 不加。第二，在 `operators.py` 新增一个 `blocking_chain_remove`：对最严重 Type B 晚点 trip，找到同一物理车在它之前的 1-2 条 trip，优先移除那些“可被燃油接管”的前序节点，而不是只移除晚点节点。第三，在 `scheduler_local_search.py` 加一个很窄的 swap：尝试把 pre-16 的非绿区 E1/E2 trip 改派给 F1，再整体重排，看是否能用更低的罚金甚至更低的总成本换回绿区关键 trip 的准点。因为当前很多迟到点 fresh-start 都可准时，说明表示能力不是瓶颈，瓶颈是资源先后次序。fileciteturn20file0fileciteturn25file0fileciteturn28file0

这条路线的预期收益，是**最大迟到和晚点点数有较大机会下降，而且总成本未必会上升**。原因很简单：当前晚点主要压在绿区关键任务上，罚金已经在付；如果把少数“灵活的早间 E1 任务”让给 F1，新增的能耗/碳排/固定成本，未必大于释放 EV 后带来的罚金下降。风险在于 heuristic surcharge 设太大，会把过多工作推给 F1，导致总成本反弹；所以这条路线一定要先做成实验开关，而不是直接改正式默认。这个方向与 rich VRP/MT-TDVRPTW 里“问题专用 removal / local search”的做法也是一致的。fileciteturn12file0citeturn11search0turn13search0turn13search1

### 热点绿区局部细拆

这是我推荐的第二条线，也是比 `GREEN_E2_ADAPTIVE` 更合理的“第三候选主线”。重点不在于“把所有绿区都拆到 E2 粒度”，而在于**只对真正制造了冲突和大额迟到的绿区热点客户做局部 visit 重构**。你们自己的路线文档已经指出，第一问在第二问政策下的冲突集中于客户 `3, 6, 7, 8, 11, 12`；而当前正式第二问晚点也主要集中在 `3, 6, 7, 8, 11`。因此最自然的新 variant，不是全量 `GREEN_E2_ADAPTIVE`，而是一个小很多的 `GREEN_HOTSPOT_PARTIAL_SPLIT`。fileciteturn9file0fileciteturn14file0

我建议这个 variant 的规则做得非常克制：只对同时满足“绿区”“默认解里曾经冲突或当前正式解里贡献大额晚点”“默认节点超过 E2 容量、而在 16:00 前服务价值高”的客户细拆，而且**不要一律按 E2 容量拆到底**，而是优先采用 “若干 E2 可服务 visit + 最多一个残余 E1 visit” 的混合拆分。这样做的好处是：你不是把全部绿区都碎片化，而是只在热点客户上释放 E2 的协同能力，同时尽量保留默认拆分的复用效率。换句话说，这条线解决的是“E2 根本进不了场”的问题，但不额外放大全局同步难度。fileciteturn18file0fileciteturn30file0fileciteturn31file0

这条路线的预期收益，是**在不走向 166 节点全量细拆的前提下，降低绿区关键客户对 E1 的单点依赖**。实现成本也不高，主要改 `problem_variants.py` 和 `construct_problem2_initial_route_specs()`，再加一个新的 split mode 与对比输出即可。风险则是两类：一类是拆得太少，效果不明显；另一类是规则一旦放宽，又会滑向 `GREEN_E2_ADAPTIVE` 的老问题。所以建议第一版就用最保守的热点集合，不要一开始让所有绿区都参与。fileciteturn18file0fileciteturn6file0fileciteturn13file0

### 成本主导的 ε 档案与迟到感知搜索

这条路线不是为了解决根因，而是为了把你们已经明确提出的“成本优先，但在成本接近时更偏好更好服务质量”落成代码，而且**不改变最终推荐规则**。现在 `_is_better_formal_solution()` 已经做到了“正式 best 先比总成本，仅在精确同成本时才比总晚点”；这在正式答案上是对的，但对搜索过程来说偏硬。更稳妥的做法，是新增一个**只服务搜索、不服务最终报表**的 `elite_aux` 档案：保留若干个成本在当前 best 上方一个很小阈值内、但 `late_stop_count / max_late_min / total_late_min` 更好的零冲突可行解，并允许 ALNS 周期性从这些解重启。最终输出仍然按官方最低总成本选，不动。fileciteturn26file0fileciteturn27file0fileciteturn8file0

我会把这个阈值设得很保守，比如 `eps_abs = 150~300` 元或 `eps_rel = 0.3%` 左右，并且只允许完整覆盖、容量可行、政策冲突为 0 的解进入档案。这样做的逻辑是：第二问当前的正式 gap 不是个位数噪声，而是有结构性的；但在 ALNS 搜索中，很多“稍贵一点但 EV 配置更顺”的中间态，可能正是通往更低正式总成本的台阶。文献上，ALNS 在 rich VRP 里保留问题特定的辅助评价一直是常见做法；你们项目里也已经把 `search_score` 和正式 `total_cost` 分开了，所以继续向前走到“正式 best + 辅助 elite”是顺手的，而不是变更目标函数。fileciteturn26file0citeturn11search0turn10search1

## 结构重构的取舍

我不建议现在就做一次性 `DemandAtom -> ServiceVisit -> RouteSpec -> ScheduledRoute` 大重写。理由很直接：**当前 12 个晚点全部是 Type B，fresh-route 都能准时，这说明表达能力不是眼下第一瓶颈，资源分配与排班才是。** 在这种情况下，先大重构，收益未必比定向改 scheduler/ALNS 来得高。fileciteturn14file0fileciteturn17file0

但这不等于“四层结构完全没价值”。如果前两条路线跑完后，你们仍然觉得热点客户的局部拆分/重构不够顺手，那我建议上一个**最小可落地版本**，而不是全仓重构。这个 MVP 可以这样做：`DemandAtom` 直接沿用现有 `service_nodes`；新增一个轻量 `ServiceVisit`，只在 Problem 2 的热点客户局部细拆时生成；`RouteSpec` 从“node_id 元组”升级为“visit_id 元组 + allowed_vehicle_type_ids + green_critical 标记”；`ScheduledRoute` 仍然复用现有 `Route`/`Solution` 输出，不动 `travel_time.py`、`cost.py` 和导出层。这样你们只是把“局部 visit 重构”显式化了，而不是把整个求解器翻掉。fileciteturn22file0fileciteturn20file0fileciteturn6file0

这类“先把 trip/visit 层抽薄，再逐步增强”的节奏，也更接近近年 multi-trip 文献的实务路线：很多工作确实会走向 trip-based set partitioning 或更清晰的 route/trip 分层，但那通常发生在**已经确认‘表示层’是瓶颈**之后，而不是一开始就因为代码美观去重写。对你们当前仓库，我认为这一步最多算“第二阶段工程清理”，还不应排在本轮优化最前面。citeturn13search1turn13search4turn13search8

## 优先实现建议

如果现在只允许我给一个明确优先级，我的建议是：

**先做“EV 资源保留 + 阻塞链重排”，再做“热点绿区局部细拆”，最后再补“ε 档案式迟到感知搜索”。** 这三个动作里，第一条最贴合当前已审计出的主因，因为当前晚点本质上是可行 trip 被排班挤晚；第二条是在第一条还不够时，给热点绿区客户额外释放 E2 协同空间；第三条则是把“成本优先但服务质量感知”更稳妥地嵌入搜索，而不碰正式目标。fileciteturn14file0fileciteturn17file0fileciteturn26file0

换句话说，我当前最不建议的两件事，是：其一，继续把主要精力放在 fuel-conflict 专用算子上，因为它们并没有对准当前 11 个 E1 级联晚点这个主战场；其二，继续把所有绿区客户都往 `GREEN_E2_ADAPTIVE` 方向推，因为现有正式结果已经显示那条线的主要代价不在路程，而在物理车辆数和时间窗罚金上。围绕题面“总配送成本最低”这个唯一正式目标，最有希望的下一步不是更激进，而是**更准确地把稀缺 EV 留给真正必须抢 EV 的任务**。fileciteturn14file0fileciteturn13file0fileciteturn31file0fileciteturn32file0