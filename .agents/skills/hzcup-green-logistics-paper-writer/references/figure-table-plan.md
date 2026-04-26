# Figure And Table Plan

## Table Plan

| Table | Placement | Data source | Purpose |
| --- | --- | --- | --- |
| 数据预处理汇总表 | 数据预处理 | `解题总思路.md`, data loader outputs | show 2169 orders, 88 active customers, 148 service nodes |
| 车辆参数表 | 模型假设/符号说明 | problem statement | show capacity, type, count |
| 全局符号表 | 符号说明 | section drafts | define sets, variables, time, cost |
| 第一问结果表 | Problem 1 result | `outputs/problem1/summary.json` | official cost, vehicles, distance, carbon, lateness |
| 第二问候选方案表 | Problem 2 result | `outputs/problem2/variant_comparison.csv` | compare split strategies |
| 第二问服务质量权衡表 | sensitivity | `outputs/problem2_experiments/formal_screen_policy_ev_p500/` | distinguish formal min-cost and service-quality contrast |
| 第三问代表性情景表 | Problem 3 result | `outputs/problem3/scenario_comparison.csv` | show dynamic response facts |
| 模型检验矩阵 | validation | `outputs/model_validation/feasibility_validation_matrix.csv` | hard feasibility evidence |
| 优缺点评价表 | evaluation | paper text | concise strengths/limits/improvements |

Use three-line tables for paper-facing result tables. Long route lists belong in appendices/support files.

## Figure Plan

Use the higher-quality prompt/data pack:

- `outputs/gpt_pro_visual_pack/`
- `outputs/gpt_pro_visual_pack.zip`
- `outputs/gpt_pro_visual_pack/gpt_pro_master_prompt.md`
- `outputs/gpt_pro_visual_pack/visual_prompt_brief.md`

### Fig 1 客户需求空间分布核密度图

- Data: `outputs/gpt_pro_visual_pack/data/01_customer_spatial_demand.csv`, `01_green_zone_boundary.csv`, `01_key_points.csv`
- Visual elements: X/Y coordinates; weighted KDE; bubble size for demand; ring for green zone; markers for `(0,0)` and `(20,20)`.
- Intent: show spatial heterogeneity and prevent green-zone/depot confusion.
- Placement: data preprocessing or problem analysis.

### Fig 2 订单聚合前后的拓扑流向图

- Data: `02_order_aggregation_split_summary.csv`, `02_customer_split_detail.csv`
- Visual elements: Sankey from raw orders to active customers/split customers to virtual nodes.
- Intent: make virtual-node preprocessing auditable.
- Placement: data preprocessing.

### Fig 3 时变路网下车速-能耗时空立方体图

- Data: `03_speed_energy_profile.csv`
- Visual elements: time, load ratio, expected fuel/electric energy; period color bands.
- Intent: justify time-dependent ETA and Jensen energy correction.
- Placement: model building or error analysis.

### Fig 4 第一问静态调度空间路径与迟到风险双编码图

- Data: `04_route_visual_arcs_p1_p2.csv`, `01_customer_spatial_demand.csv`, `01_green_zone_boundary.csv`
- Visual elements: line color for vehicle type; line width for trip load/cost; red highlight for lateness.
- Intent: connect route coverage, vehicle choice, and residual time-window risk.
- Placement: Problem 1 results.
- Must state: straight lines indicate visit order, not roads.

### Fig 5 绿色限行政策前后的成本-碳排-车队结构迁移图

- Data: `05_policy_cost_carbon_shift.csv`
- Visual elements: stacked official cost components; arrow for total-cost change; carbon and vehicle-usage callouts.
- Intent: answer how policy changes cost/carbon/fleet structure.
- Placement: Problem 2 results.

### Fig 6 绿色配送区服务时刻与车型合规热力图

- Data: `05_green_service_policy_timeline.csv`
- Visual elements: arrival time vs service/customer node; color by vehicle type; shaded restricted window; policy conflict marker.
- Intent: prove zero-conflict green-zone service logic.
- Placement: Problem 2 validation.

### Fig 7 第二问候选方案成本-准时性 Pareto 权衡图

- Data: `06_problem2_candidate_tradeoff.csv`
- Visual elements: X total cost; Y max lateness; bubble size late-stop count; color formal/sensitivity.
- Intent: honestly show cost-service tradeoff.
- Placement: sensitivity analysis.

### Fig 8 第三问动态事件响应成本-扰动矩阵图

- Data: `07_problem3_event_response.csv`, `07_problem3_route_change_counts.csv`
- Visual elements: scenario rows; columns for cost delta, changed stops, reassignment; color red/green by cost change.
- Intent: show rolling response stability and feasibility.
- Placement: Problem 3 results or validation.

### Fig 9 基于事实冻结的滚动时域车辆时间轴图

- Data: `07_problem3_case_validation.csv` plus scenario subfolder diagnosis files if needed.
- Visual elements: event time vertical line; done/locked/free segments; vehicle lanes.
- Intent: explain physical realism of dynamic model.
- Placement: Problem 3 model building.

### Fig 10 全题模型可信性检验矩阵图

- Data: `08_feasibility_validation_matrix.csv`
- Visual elements: heatmap rows P1/P2/P3 scenarios; columns coverage/capacity/vehicle chain/policy.
- Intent: concise proof of hard feasibility.
- Placement: validation section.

## Existing Validation Figures

Already generated under `outputs/model_validation/`; use them if GPT-generated figures are delayed:

- `feasibility_validation_matrix.png`
- `problem1_alns_convergence.png`
- `problem1_late_diagnosis.png`
- `problem2_cost_component_delta.png`
- `problem2_variant_service_tradeoff.png`
- `problem3_scenario_cost_response.png`
- `problem3_event_response_bubble.png`

These are derived from project outputs and can be cited directly.
