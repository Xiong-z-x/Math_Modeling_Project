# 第三问动态事件响应结果摘要

> 状态：2026-04-26 当前正式第三问情景结果。题面没有给具体动态事件数据，以下四组均为代表性“情景假设”，用于展示实时响应策略。当前阶段不再进行长时间全量重跑，论文写作以本文件、完整收官母稿 `docs/results/problem3_modeling_and_solution_closeout.md` 和已生成的 `outputs/problem3/` 结果为准。

## 1. 题意边界

第三问要求处理配送过程中可能出现的订单取消、新增订单、配送地址变更和时间窗调整，并设计能够实时响应和调整路径的动态调度策略。原题没有给出事件时刻、订单编号、客户编号、新增订单坐标、需求或新时间窗，因此本项目不虚构官方数据，而是构造可复现的代表性情景。

主线继承第二问绿色限行政策，以 `outputs/problem2/` 中 `DEFAULT_SPLIT` 为基准。若燃油车在 `[480,960)` 服务绿色区客户，则视为硬政策冲突。官方成本仍为固定成本、能源成本、碳排成本和软时间窗罚金；路线变化规模只作为动态响应辅助指标。

## 2. 动态响应策略

实现采用事件驱动滚动时域：

1. 在事件时刻生成快照。
2. 锁定已经完成和已经出发的趟次。
3. 只对未发车未来趟次和新增需求构造残余子问题。
4. 先做稳定性优先的快速修复，再运行轻量 ALNS 作为候选。
5. 用“官方成本 + 辅助稳定性评分”选择响应方案，但输出中单独报告官方成本和路线扰动，不把稳定性惩罚写成题面成本。

实现中特别保留货物物理状态：已经出发的车辆不能凭空接新增订单，已在车上的未送达货物也不能无条件转移给其他车辆。

对第三问四类突发事件的正面处理规则如下：

- **订单取消**：若取消节点所在趟次尚未发车，则从未装车需求池删除并重算后续趟次；若车辆已出发，则只取消服务动作，不默认减少车载重量，除非模型显式安排回库卸货。
- **新增订单**：新增货物只能分配给尚未发车趟次、已回库车辆的后续趟次或新增趟次；若新增点没有距离矩阵，则使用既有客户点代理并标注为情景假设。
- **地址变更**：在无新道路数据时不虚构坐标间距离，改用既有客户点作为新地址代理；变更后重新检查容量、时变行驶时间和绿色政策。
- **时间窗调整**：更新对应节点软时间窗，保留已执行事实，对未发车部分做局部重插入或轻量 ALNS，并用迟到罚金反映服务质量变化。

## 2.1 数学模型

令事件发生时刻为 \(t_e\)，原计划为 \(X^0\)，动态调整后方案为 \(X\)。在 \(t_e\) 处将服务集合划分为：

\[
N = N^{done}(t_e) \cup N^{lock}(t_e) \cup N^{free}(t_e)
\]

其中 \(N^{done}\) 为已完成服务，\(N^{lock}\) 为已出发车辆上的锁定服务，\(N^{free}\) 为未发车、可调整的未来服务。若发生取消、新增、地址变更或时间窗调整事件，则只更新 \(N^{free}\) 及其派生集合，不改变 \(N^{done}\) 和 \(N^{lock}\)。

官方成本目标保持为：

\[
\min C(X)=C_{fixed}(X)+C_{energy}(X)+C_{carbon}(X)+C_{tw}(X)
\]

其中 \(C_{tw}\) 为软时间窗等待/迟到罚金。动态响应另外报告稳定性辅助指标：

\[
D(X,X^0)=\alpha n_{change}+\beta n_{vehicle}+\gamma n_{edge}
\]

这里 \(n_{change}\) 为改变服务节点数，\(n_{vehicle}\) 为换车节点数，\(n_{edge}\) 为原连续服务边被破坏的数量。该项只用于候选方案选择和论文解释，不计入题面官方成本。

正式筛选采用：

\[
\text{hard feasible} \rightarrow \min \left(C(X)+D(X,X^0)\right)
\]

并在结果表中分别列出 \(C(X)\) 与路线扰动，避免把辅助稳定性包装成官方成本。

核心约束包括：

\[
\sum_{k,r} y_{ikr}=1,\quad \forall i\in N\setminus N^{cancel}
\]

\[
\sum_{i\in r} q_i \le Q_k,\quad \sum_{i\in r} v_i \le V_k
\]

\[
dep_{k,r+1}\ge ret_{k,r}
\]

\[
\text{fuel}(k)\land green(i)\land arr_i\in[480,960) \Rightarrow \text{infeasible}
\]

没有道路几何数据，因此绿色政策只检查“燃油车是否在限行时段服务绿色客户”，不声称检测车辆路径是否穿越绿色区。

本问的可解释创新点是把动态调度拆成两层：第一层保证题面硬事实和物理事实，包括服务覆盖、容量、车辆时间链、绿色政策和货物不可瞬移；第二层在可行方案中比较官方成本与稳定性辅助指标。这样既避免把“路线扰动惩罚”伪装成官方成本，又能体现实时调度中驾驶员、客户和运营系统不希望大幅改派的现实需求。

从算法角度看，最终采用“事件触发快照 + 事实冻结 + 残余池修复 + 短预算候选优化 + 多情景评估”。该路线比全量重跑更符合实时响应，也比纯规则修补更有优化空间；若后续继续拔高，可把当前代理情景扩展为多事件滚动仿真，但不建议在论文主线中声称已获得全局最优。

## 3. 命令与输出

正式输出目录：`outputs/problem3/`

推荐复现命令：

```powershell
python problems/problem3.py --iterations 8 --remove-count 4 --seed 20260426 --output-dir outputs/problem3 --no-plots
```

说明：PNG 图表已在先前完整输出中生成并保留；最终 CSV/JSON 用上面的无绘图命令刷新，以避免长时间绘图/进程超时干扰。

## 4. 情景结果

情景数据设定遵循两个原则：第一，题面没有给官方动态记录，因此事件时刻和扰动对象均写作“代表性情景假设”；第二，新增订单和地址变更不创建虚构道路距离，只映射到既有客户点或既有绿区客户代理点。四个情景覆盖了题面列出的四类事件，能够正面回答“给出一个或者几个突发事件下的车辆调度策略”的要求。

| 情景 | 事件 | 动态总成本 | 相对基准 | 政策冲突 | 迟到点 / 最大迟到 | 调整节点 | 换车节点 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cancel_future_order_1030` | 10:30 取消尚未发车服务节点 | `48711.28` | `-528.51` | `0` | `12 / 129.44` | `1` | `0` |
| `new_green_order_1330` | 13:30 新增绿区代理订单 | `49237.36` | `-2.42` | `0` | `12 / 129.44` | `2` | `0` |
| `time_window_pull_forward_1500` | 15:00 未来节点时间窗提前 | `49263.35` | `+23.57` | `0` | `13 / 129.44` | `1` | `0` |
| `address_change_proxy_1200` | 12:00 地址变更为既有客户代理点 | `49207.47` | `-32.31` | `0` | `12 / 129.44` | `2` | `0` |

四个情景均满足完整覆盖、容量可行、物理车辆时间链可行和零政策冲突。

案例展开数据见 `outputs/problem3/case_validation_summary.csv`。其中新增绿区订单被插入 `E1-004/T0038`，到达新增节点 `149` 的时刻为 16:27 且无迟到；时间窗提前案例中节点 `112` 新增迟到 `28.28 min`，对应罚金增加 `23.57`；地址变更案例中节点 `17` 仍由 `E1-008/T0026` 服务，到达时刻由 14:09 提前至 13:44。完整论文式解释见 `docs/results/problem3_modeling_and_solution_closeout.md` 第 20 节。

## 5. 结果解释

- 取消订单降低成本，主要来自取消未发车服务节点后的路线成本减少。
- 新增绿区订单没有增加政策冲突，且因为该代理点可吸收原路线等待时间，官方总成本略低于基准。这不是说“新增订单天然降成本”，而是软时间窗等待罚金与新增服务时间相互抵消后的特定情景结果。
- 时间窗提前增加一个迟到点和少量罚金，说明该事件对服务质量有真实压力。
- 地址变更使用既有客户点代理，不生成新距离矩阵；该情景因代理点距离结构更近，成本略降。

## 6. 验证

已验证：

- `python -m pytest tests/test_dynamic.py tests/test_scheduler.py tests/test_problem3_engine.py tests/test_problem3.py -q`
  - `14 passed`
- `python problems/problem3.py --iterations 8 --remove-count 4 --seed 20260426 --output-dir outputs/problem3 --no-plots`
  - 四情景均可行，`feasible_scenario_count = 4`
- 每个情景的 `problem2_policy_conflicts.csv` 均无 true conflict 行。
- 每个情景的 `dynamic_diagnosis.csv` 均显示物理时间链可行。

## 7. 局限

- 事件数据为情景假设，不是官方附件数据。
- 地址变更和新增订单使用既有客户点作为代理，避免虚构道路距离。
- 当前正式选择偏向稳定修复；轻量 ALNS 作为候选保留，但若它导致过大的路线扰动且成本收益不足，不作为最终响应。
- 尚未建模中途换装、路边转运或车辆在客户间弧上的精确位置插值。

## 8. 方法依据与写作口径

动态车辆路径问题通常需要在执行过程中根据新信息重定义路线，Pillac 等对 DVRP 的综述明确把信息随时间演化作为核心特征。本文的事件触发滚动时域框架与这一分类一致。项目中的时变行驶时间继续采用分段速度积分，并保持 FIFO 思想，这与 Ichoua、Gendreau 和 Potvin 的时变行驶时间模型一致。局部候选优化使用轻量 ALNS 的原因，是 Ropke 和 Pisinger 的 ALNS 框架已证明多算子自适应搜索适合带时间窗路径问题。由于题面没有给动态概率分布，本文没有采用大规模随机预测，而只借鉴 Bent 和 Van Hentenryck 的情景规划思想，构造可复现代表性情景进行响应评估。

可在论文中这样表述：在题面未给定具体动态事件数据的前提下，本文以第二问最优绿色限行方案为基准，构造订单取消、新增订单、地址变更和时间窗调整四类代表性扰动情景，采用事件驱动滚动时域算法进行响应，并对每个情景输出调整后成本、政策冲突、迟到水平和路线扰动。不可写成“官方附件给出了这些事件”，也不可把辅助稳定性评分写成题面官方成本。

主要参考依据：

- Pillac, Gendreau, Gueret and Medaglia, *A review of dynamic vehicle routing problems*, European Journal of Operational Research, DOI `10.1016/j.ejor.2012.08.015`。
- Ichoua, Gendreau and Potvin, *Vehicle dispatching with time-dependent travel times*, European Journal of Operational Research, DOI `10.1016/S0377-2217(02)00147-9`。
- Ropke and Pisinger, *An Adaptive Large Neighborhood Search Heuristic for the Pickup and Delivery Problem with Time Windows*, Transportation Science, DOI `10.1287/trsc.1050.0135`。
- Bent and Van Hentenryck, *Scenario-Based Planning for Partially Dynamic Vehicle Routing with Stochastic Customers*, Operations Research, DOI `10.1287/opre.1040.0124`。
- Blauth et al., *Vehicle routing with time-dependent travel times: Theory, practice, and benchmarks*, Discrete Optimization, DOI `10.1016/j.disopt.2024.100848`。该 2024 年开放论文说明了时变行驶时间下插入、删除和调度评估的高效实现价值，支持本文采用短预算局部响应而不是长时间全局重算。
