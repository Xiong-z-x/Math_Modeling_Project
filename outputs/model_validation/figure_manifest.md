# 模型检验图表清单与生成提示词

本清单对应 `outputs/model_validation/` 中已生成的 7 张派生图片。图表均直接使用项目输出数据，不使用外部虚构数值。

## P1-F1 第一问 ALNS 收敛与同 seed 稳定性检验图

- 文件：`outputs/model_validation/problem1_alns_convergence.png`
- 数据源：`outputs/problem1/alns_history.csv`，`outputs/problem1_cost_100_trial/alns_history.csv`
- 视觉元素：X 轴为迭代次数，Y 轴为当前最优官方总成本；两条折线分别表示 40 迭代正式运行和 100 迭代审计运行；水平虚线标出正式总成本 `48644.68`。
- 设计意图：展示第一问在同一 seed 更长迭代下没有找到更低官方总成本，用于支撑收敛稳定性。该图只能说明当前启发式运行的稳定性，不能声明全局最优。
- 建议位置：第六节“稳定性与敏感性分析”的第一问检验段。
- 生成提示词：基于 `outputs/problem1/alns_history.csv` 和 `outputs/problem1_cost_100_trial/alns_history.csv` 画双折线收敛图，横轴为 `iteration`，纵轴为 `best_cost`，标注正式成本 `48644.68`，风格简洁、适合数学建模论文。

## P1-F2 第一问残余迟到来源诊断柱线图

- 文件：`outputs/model_validation/problem1_late_diagnosis.png`
- 数据源：`outputs/problem1/late_stop_diagnosis.csv`
- 视觉元素：X 轴为迟到诊断类型 `Type A/Type B/Type C`，左 Y 轴为迟到停靠数，右 Y 轴为最大迟到分钟数；柱表示数量，折线表示每类最大迟到。
- 设计意图：说明第一问 4 个残余迟到点不是模型遗漏时间窗，而是软时间窗成本权衡下的三类来源：直达也迟到、多趟级联、路线顺序局部问题。
- 建议位置：第六节“误差分析与服务质量检验”的第一问段落。
- 生成提示词：聚合 `outputs/problem1/late_stop_diagnosis.csv` 的 `classification` 字段，绘制柱线组合图；柱为迟到停靠数，折线为 `late_min` 最大值，突出第一问残余迟到的物理来源。

## P2-F1 第一问至第二问官方成本分项迁移堆叠图

- 文件：`outputs/model_validation/problem2_cost_component_delta.png`
- 数据源：`outputs/problem1/summary.json`，`outputs/problem2/default_split/summary.json`
- 视觉元素：X 轴为 `P1` 与 `P2`，Y 轴为成本；堆叠颜色分别表示固定成本、能源成本、碳排成本和软时间窗罚金；柱顶标注总成本。
- 设计意图：量化绿色限行硬约束引入后的成本变化。第二问相对第一问总成本增加 `595.10` 元，其中固定成本和时间窗罚金上升，能源与碳排成本下降。
- 建议位置：第二问结果对比之后，或第六节“新旧方案对比”。
- 生成提示词：读取两个 `summary.json` 的 `cost_breakdown`，画 P1 与 P2 成本分项堆叠柱状图，颜色区分 `fixed_cost`、`energy_cost`、`carbon_cost`、`penalty_cost`，顶部标总成本，突出政策合规代价。

## P2-F2 第二问成本-服务质量灵敏度权衡气泡图

- 文件：`outputs/model_validation/problem2_variant_service_tradeoff.png`
- 数据源：`outputs/problem2/variant_comparison.csv`，`outputs/problem2_experiments/formal_screen_policy_ev_p500/best_feasible_by_cost.csv`
- 视觉元素：X 轴为官方总成本，Y 轴为最大迟到分钟数；颜色区分正式候选和服务质量对照方案；气泡大小映射迟到点数；标签为方案名。
- 设计意图：展示 `DEFAULT_SPLIT` 是当前官方成本最低方案；`POLICY_OPS + EV_RESERVATION_P500` 可显著降低迟到，但总成本更高，因此只能作为服务质量灵敏度对照。
- 建议位置：第六节“敏感性分析”的第二问政策与服务质量权衡段。
- 生成提示词：合并 `variant_comparison.csv` 和 `formal_screen_policy_ev_p500/best_feasible_by_cost.csv`，绘制气泡图，横轴 `total_cost`，纵轴 `max_late_min`，气泡大小为 `late_stop_count`，标注 `DEFAULT_SPLIT`、`GREEN_E2_ADAPTIVE`、`GREEN_HOTSPOT_PARTIAL`、`POLICY_OPS+P500`。

## P3-F1 第三问四类动态事件成本响应瀑布图

- 文件：`outputs/model_validation/problem3_scenario_cost_response.png`
- 数据源：`outputs/problem3/scenario_comparison.csv`
- 视觉元素：X 轴为订单取消、新增绿区订单、时间窗提前、地址变更四类事件，Y 轴为相对第二问基准的官方总成本变化；绿色表示成本下降，红色表示成本上升。
- 设计意图：说明四类事件对成本的影响方向不同。取消订单释放成本，时间窗提前增加罚金，新订单和改址结果取决于局部路线结构。
- 建议位置：第三问结果分析后，或第六节“动态情景敏感性分析”。
- 生成提示词：基于 `outputs/problem3/scenario_comparison.csv` 的 `delta_total_cost` 画柱状图，四个事件按取消、新增绿区、时间窗提前、地址变更排序，红绿配色并标注数值。

## P3-F2 第三问事件时刻-路线扰动响应气泡图

- 文件：`outputs/model_validation/problem3_event_response_bubble.png`
- 数据源：`outputs/problem3/scenario_comparison.csv`
- 视觉元素：X 轴为事件发生时刻，Y 轴为相对基准成本变化；颜色映射事件类型，气泡大小映射调整服务节点数。
- 设计意图：把动态响应的时间维度、成本维度和稳定性维度放在同一图中，强调稳定性是辅助解释指标，不是官方成本项。
- 建议位置：第六节“稳定性与敏感性分析”的第三问段。
- 生成提示词：读取 `scenario_comparison.csv`，令 `x=event_time_min/60`，`y=delta_total_cost`，颜色映射 `event_type`，大小映射 `changed_stop_count`，标注事件类型，并注明全部场景政策冲突为 0。

## ALL-F1 全题正式结果可行性检验矩阵图

- 文件：`outputs/model_validation/feasibility_validation_matrix.png`
- 数据源：`outputs/model_validation/feasibility_validation_matrix.csv`
- 视觉元素：行表示第一问正式解、第二问正式解和第三问四个情景；列表示覆盖、容量和物理车辆链；格内 `OK` 表示通过。
- 设计意图：用一张矩阵给出全题硬可行性证据，避免模型检验只停留在文字声称。
- 建议位置：第六节“可行性检验”开头。
- 生成提示词：用 `feasibility_validation_matrix.csv` 画绿色热力矩阵，行是 `P1/P2/P3 scenarios`，列是 `coverage/capacity/vehicle chain`，格内写 `OK`，标题为 `Formal-result feasibility validation matrix`。
