# 全题模型检验派生输出说明

本目录由 2026-04-26 全题模型检验与优缺点评价整理任务生成。所有文件均为论文第六节“模型检验”和第七节“模型优缺点评价”的派生支撑材料，不是第一问、第二问或第三问的正式主结果。

正式主结果仍以以下目录为准：

- `outputs/problem1/`
- `outputs/problem2/`
- `outputs/problem3/`

## 派生表格

| 文件 | 用途 |
| --- | --- |
| `cost_components_and_quality_summary.csv` | 汇总第一问、第二问和第三问四个情景的成本与服务质量指标 |
| `feasibility_validation_matrix.csv` | 汇总覆盖、容量、物理车辆链和政策冲突等硬可行性检查 |
| `problem2_sensitivity_tradeoff_table.csv` | 第二问三种正式候选与服务质量对照方案的成本-准时性权衡表 |
| `problem3_dynamic_sensitivity_table.csv` | 第三问四类代表性动态情景的成本、可行性和路线扰动表 |
| `problem3_case_validation_for_paper.csv` | 第三问案例验证总表副本，便于论文引用 |
| `figure_manifest.md` | 每张图的图名、视觉元素、设计意图、放置位置和生成提示词 |

## 派生图片

| 文件 | 论文用途 |
| --- | --- |
| `feasibility_validation_matrix.png` | 全题硬可行性矩阵 |
| `problem1_alns_convergence.png` | 第一问 ALNS 收敛与同 seed 100 迭代审计 |
| `problem1_late_diagnosis.png` | 第一问残余迟到来源诊断 |
| `problem2_cost_component_delta.png` | 第一问到第二问官方成本分项变化 |
| `problem2_variant_service_tradeoff.png` | 第二问候选方案与服务质量对照的成本-迟到权衡 |
| `problem3_scenario_cost_response.png` | 第三问四类动态事件的成本响应 |
| `problem3_event_response_bubble.png` | 第三问事件时刻、成本变化和路线扰动联合图 |

使用这些图表时需保留以下口径：

1. 第三问事件是代表性情景假设，不是官方附件数据。
2. 政策冲突、EV reservation、路线扰动和稳定性指标不是官方成本项。
3. 绿色限行只能按服务绿色区客户进行检查，不能写成道路穿越绿色区检测。
