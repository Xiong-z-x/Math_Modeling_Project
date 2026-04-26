# Source Map And Result Boundaries

## Formal Results

Use these as main paper results:

| Scope | Source | Paper use |
| --- | --- | --- |
| Problem 1 | `outputs/problem1/` | static no-policy baseline |
| Problem 2 | `outputs/problem2/recommendation.json`, `outputs/problem2/default_split/`, `outputs/problem2/variant_comparison.csv` | green-zone policy result and formal candidate comparison |
| Problem 3 | `outputs/problem3/recommendation.json`, `outputs/problem3/scenario_comparison.csv`, `outputs/problem3/scenario_assumptions.csv`, scenario subfolders | representative dynamic-event evaluation |
| Validation | `outputs/model_validation/`, `docs/results/model_validation_and_evaluation_sections.md` | model validation, sensitivity, errors, evaluation |

## Sensitivity Or Supporting Results

These may be cited only with labels:

| Source | Label |
| --- | --- |
| `outputs/problem2_experiments/formal_screen_policy_ev_p500/` | service-quality sensitivity / contrast solution |
| `outputs/problem1_cost_100_trial/` | same-seed convergence audit, not a new formal answer |
| `outputs/model_validation/` | paper-support derivative outputs |
| `outputs/gpt_pro_visual_pack/` | figure-generation prompt/data package, not solver output |

## Non-Citable Or Reference-Only Areas

Use these only for inspiration or audit notes:

| Source | Boundary |
| --- | --- |
| `模型分析参考思路/` | may contain useful structure but also unsupported numbers |
| `参考思路/`, `第一问改进思路/`, `第二问参考思路/`, `第三问参考思路/` | brainstorming/reference only |
| old debug folders | do not cite unless explicitly documented as experiment |
| external online templates | style reference only, not project evidence |

## Files To Update During Paper Work

When creating new paper-writing artifacts, prefer:

- `docs/paper_writing/`
- `docs/results/` for final section mother drafts;
- `outputs/model_validation/` for derived validation tables or figures;
- `outputs/gpt_pro_visual_pack/` for GPT image generation inputs.

Do not overwrite:

- `outputs/problem1/`
- `outputs/problem2/`
- `outputs/problem3/`

## Support Material Packaging

For HuaZhong Cup support files, include:

- Word or LaTeX source of the paper;
- key runnable source code under `green_logistics/`, `problems/`, and `tests/`;
- output summaries needed to reproduce paper tables;
- figure prompt/data packs if AI-assisted figure rendering is used;
- a file-list appendix.

Do not include personal identity, school identity, or unrelated debug dumps.
