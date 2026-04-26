# 华中杯 A 题论文 LaTeX 编译说明

主文件：

- `hzcup_a_final_paper.tex`

图片目录：

- `figures/`

推荐编译命令：

```powershell
xelatex hzcup_a_final_paper.tex
xelatex hzcup_a_final_paper.tex
```

说明：

1. 本文使用 `ctexart`，需安装支持中文的 TeX 发行版，如 TeX Live 或 MiKTeX。
2. 目录由 `\tableofcontents` 自动生成并支持跳转。
3. 正文图片采用 14 张图：10 张为项目 CSV 支撑的结果/检验图，4 张为机制示意补充图。
4. 机制示意图已在图注中标明不代表道路几何、官方动态事件日志或额外成本项。
5. 若最终按提交规则删除目录页，可注释 `hzcup_a_final_paper.tex` 中的 `\tableofcontents` 及其前后 `\clearpage`。
