# Template And Web Research Notes

## Local Files Reviewed

Folder: `论文模板案例/`

- `A题4.26-09.20(1).docx`
- `华中杯论文.docx`
- `华中杯论文.pdf`
- `C202508300363(1).pdf`
- `“华中杯”大学生数学建模挑战赛论文格式规范_1646985301187(1).pdf`

Key observations:

1. The local A-problem template uses: title, abstract, keywords, problem restatement, problem analysis, assumptions, symbols, data preprocessing, model building/solution, model validation, model evaluation, references, appendices.
2. The local template explicitly instructs the abstract to contain background, one paragraph per problem, and final model value/innovation summary.
3. The template favors per-problem “建模思路 -> 模型建立 -> 求解过程 -> 结果分析 -> 小结”.
4. Figures in the examples are usually placed after the paragraph that defines the data/model mechanism, not in a separate gallery.
5. The format PDF states: abstract page first, references must be listed, support files must contain runnable code and required materials, and identity information must not appear.

## Web Search Summary

Searches were run for recent HuaZhong Cup papers and A-problem optimization examples. Public complete downloads were inconsistent: many hits were preview pages, commercial document sites, or non-authoritative reposts. Use them only for style if manually inspected; do not cite their content as evidence.

Official/reliable references found:

- HuaZhong Cup competition official notice page, including rule notes about paper body length and no table of contents:
  `https://www.cmathc.org.cn/mcm/news/445.html`
- China University Student Online national modeling paper display:
  `https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/qkt_sxjm_lw_lwzs.shtml`
- CUMCM paper format PDF:
  `https://www.mcm.edu.cn/upload_cn/node/775/cQMeL0YY905244c8bd4b9af832f1699446d8385e.pdf`

Downloaded into `论文模板案例/web_references/`:

- `cumcm_paper_format_2023.pdf`
- `cumcm_paper_format_2023.doc`

## Skill Search Summary

The requested `find-skills` lookup was performed:

```powershell
npx skills find "academic writing latex paper"
npx skills find "document writing docx latex"
```

Relevant results:

- `bahayonghang/academic-writing-skills@latex-paper-en`, 994 installs
- `eyh0602/skillshub@paper-polish`, 264 installs
- `ndpvt-web/latex-document-skill@latex-document`, 219 installs
- `skillcreatorai/ai-agent-skills@docx`, 155 installs

No generic external skill was installed because this project needs more domain-specific facts and red lines than a general academic-writing skill can provide.

## Style Takeaways

- Contest papers reward a tight chain: problem fact -> model need -> formula/algorithm -> result -> validation.
- Tables should carry exact numbers; figures should explain structure, mechanism, or comparison.
- Strong claims should be framed as “可行、可复核、符合题意、物理一致” rather than “最优” unless a mathematical lower bound exists.
- A good optimization paper can honestly present a tradeoff. For this project, the Problem 2 service-quality solution should be used as a Pareto sensitivity result, not hidden.
- Keep the main paper near the page limit and move route details, long code, long prompt packs, and generated image instructions to appendices/support materials.
