# 新模型论文撰写启动提示词

把下面内容发给新模型。若新模型支持读取本地文件，请让它优先读取本项目 skill：

`c:\Math_Modeling_Project\.agents\skills\hzcup-green-logistics-paper-writer\SKILL.md`

同时让它读取：

- `docs/paper_writing/project_closeout_full_summary.md`
- `docs/results/problem1_static_scheduling_summary.md`
- `docs/results/problem2_modeling_and_solution_closeout.md`
- `docs/results/problem3_modeling_and_solution_closeout.md`
- `docs/results/model_validation_and_evaluation_sections.md`
- `outputs/gpt_pro_visual_pack/gpt_pro_master_prompt.md`
- `outputs/gpt_pro_visual_pack/visual_prompt_brief.md`

## 可直接复制的提示词

```text
你现在接手 c:\Math_Modeling_Project 项目，任务是根据项目专用 skill 完成华中杯 A 题“城市绿色物流配送调度”最终论文撰写。请先读取：

1. .agents/skills/hzcup-green-logistics-paper-writer/SKILL.md
2. 该 skill 的 references/ 下所有参考文件
3. docs/paper_writing/project_closeout_full_summary.md
4. docs/results/problem1_static_scheduling_summary.md
5. docs/results/problem2_modeling_and_solution_closeout.md
6. docs/results/problem3_modeling_and_solution_closeout.md
7. docs/results/model_validation_and_evaluation_sections.md
8. outputs/problem1/summary.json
9. outputs/problem2/recommendation.json
10. outputs/problem2/variant_comparison.csv
11. outputs/problem3/recommendation.json
12. outputs/problem3/scenario_comparison.csv
13. outputs/model_validation/figure_manifest.md
14. outputs/gpt_pro_visual_pack/visual_prompt_brief.md

你的目标是生成一篇符合华中杯数学建模论文规范的中文论文母稿。写作必须紧扣题意，不能把本题写成普通 VRP，也不能遗漏时变速度、异构车队、软时间窗、载重相关能耗、碳排成本、绿色限行和动态事件响应。

硬性边界：
- 不覆盖 outputs/problem1/、outputs/problem2/、outputs/problem3/。
- 第一问正式成本 48644.68，车辆 E1:10,F1:33，迟到点/最大迟到 4/31.60。
- 第二问正式推荐 DEFAULT_SPLIT，成本 49239.78，政策冲突 0，车辆 E1:10,F1:35，迟到点/最大迟到 12/129.44。
- 第二问服务质量对照方案成本 50770.72，迟到点 2，最大迟到 5.93，只能写作灵敏度/权衡分析。
- 第三问四个代表性动态情景成本为 48711.28、49237.36、49263.35、49207.47，均硬可行且政策冲突 0；它们不是官方附件动态数据。
- 官方成本只包括固定成本、能源成本、碳排成本和软时间窗罚金。
- 政策冲突、EV reservation、稳定性指标、路线扰动指标不能写成官方成本项。
- 时间窗是软约束；绿色限行是硬约束；固定成本按物理车辆计；电动车也有电力碳排。
- 绿色区中心是 (0,0)，配送中心是 (20,20)；没有道路几何，不能声称检测路径穿越绿区。
- 距离矩阵使用原始 customer_id，算法服务颗粒使用虚拟 service_node_id。

输出策略：
1. 先生成论文总目录式结构，但不要放正式“目录”页；按华中杯提交要求控制正文页数，长表和代码放附录/支撑材料。
2. 再逐章撰写：摘要、关键词、问题重述、问题分析、模型假设、符号说明、数据预处理、模型建立与求解、模型检验、模型评价、参考文献、附录说明。
3. 每一问都必须包含：建模思路、关键公式、变量说明、算法流程、结果表、结果解释、局限说明。
4. 图像先预留占位，不要凭空生成。每个占位必须给出图名、数据源、视觉元素、设计意图、放置位置和 GPT Pro 生成提示词。
5. 表格按三线表风格组织，优先使用项目真实数据。
6. 文字风格要克制、严谨、信息密度高；避免“众所周知”“非常重要”等空话。
7. 不要编造不存在的随机实验、最优性证明、道路几何、动态事件日志或新的数值。
8. 如发现旧参考材料与正式输出矛盾，以正式输出和 docs/paper_writing/project_closeout_full_summary.md 为准。

请先输出：
A. 你对项目的 12 条核心理解；
B. 最终论文章节结构；
C. 正文图表清单；
D. 需要我确认的风险点。

确认后再开始写正文母稿。
```

## 使用说明

如果新模型没有本地文件读取能力，就把以下文件打包上传：

- `.agents/skills/hzcup-green-logistics-paper-writer/`
- `docs/paper_writing/project_closeout_full_summary.md`
- `docs/results/problem1_static_scheduling_summary.md`
- `docs/results/problem2_modeling_and_solution_closeout.md`
- `docs/results/problem3_modeling_and_solution_closeout.md`
- `docs/results/model_validation_and_evaluation_sections.md`
- `outputs/model_validation/`
- `outputs/gpt_pro_visual_pack.zip`

先让新模型做项目理解和风险点确认，再让它逐章写作。不要一次要求直接生成最终 PDF。
