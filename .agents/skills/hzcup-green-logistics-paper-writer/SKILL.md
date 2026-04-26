---
name: hzcup-green-logistics-paper-writer
description: Use this project-specific skill when summarizing, planning, drafting, polishing, or compiling the Huazhong Cup A problem paper for c:\Math_Modeling_Project, especially the full first-to-third-question green logistics routing solution, figures, tables, validation, appendices, Word/LaTeX handoff, or final paper narrative.
---

# Huazhong Cup Green Logistics Paper Writer

## Purpose

Use this skill to turn the completed `c:\Math_Modeling_Project` solution into a contest-paper-ready narrative. It is project-specific: always ground the paper in the original HuaZhong Cup A problem, the supplementary statement, the formal outputs, and the closeout summaries.

This skill supports:

- whole-problem summaries before paper writing;
- section-by-section paper drafting;
- table/figure placement plans and GPT image-generation handoff;
- final Word/LaTeX handoff planning;
- consistency checks before submitting a paper or support package.

## First Files To Read

Before writing any paper content, read in this order:

1. `A题：城市绿色物流配送调度.pdf`
2. `关于第十八届“华中杯”大学生数学建模挑战赛A题的补充说明.pdf`
3. `解题总思路.md`
4. `docs/results/problem1_static_scheduling_summary.md`
5. `docs/results/problem2_modeling_and_solution_closeout.md`
6. `docs/results/problem3_modeling_and_solution_closeout.md`
7. `docs/results/model_validation_and_evaluation_sections.md`
8. `outputs/problem1/summary.json`
9. `outputs/problem2/recommendation.json`
10. `outputs/problem2/variant_comparison.csv`
11. `outputs/problem3/recommendation.json`
12. `outputs/problem3/scenario_comparison.csv`
13. `outputs/model_validation/figure_manifest.md`
14. `outputs/gpt_pro_visual_pack/visual_prompt_brief.md`

Then load only the reference file(s) below that match the current task.

## Reference Files

- `references/project-facts.md`: immutable facts, official results, model boundaries, and innovation claims.
- `references/source-map.md`: which folders are formal results, sensitivity outputs, prompt packs, or non-citable references.
- `references/paper-section-rules.md`: section-by-section writing rules for the HuaZhong Cup paper.
- `references/figure-table-plan.md`: figure/table placeholders, data sources, visual encodings, and prompt handoff.
- `references/template-research-notes.md`: local template observations, web-search notes, and format constraints.

## Non-Negotiable Boundaries

Do not write unsupported claims.

- Official cost is exactly fixed cost, energy cost, carbon cost, and soft-time-window penalty.
- Policy conflict, EV reservation, stability metrics, and route disturbance metrics are not official cost terms.
- Time windows are soft constraints; green restriction is a hard constraint.
- Fixed cost is counted by physical vehicles, not trips.
- EVs have electricity carbon emissions; never call them zero-emission in the cost model.
- Green zone center is `(0,0)`; depot is `(20,20)`.
- There is no road geometry; route lines are visit-order visual links only.
- Distance matrix uses original `customer_id`; algorithm service granularity uses `service_node_id`.
- Problem 3 events are representative scenario assumptions, not official attachment data.
- Do not claim global optimality; claim high-quality feasible heuristic solutions with validation evidence.

## Recommended Paper Architecture

For the final paper, prefer this structure:

1. 摘要 and 关键词
2. 一、问题重述
3. 二、问题分析
4. 三、模型假设
5. 四、符号说明
6. 五、数据预处理
7. 六、模型建立与求解
   - 6.1 第一问：TD-HFVRPTW-LD 静态调度模型
   - 6.2 第二问：绿色限行硬约束与政策合规重优化模型
   - 6.3 第三问：事件驱动滚动时域动态响应模型
8. 七、模型检验与敏感性分析
9. 八、模型评价与改进方向
10. 参考文献
11. 附录：支撑材料清单、关键代码清单、长表、图表生成说明

If using the official eighteenth HuaZhong Cup notice as the final constraint, do not include a table of contents and keep the main body within 30 pages; move long code, long route tables, and extra diagnostics to support files or appendices.

## Writing Workflow

1. **Orient.** Re-read the problem and supplementary statement. State the target as TD-HFVRPTW-LD-GZ-DYN: time-dependent heterogeneous-fleet VRP with soft time windows, load-dependent energy, green-zone policy, and dynamic events.
2. **Separate evidence.** Use `outputs/problem1/`, `outputs/problem2/`, and `outputs/problem3/` as formal results. Use experiments only for sensitivity or service-quality tradeoffs with explicit labels.
3. **Draft from facts.** Write every section from project outputs and closeout documents. Use formulas from the summaries; rewrite prose, do not invent new experiments.
4. **Show strength honestly.** Emphasize physical consistency, virtual service nodes, Jensen energy correction, route/trip versus physical vehicle separation, policy-feasible repair, and event-time freezing. Do not hide the Problem 2 lateness tradeoff; turn it into a cost-service Pareto discussion.
5. **Use tables for exact numbers.** Put official costs, vehicle usage, feasibility, and scenario rows into concise three-line tables. Avoid decorative tables.
6. **Reserve image slots.** Do not generate final images inside the paper draft unless asked. Insert `[图X占位]` with name, data source, visual encoding, design intent, and generation prompt.
7. **Check formulas.** Prefer LaTeX math in Markdown/LaTeX drafts. For Word handoff, keep formulas simple and separately list any equations needing native Word equation conversion.
8. **Audit.** Before finalizing a section, check against the boundaries above, then check that every numeric claim has a cited project file.

## Tone And Style

Write in Chinese contest-paper style: precise, compressed, and causal. Avoid empty phrases such as “非常重要” or “众所周知”. Use “本文” consistently. Explain why a model component is required by the problem data or physical law. When a result is imperfect, state it and interpret it as a tradeoff rather than disguising it.

## Preferred Output Modes

When asked for a whole-project summary, produce:

- result boundary table;
- title/abstract/keyword recommendations;
- technical route;
- data preprocessing summary;
- assumptions and symbols;
- per-question model, algorithm, result, and evidence;
- model validation and limitations;
- figure/table plan;
- appendix/support-material plan.

When asked to draft the final paper, produce section files under `docs/paper_writing/` first. Generate Word or LaTeX only after the section text, formulas, and figure placeholders pass consistency checks.
