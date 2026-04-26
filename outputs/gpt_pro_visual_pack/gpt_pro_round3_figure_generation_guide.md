# GPT Pro 图像生成总说明与逐图提示词

本文档用于向 GPT Pro 上传 `gpt_pro_upload_pack_round3/` 后生成华中杯 A 题“城市绿色物流配送调度”论文插图。所有图必须服务于论文结论：时变速度、异构车队、软时间窗、载重相关能耗、碳排成本、绿色限行和动态事件响应。

## 一、总控提示词

请先把下面整段作为第一条消息发送给 GPT Pro，并上传本文件夹内全部 CSV。

```text
你是一名数学建模竞赛论文可视化专家，任务是为华中杯 A 题“城市绿色物流配送调度”生成论文级插图。请先读取我上传的全部 CSV 和说明文件，再逐张生成图。

项目背景：
本文研究城市绿色物流配送调度。模型不是普通 VRP，而是考虑时变速度、异构车队、软时间窗、载重相关能耗、碳排成本、绿色限行硬约束和动态事件滚动响应的综合调度模型。绿色区中心为 (0,0)，配送中心为 (20,20)。没有道路几何，路线折线只能表示访问顺序，不能声称车辆沿真实道路穿越绿色区。距离矩阵使用原始 customer_id，算法服务颗粒使用虚拟 service_node_id。

数据红线：
1. 不得修改 CSV 中任何数值。
2. 不得编造随机实验、最优性证明、道路几何、官方动态事件日志或新结果。
3. 官方成本只包含固定成本、能源成本、碳排成本和软时间窗罚金。
4. 政策冲突、EV reservation、稳定性指标、路线扰动指标只能作为检验或解释指标，不能画成官方成本项。
5. 电动车有电力碳排，不得写成零碳或零排放。
6. 时间窗为软约束，绿色限行为硬约束。
7. 第三问四个动态场景是代表性情景，不是官方附件动态数据。

视觉要求：
1. 使用中文标题、中文图例、中文坐标轴和单位，文字必须清楚可读。
2. 采用论文插图风格：白底、细网格、三到五种克制色、无装饰背景、无渐变大面积铺底。
3. 每张图只保留 2-3 个关键注释，注释必须直接支撑题目结论。
4. 对拥挤数据使用排序、分面、透明度、Top-K 或高分位标注降低噪声，但不得丢失核心结论。
5. 对精确图表优先用 Python/Matplotlib/Seaborn/Plotly 根据 CSV 直接绘制；如使用图像生成模型做版式增强，必须以程序图为底稿，不得手工估计数值。
6. 输出 300 dpi 或更高，优先横版 16:9 或论文适配的 4:3；字体建议 Noto Sans CJK / Microsoft YaHei / SimHei。
7. 每次生成前先给出“数据字段核对清单”；生成后进行“数值一致性自检”，列出图中标注值与 CSV 对应字段。

目标风格：
参考数学建模高水平论文的图表习惯：空间分布图回答数据特征，机制图回答模型为什么这样建，方案对照图回答每一问结论，热力图/矩阵图回答约束可行性，时间轴图回答动态响应逻辑。不要做宣传海报。
```

## 二、推荐整体图序

论文当前建议保留 10 张正文图。若版面紧张，优先保留图 1、图 2、图 3、图 5、图 7、图 9、图 10；图 4、图 6、图 8 可转入附录或支撑材料。

## 三、逐图说明与生成提示

### 图 1 订单聚合前后的拓扑流向图

**放置位置**：数据预处理章节，订单聚合与拆分规则之后。

**数据文件**：
- `data/02_order_aggregation_split_summary.csv`
- `data/02_customer_split_detail.csv`

**视觉元素**：
- 主图：Sankey / alluvial flow。
- 左侧节点：原始订单 `raw_orders=2169`。
- 中间节点：有效客户 `active_customers=88`、发生拆分客户 `split_customers=36`、绿色区客户 `active_green_customers=12`。
- 右侧节点：虚拟服务节点 `virtual_service_nodes=148`、绿色区服务节点 `green_service_nodes=19`。
- 线宽：节点数量或映射关系强度。
- 颜色：普通需求灰蓝，绿色区节点绿色，拆分节点橙色。
- 可加小插图：从 `02_customer_split_detail.csv` 选 `split_count` 最高的 Top 8 客户，画横向条形图。

**设计意图**：
该图解释为什么求解层使用虚拟 `service_node_id`，同时保留距离矩阵的原始 `customer_id`。评委应一眼看到：2169 条订单被压缩为 88 个有效客户，再由装载限制拆成 148 个服务节点；绿色区从 12 个真实客户扩展为 19 个服务节点，这是第二问限行建模的直接数据基础。

**GPT Pro 逐图提示词**：

```text
请使用 data/02_order_aggregation_split_summary.csv 和 data/02_customer_split_detail.csv 生成“图1 订单聚合前后的拓扑流向图”。

绘图要求：
1. 主图使用 Sankey / alluvial flow，展示 raw_orders=2169 -> active_customers=88 -> virtual_service_nodes=148 的数据加工链路。
2. 同图标出 active_green_customers=12、green_service_nodes=19、split_customers=36。绿色区相关节点用绿色，拆分相关节点用橙色，普通节点用灰蓝色。
3. 在右下角加入一个小型横向条形图，展示 split_count 最高的 Top 8 客户；横轴为“拆分服务节点数”，纵轴为“customer_id”。
4. 图内仅放 2 个注释：
   - “2169 条订单压缩为 88 个有效客户”
   - “36 个客户触发装载拆分，形成 148 个服务节点”
5. 标题使用中文：“订单聚合与服务节点拆分流程”。
6. 不要出现英文标题，不要使用装饰背景，不要把虚拟服务节点误写成新增真实客户。
7. 生成后列出你使用的 CSV 字段和图中标注数值，确认没有修改任何 CSV 数值。
```

### 图 2 客户需求空间分布核密度图

**放置位置**：数据预处理章节，空间数据与绿色区识别之后。

**数据文件**：
- `data/01_customer_spatial_demand.csv`
- `data/01_green_zone_boundary.csv`
- `data/01_key_points.csv`

**视觉元素**：
- X 轴：`x_km`，单位 km。
- Y 轴：`y_km`，单位 km。
- 背景：按 `total_weight_kg` 或 `demand_index_0_100` 加权的二维核密度。
- 气泡：客户点，大小为 `suggested_bubble_area`，颜色区分 `is_green_zone`。
- 边界：绿色区圆形边界，来自 `01_green_zone_boundary.csv`。
- 关键点：绿色区中心 `(0,0)` 与配送中心 `(20,20)`，来自 `01_key_points.csv`。

**设计意图**：
该图回答“需求在哪里、绿色区在哪里、仓库在哪里”。它应强调绿色区中心与配送中心不同，绿色区判定来自客户坐标到 `(0,0)` 的距离，而不是道路穿越检测。

**GPT Pro 逐图提示词**：

```text
请使用 data/01_customer_spatial_demand.csv、data/01_green_zone_boundary.csv、data/01_key_points.csv 生成“图2 客户需求空间分布核密度图”。

绘图要求：
1. 横轴为 x 坐标 / km，纵轴为 y 坐标 / km，保持等比例坐标。
2. 使用 total_weight_kg 或 demand_index_0_100 做加权二维核密度背景；颜色从浅灰到蓝绿色，避免浓重装饰色。
3. 客户点用气泡叠加：气泡大小映射 suggested_bubble_area，颜色区分 is_green_zone；绿色区客户用绿色描边。
4. 用 data/01_green_zone_boundary.csv 绘制绿色区边界；标注绿色区中心 (0,0)。
5. 用 data/01_key_points.csv 标注配送中心 (20,20)。
6. 仅保留 2 个注释：
   - “绿色区中心 (0,0)”
   - “配送中心 (20,20)，与绿色区中心分离”
7. 禁止把折线或点位解释成真实道路；本图只展示空间分布和绿色区判定。
8. 生成后列出客户数、绿色区客户数和坐标字段来源。
```

### 图 3 时变路网下车速-能耗时空立方体图

**放置位置**：模型建立章节，时变速度与载重能耗模型之后。

**数据文件**：
- `data/03_speed_energy_profile.csv`

**视觉元素**：
- X 轴：时间段 `start_time-end_time` 或 `period_label`。
- Y 轴：载重率 `load_ratio`。
- Z 轴或颜色：单位里程能耗。
- 分面：燃油车 `fuel_expected_l_per_100km` 与电动车 `ev_expected_kwh_per_100km`。
- 额外标注：`speed_mu_kmh` 表示平均车速，`speed_sigma_kmh` 表示波动。

**设计意图**：
该图把“时变速度 + 载重相关能耗 + Jensen 修正”的机制可视化，说明本文不是静态距离成本 VRP。它展示同一路段能耗随出发时段和载重率变化，因此车辆调度的时间安排会改变能源与碳排成本。

**GPT Pro 逐图提示词**：

```text
请使用 data/03_speed_energy_profile.csv 生成“图3 时变路网下车速-能耗时空立方体图”。

绘图要求：
1. 采用双分面 3D surface 或 heatmap：左图为燃油车，右图为电动车。
2. 横轴为时间段，使用 start_time-end_time 或 period_label；纵轴为 load_ratio；颜色或 Z 轴为单位里程能耗。
3. 燃油车色标单位为 L/100km，字段 fuel_expected_l_per_100km；电动车色标单位为 kWh/100km，字段 ev_expected_kwh_per_100km。
4. 在每个时段上方用小标签标注 speed_mu_kmh，格式如“均速 9.8 km/h”。
5. 只保留 2 个结论注释：
   - “拥堵时段低速放大单位能耗”
   - “高载重率提高燃油与电耗”
6. 标题：“时变速度与载重率耦合下的单位能耗曲面”。
7. 本图是模型机制图，数值必须来自 CSV；不得写成仿真结果或独立实验。
8. 不得把电动车写成零碳排，电耗后续仍参与电力碳排核算。
```

### 图 4 第一问静态调度空间路径与迟到风险双编码图

**放置位置**：第一问结果表之后。

**数据文件**：
- `data/04_route_visual_arcs_p1_p2.csv`
- `data/01_customer_spatial_demand.csv`
- `data/01_green_zone_boundary.csv`

**视觉元素**：
- 过滤：`problem=problem1`。
- X/Y 轴：客户坐标，单位 km，等比例。
- 弧线：`from_x_km,from_y_km` 到 `to_x_km,to_y_km`，仅表示访问顺序。
- 颜色：`vehicle_type`，E1 与 F1 区分。
- 透明度：降低普通弧线噪声。
- 线宽：`trip_weight_kg` 或 `trip_distance_km`。
- 红色描边：`trip_max_late_min > 0` 的路线。
- 气泡：客户需求规模。

**设计意图**：
该图展示第一问静态方案的空间覆盖、车辆异构使用和迟到风险位置。它不追求把 116 条路线全部讲清，而是用透明度和迟到描边说明：方案覆盖全域需求，少量迟到来自软时间窗权衡。

**GPT Pro 逐图提示词**：

```text
请使用 data/04_route_visual_arcs_p1_p2.csv、data/01_customer_spatial_demand.csv、data/01_green_zone_boundary.csv 生成“图4 第一问静态调度空间路径与迟到风险双编码图”。

绘图要求：
1. 仅筛选 route arcs 中 problem=problem1 的记录。
2. 坐标轴为 x/km 与 y/km，保持等比例；叠加客户需求气泡和绿色区边界。
3. 路线弧线只表示访问顺序，不能表示真实道路。请在图注写明“折线仅表示访问顺序”。
4. 弧线颜色映射 vehicle_type：E1 用蓝绿色，F1 用深灰或紫灰；透明度 0.15-0.30。
5. 线宽映射 trip_weight_kg 或 trip_distance_km；迟到路线 trip_max_late_min>0 用红色外描边。
6. 图内标注第一问关键结果：总成本 48644.68；物理车辆 E1:10,F1:33；迟到点 4，最大迟到 31.60 min。
7. 只保留 2 个解释注释：全域覆盖、少量迟到为软时间窗权衡。
8. 禁止声称路线穿越绿色区或沿道路行驶。
```

### 图 5 绿色限行政策前后的成本-碳排-车队结构迁移图

**放置位置**：第二问模型与结果章节，P1/P2 对比表之后。

**数据文件**：
- `data/05_policy_cost_carbon_shift.csv`

**视觉元素**：
- 左侧：P1 与 P2 的官方成本堆叠柱，分解为 `fixed_cost`、`energy_cost`、`carbon_cost`、`time_window_penalty`。
- 中部：成本差箭头，标注 `49239.78 - 48644.68 = +595.10`。
- 右侧：碳排柱或折线，`carbon_kg` 从 8337.49 到 8156.49。
- 下方小图：物理车辆结构 `E1:10,F1:33` 到 `E1:10,F1:35`。
- 颜色：固定成本灰、能源蓝、碳排绿、罚金橙。

**设计意图**：
该图直接回答绿色限行政策对调度方案的影响：P2 在政策冲突为 0 的硬合规条件下，官方成本小幅增加，同时碳排下降。它把“政策合规不是成本项”与“政策改变车队和时序结构”区分开。

**GPT Pro 逐图提示词**：

```text
请使用 data/05_policy_cost_carbon_shift.csv 生成“图5 绿色限行政策前后的成本-碳排-车队结构迁移图”。

绘图要求：
1. 主图为两根官方成本堆叠柱：problem1_no_policy_baseline 与 problem2_green_policy_formal。
2. 成本构成只允许使用 fixed_cost、energy_cost、carbon_cost、time_window_penalty 四项。
3. 在两柱之间标注成本变化：“+595.10”。
4. 右侧用小柱图或折线展示 carbon_kg：8337.49 kg -> 8156.49 kg。
5. 下方用简洁车辆图标或横向堆叠条展示 physical_vehicle_usage：E1:10,F1:33 -> E1:10,F1:35。
6. 标注 P2 policy_conflict_count=0，但不要把它放入成本堆叠。
7. 图题：“绿色限行引起的成本、碳排与车队结构迁移”。
8. 生成后核对总成本、碳排、车辆结构三组数值。
```

### 图 6 绿色配送区服务时刻与车型合规热力图

**放置位置**：第二问结果解释或模型检验章节，绿色限行可行性说明处。

**数据文件**：
- `data/05_green_service_policy_timeline.csv`

**视觉元素**：
- X 轴：服务到达时间 `arrival_min` 转换为 HH:MM。
- Y 轴：`service_node_id` 或 `customer_id`，建议仅显示绿色区服务节点。
- 背景阴影：限行时段 `[08:00,16:00)`。
- 点颜色：`vehicle_type`；点形状：是否燃油车 `is_fuel_vehicle`。
- 红色叉号：`policy_conflict=True`，正式 P2 应为 0。
- 分面：`case`，可对比 `problem1_screened_under_p2_policy` 与 `problem2_formal`。

**设计意图**：
该图证明绿色限行作为硬约束被显式处理。它应表达“服务发生在绿色区内何时由何种车型完成”，而不是声称检测道路穿越绿色区。

**GPT Pro 逐图提示词**：

```text
请使用 data/05_green_service_policy_timeline.csv 生成“图6 绿色配送区服务时刻与车型合规热力图”。

绘图要求：
1. 筛选 is_green_zone=True 的服务记录。
2. 横轴为到达时间 arrival_min，转换成 HH:MM；纵轴为 service_node_id，按到达时间排序。
3. 用浅绿色背景标出绿色限行关注时段 08:00-16:00。
4. 点颜色映射 vehicle_type，点形状映射 is_fuel_vehicle。
5. 若 policy_conflict=True，用红色叉号叠加；正式第二问应清楚显示 policy_conflict_count=0。
6. 分面展示 case，优先比较“第一问方案按第二问政策筛查”和“第二问正式方案”。
7. 图内只保留 2 个注释：
   - “限行硬约束：绿色区内燃油车服务受控”
   - “第二问正式方案政策冲突 0”
8. 禁止把服务点合规解释成道路穿越合规。
```

### 图 7 第二问候选方案成本-准时性 Pareto 权衡图

**放置位置**：第二问灵敏度与方案权衡分析处。

**数据文件**：
- `data/06_problem2_candidate_tradeoff.csv`

**视觉元素**：
- X 轴：`total_cost`。
- Y 轴：`max_late_min`，必要时使用截断轴或对数辅助网格，但需标明。
- 点大小：`late_stop_count`。
- 点颜色：`case_type`，正式候选与服务质量对照区分。
- 标注：`default_split`、`policy_ops_ev_reservation_p500`。
- 可用虚线连接“成本优先硬合规方案”与“服务质量对照方案”。

**设计意图**：
该图把第二问写成“最低成本硬合规推荐 + 服务质量对照方案的 Pareto 权衡”。它避免把服务质量方案误写为正式推荐，同时展示团队对管理取舍的解释能力。

**GPT Pro 逐图提示词**：

```text
请使用 data/06_problem2_candidate_tradeoff.csv 生成“图7 第二问候选方案成本-准时性 Pareto 权衡图”。

绘图要求：
1. 横轴为 official total_cost，纵轴为 max_late_min；点大小为 late_stop_count。
2. 点颜色按 case_type 区分 formal_candidate 与 service_quality_sensitivity。
3. 强调两个点：
   - default_split：成本 49239.78，政策冲突 0，迟到点 12，最大迟到 129.44 min，标注为“正式推荐：最低成本硬合规”
   - policy_ops_ev_reservation_p500：成本 50770.72，政策冲突 0，迟到点 2，最大迟到 5.93 min，标注为“服务质量对照：灵敏度分析”
4. 不要把服务质量对照方案写成官方推荐，不要把 EV reservation 写入成本项。
5. 使用清爽散点图，配 Pareto 方向箭头：“成本下降”和“准时性改善”。
6. 图题：“绿色限行下成本与服务质量的候选方案权衡”。
7. 生成后核对四个候选方案的 total_cost、late_stop_count、max_late_min。
```

### 图 8 基于事实冻结的滚动时域车辆时间轴图

**放置位置**：第三问动态事件响应模型章节，滚动修复算法流程之后。

**数据文件**：
- `data/problem3_frozen_segments/cancel_future_order_1030_frozen_segments.csv`
- `data/problem3_frozen_segments/new_green_order_1330_frozen_segments.csv`
- `data/problem3_frozen_segments/time_window_pull_forward_1500_frozen_segments.csv`
- `data/problem3_frozen_segments/address_change_proxy_1200_frozen_segments.csv`
- 辅助：`data/07_problem3_event_response.csv`

**视觉元素**：
- X 轴：时间，分钟或 HH:MM。
- Y 轴：情景或受影响车辆。
- 纵向线：事件发生时刻 `event_time_min`。
- 时间条：`depart_min` 到 `return_min`。
- 颜色：事件前已冻结、事件后可修复、受影响路线。
- 标注：四个代表性情景的事件时间。

**设计意图**：
该图解释第三问的动态调度不是全盘重排，而是在事实冻结基础上滚动修复。它突出“已执行部分不被回滚、未执行部分局部调整”的物理可行性。

**GPT Pro 逐图提示词**：

```text
请使用 data/problem3_frozen_segments/ 下四个 frozen_segments.csv 和 data/07_problem3_event_response.csv 生成“图8 基于事实冻结的滚动时域车辆时间轴图”。

绘图要求：
1. 每个情景做一个横向小面板，横轴为时间 HH:MM。
2. 从 frozen_segments.csv 中读取 trip_id、physical_vehicle_id、vehicle_type、depart_min、return_min。
3. 在每个面板画车辆任务条，事件时刻用垂直虚线标出：
   - cancel_future_order_1030：10:30
   - new_green_order_1330：13:30
   - time_window_pull_forward_1500：15:00
   - address_change_proxy_1200：12:00
4. 事件线左侧任务段用灰色表示事实冻结，事件线右侧任务段用蓝绿色表示可修复区间；受影响车辆或路线用橙色描边。
5. 仅标注四个事件类型和“已执行部分冻结”。
6. 不要虚构未在 frozen_segments.csv 出现的车辆轨迹；如果字段不足，只展示文件内可确认的任务条。
7. 图题：“事实冻结约束下的动态事件滚动修复时间轴”。
```

### 图 9 第三问动态事件响应成本-扰动矩阵图

**放置位置**：第三问结果表之后。

**数据文件**：
- `data/07_problem3_event_response.csv`
- `data/07_problem3_route_change_counts.csv`

**视觉元素**：
- 左侧：四个情景的 `dynamic_total_cost` 与 `delta_total_cost`。
- 中部：硬可行性列，`policy_conflict_count`、`is_complete`、`is_capacity_feasible`、`physical_time_chain_feasible`。
- 右侧：扰动列，`changed_stop_count`、`vehicle_reassignment_count`；可用小型堆叠条补充 `route_change_counts`。
- 色彩：成本下降绿色，成本上升橙色；硬可行性通过绿色对勾。

**设计意图**：
该图集中回答第三问：四类事件都能在硬可行条件下修复，政策冲突均为 0，路线扰动规模小。成本变化不是唯一评价，稳定性与硬约束同样重要。

**GPT Pro 逐图提示词**：

```text
请使用 data/07_problem3_event_response.csv 和 data/07_problem3_route_change_counts.csv 生成“图9 第三问动态事件响应成本-扰动矩阵图”。

绘图要求：
1. 行为四个 scenario：
   cancel_future_order_1030、new_green_order_1330、time_window_pull_forward_1500、address_change_proxy_1200。
2. 列分为三组：
   - 成本响应：dynamic_total_cost、delta_total_cost
   - 硬可行性：policy_conflict_count、is_complete、is_capacity_feasible、physical_time_chain_feasible
   - 稳定性：changed_stop_count、vehicle_reassignment_count
3. 成本变化用发散色条：负值绿色，正值橙色；硬可行性用绿色对勾或 0/1 标记；扰动规模用小条形。
4. 在右侧加入 route_change_counts 的小型堆叠条，展示 unchanged、locked_unchanged、retimed、cancelled、sequence_changed 等变化类型。
5. 图中标注四个正式动态成本：
   48711.28、49237.36、49263.35、49207.47。
6. 注释仅保留：
   - “四个情景均硬可行且政策冲突 0”
   - “扰动集中在少量服务节点”
7. 明确写作“代表性动态情景”，不要写成官方附件动态数据。
```

### 图 10 全题模型可信性检验矩阵图

**放置位置**：模型检验章节开头或结尾。

**数据文件**：
- `data/08_feasibility_validation_matrix.csv`

**视觉元素**：
- 行：P1、P2、四个 P3 情景。
- 列：覆盖可行、容量可行、物理车辆时间链可行、政策冲突数、迟到点数、最大迟到。
- 图形编码：硬约束通过为绿色对勾；政策冲突 0 为绿色；软时间窗迟到用橙色强度，不画成不可行。
- 右侧数值列：`late_stop_count` 与 `max_late_min`。

**设计意图**：
该图把论文的可信性从“有结果”提升为“结果通过关键约束核验”。它明确区分硬约束和软约束，避免把软时间窗迟到误判为模型不可行。

**GPT Pro 逐图提示词**：

```text
请使用 data/08_feasibility_validation_matrix.csv 生成“图10 全题模型可信性检验矩阵图”。

绘图要求：
1. 行为 case，列为 coverage_feasible、capacity_feasible、physical_chain_feasible、policy_conflict_count、late_stop_count、max_late_min。
2. coverage_feasible、capacity_feasible、physical_chain_feasible 为 True 时使用绿色对勾。
3. policy_conflict_count 为 0 时使用绿色“0”；P1 政策不适用时用灰色“—”。
4. late_stop_count 与 max_late_min 用橙色渐变或数值条表示，图注写明“时间窗为软约束”。
5. 图题：“全题关键约束可行性与服务风险检验矩阵”。
6. 图中只保留 2 个结论注释：
   - “硬约束全部通过”
   - “迟到作为软时间窗风险单独报告”
7. 不要把迟到点画成不可行，也不要把政策冲突计入成本。
```

## 四、不建议生成的图

1. 不生成“真实道路路径图”。项目没有道路几何，所有折线只能解释为访问顺序。
2. 不生成“车辆穿越绿色区检测图”。第二问只判断绿色区客户服务与车型/时段合规。
3. 不生成“电动车零排放宣传图”。电动车耗电仍有碳排。
4. 不生成“随机种子稳定性箱线图”。除非项目已有真实多次运行数据，否则容易构成虚构实验。
5. 不生成“算法最优性证明图”。当前方案是高质量可行启发式结果，不是全局最优证明。
6. 不生成“官方动态事件日志图”。第三问四类情景为代表性动态扰动情景。

## 五、让数据更好看的合法方法

可以使用：
- 按成本、迟到、扰动数排序。
- 用分面减少一图内变量数量。
- 对路线弧线使用低透明度，突出迟到或受影响路线。
- 标注 Top-K 或高分位点，但图注必须说明筛选规则。
- 使用管理含义标签，如“成本优先硬合规”“服务质量对照”，但不改变方案身份。
- 将机制图标注为“模型机制图”或“理论曲线”，不得冒充实验结果。

不可以使用：
- 修改 CSV 数值让图更漂亮。
- 补造缺失列。
- 将局部扰动指标加入官方成本。
- 把服务质量对照方案写成第二问正式推荐。

## 六、联网资料提炼

本提示词结构参考了 OpenAI 官方提示词建议：把指令放在前部、用分隔符区分上下文、明确输出格式、减少含糊描述；图像生成侧采用“明确约束、逐步迭代、控制文字与版式”的思路。OpenAI 图像文档也提醒复杂图像存在文字和布局控制风险，因此本包要求对数据图优先用 Python 直接绘制，并在生成后核对数值。

数学建模格式侧，本项目仍服从华中杯正文 30 页、无正式目录、附录不受正文页数限制的要求；图表设计按“图回答问题、表支撑数值、附录承载长表和代码”的竞赛论文逻辑执行。

参考链接：
- OpenAI Prompt Engineering Best Practices: https://help.openai.com/en/articles/6654000-best-practices-for-prompt-enginee
- OpenAI Image Generation Guide: https://platform.openai.com/docs/guides/images/image-generation
- OpenAI Cookbook GPT Image Prompting Guide: https://cookbook.openai.com/examples/multimodal/image-gen-1.5-prompting_guide
- 第十八届“华中杯”大学生数学建模挑战赛参赛注意事项: https://www.cmathc.org.cn/mcm/news/445.html
- 全国大学生数学建模竞赛论文格式规范（2026年修订稿）: https://www.cmathc.org.cn/mcm/tz/407.html
- baoyu-infographic skill: https://skills.sh/jimliu/baoyu-skills/baoyu-infographic
