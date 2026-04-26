# GPT Pro 高级中文图表生成包

本目录用于把项目中的真实数据整理成可上传给 GPT Pro 的图表生成输入。所有 CSV 均由 `c:\Math_Modeling_Project` 的正式数据、正式输出或已标注的灵敏度对照输出派生。

正式主结果仍以以下目录为准：

- `outputs/problem1/`
- `outputs/problem2/`
- `outputs/problem3/`

## 使用纪律

1. 不要把编造数据写成项目真实结果。
2. 可以生成理论机制示意图，但图题必须写明“机制示意”或“理论曲线”。
3. 第三问动态事件必须写成“代表性情景假设”，不是官方附件数据。
4. 路线弧线只表示访问顺序，不能表示真实道路轨迹，也不能用于判断是否穿越绿色区。
5. 绿色区中心是 `(0,0)`，配送中心是 `(20,20)`。
6. 图内文字统一使用中文：标题、坐标轴、图例、注释均用中文。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `gpt_pro_master_prompt.md` | 先让 GPT Pro 理解项目、读取数据、自检并逐图生成的总控提示词 |
| `prompt_research_notes.md` | 联网检索和 `find-skills` 结果摘要，说明总控提示词的设计依据 |
| `visual_prompt_brief.md` | 可直接交给 GPT Pro 的中文图表说明和生成提示词 |
| `metadata.json` | 数据来源和红线说明 |
| `data/01_customer_spatial_demand.csv` | 客户坐标、需求、订单数、绿区标记和拆分节点数 |
| `data/01_green_zone_boundary.csv` | 绿色配送区半径 10 km 的圆形边界 |
| `data/01_key_points.csv` | 城市中心和配送中心坐标 |
| `data/02_order_aggregation_split_summary.csv` | 订单、客户、虚拟服务节点的层级汇总 |
| `data/02_customer_split_detail.csv` | 客户需求与拆分节点数明细 |
| `data/03_speed_energy_profile.csv` | 按题面速度分布和能耗公式派生的时段速度-能耗理论曲线数据 |
| `data/04_route_visual_arcs_p1_p2.csv` | 第一问和第二问访问顺序直线弧数据，仅作路线结构可视化 |
| `data/05_policy_cost_carbon_shift.csv` | 第一问到第二问成本、碳排和服务质量变化 |
| `data/05_green_service_policy_timeline.csv` | 第一问政策预判与第二问正式解的绿区服务时刻表 |
| `data/06_problem2_candidate_tradeoff.csv` | 第二问候选方案和服务质量对照方案权衡表 |
| `data/07_problem3_event_response.csv` | 第三问四类代表性动态情景总表 |
| `data/07_problem3_case_validation.csv` | 第三问案例验证表 |
| `data/07_problem3_route_change_counts.csv` | 第三问各情景路线变化类型计数 |
| `data/08_feasibility_validation_matrix.csv` | 全题正式结果可行性矩阵 |
