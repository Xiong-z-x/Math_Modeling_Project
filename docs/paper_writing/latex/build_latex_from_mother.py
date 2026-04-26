from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
MD_PATH = ROOT / "docs/paper_writing/hzcup_a_final_paper_mother_draft.md"
OUT_PATH = ROOT / "docs/paper_writing/latex/hzcup_a_final_paper.tex"


def remove_draft_blocks(text: str) -> str:
    lines = text.splitlines()
    if len(lines) > 2 and lines[2].startswith("> 写作阶段说明"):
        del lines[2]
        if len(lines) > 2 and lines[2].strip() == "":
            del lines[2]
    text = "\n".join(lines) + "\n"

    start = text.find("## 总目录式结构")
    if start != -1:
        end = text.find("\n---", start)
        if end != -1:
            end2 = text.find("\n", end + 1)
            text = text[:start] + text[end2 + 1 :]

    ref_start = text.find("\n## 参考文献")
    app_start = text.find("\n## 附录说明")
    if ref_start != -1 and app_start != -1 and app_start > ref_start:
        text = text[:ref_start] + "\n## 参考文献\n" + text[app_start:]

    app_c = text.find("\n### 附录 C：长表与图表生成说明")
    if app_c != -1:
        text = (
            text[:app_c]
            + "\n### 附录 C：长表与图表生成说明\n"
            + "正文图像已嵌入 LaTeX 源文件，图像原始数据、数值自检记录和生成数据包随支撑材料一并提交。"
            + "长路线表、逐停靠明细和动态诊断文件不放入正文。\n"
        )
    return text


def add_citations(text: str) -> str:
    needle = "最后，在第三问中以第二问正式方案为基准，对代表性动态事件进行事实冻结和滚动修复。\n"
    if needle not in text or "ropke2006alns" in text:
        return text
    cite_para = (
        "\n方法依据方面，本文的自适应大邻域搜索框架参考车辆路径与带时间窗取送问题中的 ALNS 思路"
        "\\cite{ropke2006alns,pisinger2007general}；时变行驶时间处理参考时间依赖车辆调度研究"
        "\\cite{ichoua2003time}；能耗、碳排和绿色车辆路径建模参考污染路径、绿色车辆路径与电动车路径问题研究"
        "\\cite{bektas2011pollution,demir2012alns,erdogan2012green,schneider2014evrptw,goeke2015mixed}；"
        "动态事件响应参考动态车辆路径综述和随机客户情景规划研究\\cite{bent2004scenario,pillac2013review}。\n"
    )
    return text.replace(needle, needle + cite_para, 1)


def add_cross_reference_phrases(text: str) -> str:
    replacements = {
        "GPT Pro 图表包": "图表生成数据包",
        "图表 CSV、提示词和红线说明": "图表 CSV、数值自检记录和生成说明",
        "表 1 给出全局主要符号。": "表\\ref{tab:symbols} 给出全局主要符号。",
        "车辆参数如下表。": "车辆参数见表\\ref{tab:vehicle-params}。",
        "数据预处理结果如下。": "数据预处理结果见表\\ref{tab:preprocess}。",
        "速度时段参数如下。": "速度时段参数见表\\ref{tab:speed-periods}。",
        "表 3 给出第一问正式结果。": "第一问正式结果见表\\ref{tab:p1-result}。",
        "候选方案比较如下。": "候选方案比较见表\\ref{tab:p2-candidates}。",
        "正式推荐 `DEFAULT_SPLIT`，其成本分项为：": "正式推荐 `DEFAULT_SPLIT`，其成本分项见表\\ref{tab:p2-result}。",
        "成本分项变化为：": "成本分项变化见表\\ref{tab:p1-p2-cost-delta}。",
        "四个代表性情景的正式结果如下。": "四个代表性情景的正式结果见表\\ref{tab:p3-result}。",
        "可行性检验结果如下。": "可行性检验结果见表\\ref{tab:validation}。",
        "正式支撑材料建议包括：": "正式支撑材料建议见表\\ref{tab:support-files}。",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


FIGURES = {
    1: (
        "fig01_order_aggregation_split_topology.png",
        "fig:order-aggregation",
        "订单聚合与虚拟服务节点拆分流程见图\\ref{fig:order-aggregation}。",
        "订单聚合前后的拓扑流向图。图中展示 2169 条原始订单向 88 个有效客户和 148 个虚拟服务节点的转化关系，强调距离矩阵索引与算法服务颗粒的分离。",
    ),
    2: (
        "fig02_customer_spatial_density.png",
        "fig:spatial-density",
        "客户需求与绿色配送区的空间关系见图\\ref{fig:spatial-density}。",
        "客户需求空间分布与绿色区约束。绿色配送区以城市中心 (0,0) 为圆心，配送中心位于 (20,20)，图中气泡和密度层仅表示客户需求分布。",
    ),
    3: (
        "fig03_speed_energy_surface.png",
        "fig:speed-energy",
        "速度时段、载重率与单位能耗的耦合关系见图\\ref{fig:speed-energy}。",
        "时变速度与载重率耦合下的单位能耗曲面。燃油车与电动车均按题面能耗函数计算，电动车电耗后续仍计入电力碳排。",
    ),
    4: (
        "fig04_problem1_route_risk_bundle.png",
        "fig:p1-route-risk",
        "第一问静态调度的空间覆盖与迟到风险见图\\ref{fig:p1-route-risk}。",
        "第一问静态调度路线束与迟到风险。折线仅表示访问顺序，不代表真实道路轨迹；红色描边表示存在迟到风险的趟次。",
    ),
    5: (
        "fig05_policy_cost_carbon_fleet_shift.png",
        "fig:policy-shift",
        "绿色限行政策对成本、碳排和车队结构的影响见图\\ref{fig:policy-shift}。",
        "绿色限行政策前后的成本、碳排与车队结构迁移。成本堆叠仅包含固定成本、能源成本、碳排成本和软时间窗罚金。",
    ),
    6: (
        "fig06_green_zone_service_policy_timeline.png",
        "fig:green-policy-timeline",
        "绿色区服务时刻与车型合规性见图\\ref{fig:green-policy-timeline}。",
        "绿色配送区服务时刻与车型合规检验。图中只检验绿色区客户服务事件，不推断道路几何穿越情况。",
    ),
    7: (
        "fig07_problem2_cost_punctuality_pareto.png",
        "fig:p2-pareto",
        "第二问候选方案的成本与准时性权衡见图\\ref{fig:p2-pareto}。",
        "第二问候选方案成本--准时性 Pareto 权衡。DEFAULT\\_SPLIT 为正式成本推荐，服务质量对照方案仅用于灵敏度分析。",
    ),
    8: (
        "fig08_problem3_frozen_gantt.png",
        "fig:p3-frozen-gantt",
        "动态事件发生后的事实冻结与滚动修复时间轴见图\\ref{fig:p3-frozen-gantt}。",
        "基于事实冻结的滚动时域车辆时间轴。事件线左侧表示已执行或锁定事实，右侧未来服务池参与局部修复。",
    ),
    9: (
        "fig09_problem3_event_response_matrix.png",
        "fig:p3-response-matrix",
        "四个代表性动态情景的成本响应与扰动规模见图\\ref{fig:p3-response-matrix}。",
        "第三问动态事件响应成本--扰动矩阵。四个情景为代表性动态扰动，均保持硬可行且政策冲突为 0。",
    ),
    10: (
        "fig10_feasibility_validation_dashboard.png",
        "fig:validation-dashboard",
        "全题关键约束检验结果见图\\ref{fig:validation-dashboard}。",
        "全题模型可信性检验矩阵。硬约束通过项与软时间窗迟到风险分列展示，避免将迟到误判为不可行。",
    ),
}


def figure_block(index: int) -> list[str]:
    file_name, label, before, caption = FIGURES[index]
    width = "0.96\\textwidth" if index in {5, 8, 9, 10} else "0.95\\textwidth"
    return [
        before,
        "",
        "\\begin{figure}[H]",
        "  \\centering",
        f"  \\includegraphics[width={width}]{{{file_name}}}",
        f"  \\caption{{{caption}}}",
        f"  \\label{{{label}}}",
        "\\end{figure}",
    ]


EXTRA_FIGURES = {
    "speed_mechanism": [
        "上述分段速度、二阶矩修正与载重率之间的作用关系见图\\ref{fig:speed-energy-mechanism}；随后图\\ref{fig:speed-energy} 给出由 CSV 直接生成的定量能耗曲面。",
        "",
        "\\begin{figure}[H]",
        "  \\centering",
        "  \\includegraphics[width=0.92\\textwidth]{fig03a_speed_energy_mechanism.png}",
        "  \\caption{时变速度--时间--能耗关系机制示意。该图用于解释分时段速度、Jensen 二阶矩修正和载重率对能耗估计的耦合关系；定量结果以题面函数和图\\ref{fig:speed-energy} 的 CSV 曲面为准。}",
        "  \\label{fig:speed-energy-mechanism}",
        "\\end{figure}",
    ],
    "green_constraint": [
        "绿色限行的空间围栏与时间禁行窗口可抽象为图\\ref{fig:green-constraint-mechanism} 所示的时空双重可行域。",
        "",
        "\\begin{figure}[H]",
        "  \\centering",
        "  \\includegraphics[width=0.92\\textwidth]{fig06a_green_constraint_mechanism.png}",
        "  \\caption{绿色约束的时空双重可行域示意。图中车辆图标仅用于说明绿色区服务事件的车型--时段可行性，不表示道路几何轨迹或路段穿越检测。}",
        "  \\label{fig:green-constraint-mechanism}",
        "\\end{figure}",
    ],
    "dynamic_freezing_cube": [
        "第三问滚动响应的状态冻结逻辑可用图\\ref{fig:dynamic-freezing-cube} 概括：事件时刻之前的事实不可逆，事件时刻之后的残余任务进入局部修复。",
        "",
        "\\begin{figure}[H]",
        "  \\centering",
        "  \\includegraphics[width=0.92\\textwidth]{fig08a_dynamic_freezing_cube.png}",
        "  \\caption{滚动时域下的状态冻结机制示意。该图为动态响应框架图，空间轨迹仅表示调度状态随时间的分层，不对应官方动态事件日志。}",
        "  \\label{fig:dynamic-freezing-cube}",
        "\\end{figure}",
    ],
    "dynamic_route_repair": [
        "在具体路线层面，局部修复原则如图\\ref{fig:dynamic-route-repair} 所示：冻结段保持不变，受影响的未来节点在原车辆和局部邻域内优先调整。",
        "",
        "\\begin{figure}[H]",
        "  \\centering",
        "  \\includegraphics[width=0.92\\textwidth]{fig08b_dynamic_route_reconstruction.png}",
        "  \\caption{动态事件前后的局部路线重构示意。该图仅说明新增与取消事件下的局部修复逻辑，不代表第三问四个情景的官方事件记录或真实道路轨迹。}",
        "  \\label{fig:dynamic-route-repair}",
        "\\end{figure}",
    ],
}


def insert_extra_figures(text: str) -> str:
    speed_needle = "其中 \\(t_i\\) 为离开上一节点的时刻。分段积分避免跨越速度时段边界时使用单一出发时刻速度造成的时间误差。\n"
    if speed_needle in text and "fig:speed-energy-mechanism" not in text:
        text = text.replace(speed_needle, speed_needle + "\n" + "\n".join(EXTRA_FIGURES["speed_mechanism"]) + "\n", 1)

    green_needle = "该约束是正式可行性条件，不是成本项。本文在搜索中可使用 EV reservation 作为调度评分辅助，使稀缺 E1 更倾向于服务受政策影响的绿色区任务；但最终成本仍按四项官方成本计算，EV reservation 不进入结果表中的总成本。\n"
    if green_needle in text and "fig:green-constraint-mechanism" not in text:
        text = text.replace(green_needle, green_needle + "\n" + "\n".join(EXTRA_FIGURES["green_constraint"]) + "\n", 1)

    dynamic_needle = "该流程的核心价值在于把“动态响应”从重新求解问题转化为带执行记忆的在线修复问题。已完成服务代表不可撤销事实，锁定趟次代表在途货物和司机任务边界，可调整池代表仍可由系统调度的未来计划。这样的分层能够解释为什么第三问不追求全天重排后的最低数值，而追求在硬可行、低扰动和可执行之间取得平衡。\n"
    if dynamic_needle in text and "fig:dynamic-freezing-cube" not in text:
        addition = "\n".join(EXTRA_FIGURES["dynamic_freezing_cube"] + [""] + EXTRA_FIGURES["dynamic_route_repair"])
        text = text.replace(dynamic_needle, dynamic_needle + "\n" + addition + "\n", 1)

    return text


def replace_figure_placeholders(text: str) -> str:
    lines = text.splitlines()
    for index in range(1, 11):
        marker = f"[图{index}占位"
        found = next((i for i, line in enumerate(lines) if line.startswith(marker)), None)
        if found is None:
            raise RuntimeError(f"missing figure placeholder {index}")
        end = found + 1
        while end < len(lines) and not (
            lines[end].startswith("### ")
            or lines[end].startswith("#### ")
            or lines[end].startswith("## ")
            or lines[end].startswith("[图")
        ):
            end += 1
        lines[found:end] = figure_block(index)
    return "\n".join(lines) + "\n"


def escape_text(s: str) -> str:
    return (
        s.replace("&", "\\&")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .replace("#", "\\#")
    )


def code_to_tex(code: str) -> str:
    code = (
        code.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .replace("#", "\\#")
        .replace("{", "\\{")
        .replace("}", "\\}")
    )
    return "\\texttt{" + code + "}"


def inline(s: str) -> str:
    s = s.replace("**", "")
    code_parts: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        code_parts.append(code_to_tex(match.group(1)))
        return f"@@CODE{len(code_parts) - 1}@@"

    s = re.sub(r"`([^`]+)`", stash_code, s)
    parts = re.split(r"(\\\(.*?\\\))", s)
    out: list[str] = []
    for part in parts:
        if part.startswith("\\(") and part.endswith("\\)"):
            out.append(part)
        else:
            escaped = escape_text(part)
            for idx, code in enumerate(code_parts):
                escaped = escaped.replace(f"@@CODE{idx}@@", code)
            out.append(escaped)
    return "".join(out)


TABLE_META = [
    ("主要符号说明", "tab:symbols"),
    ("车辆参数表", "tab:vehicle-params"),
    ("数据预处理结果", "tab:preprocess"),
    ("时变速度参数", "tab:speed-periods"),
    ("第一问正式调度结果", "tab:p1-result"),
    ("第二问候选方案比较", "tab:p2-candidates"),
    ("第二问正式推荐方案结果", "tab:p2-result"),
    ("第一问与第二问成本分项变化", "tab:p1-p2-cost-delta"),
    ("第二问服务质量对照方案", "tab:p2-service-tradeoff"),
    ("第三问代表性动态情景设计", "tab:p3-scenarios"),
    ("第三问动态响应结果", "tab:p3-result"),
    ("硬可行性检验汇总", "tab:validation"),
    ("误差来源与控制方式", "tab:error-sources"),
    ("支撑材料文件列表", "tab:support-files"),
]


def convert_markdown_to_latex(text: str) -> str:
    src = text.splitlines()
    body: list[str] = []
    table_idx = 0
    in_code = False
    in_math = False
    i = 0

    while i < len(src):
        line = src[i]
        stripped = line.strip()

        if stripped == "---":
            i += 1
            continue

        if stripped == "\\begin{figure}[H]":
            while i < len(src):
                body.append(src[i])
                if src[i].strip() == "\\end{figure}":
                    i += 1
                    break
                i += 1
            continue

        if stripped.startswith("```"):
            if not in_code:
                in_code = True
                body.append("\\begin{lstlisting}[basicstyle=\\ttfamily\\small,breaklines=true]")
            else:
                in_code = False
                body.append("\\end{lstlisting}")
            i += 1
            continue
        if in_code:
            body.append(line)
            i += 1
            continue

        if stripped == "\\[":
            in_math = True
            body.append("\\[")
            i += 1
            continue
        if in_math:
            body.append(line)
            if stripped == "\\]":
                in_math = False
            i += 1
            continue

        if (
            stripped.startswith("|")
            and i + 1 < len(src)
            and re.match(r"^\s*\|\s*:?-{2,}", src[i + 1])
        ):
            raw_rows = [line]
            i += 2
            while i < len(src) and src[i].strip().startswith("|"):
                raw_rows.append(src[i])
                i += 1
            rows = [[c.strip() for c in row.strip().strip("|").split("|")] for row in raw_rows]
            headers, data_rows = rows[0], rows[1:]
            caption, label = (
                TABLE_META[table_idx]
                if table_idx < len(TABLE_META)
                else (f"正文表格 {table_idx + 1}", f"tab:auto-{table_idx + 1}")
            )
            table_idx += 1
            ncols = len(headers)
            colspec = "".join([">{\\raggedright\\arraybackslash}X" for _ in range(ncols)])
            body.extend(
                [
                    "\\begin{table}[H]",
                    "\\centering",
                    "\\small",
                    f"\\caption{{{caption}}}",
                    f"\\label{{{label}}}",
                    "\\begin{tabularx}{\\textwidth}{" + colspec + "}",
                    "\\toprule",
                    " & ".join(inline(cell) for cell in headers) + " \\\\",
                    "\\midrule",
                ]
            )
            for row in data_rows:
                row = row + [""] * (ncols - len(row))
                body.append(" & ".join(inline(cell) for cell in row[:ncols]) + " \\\\")
            body.extend(["\\bottomrule", "\\end{tabularx}", "\\end{table}"])
            continue

        if stripped.startswith("# "):
            i += 1
            continue
        if stripped == "## 摘要":
            body.append("\\begin{abstract}")
            i += 1
            continue
        if stripped == "## 关键词":
            body.append("\\end{abstract}")
            i += 1
            while i < len(src) and not src[i].strip():
                i += 1
            if i < len(src):
                body.append("\\noindent\\textbf{关键词：}" + inline(src[i].strip()))
                body.append("\\clearpage")
                body.append("\\tableofcontents")
                body.append("\\clearpage")
                i += 1
            continue
        if stripped == "## 参考文献":
            body.extend(bibliography_block())
            i += 1
            continue
        if stripped == "## 附录说明":
            body.append("\\appendix")
            body.append("\\section{附录说明}")
            i += 1
            continue
        if stripped.startswith("## "):
            body.append("\\section{" + inline(stripped[3:].strip()) + "}")
            i += 1
            continue
        if stripped.startswith("### "):
            body.append("\\subsection{" + inline(stripped[4:].strip()) + "}")
            i += 1
            continue
        if stripped.startswith("#### "):
            body.append("\\subsubsection{" + inline(stripped[5:].strip()) + "}")
            i += 1
            continue

        if re.match(r"^\d+\.\s+", stripped):
            items: list[str] = []
            while i < len(src) and re.match(r"^\d+\.\s+", src[i].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", src[i].strip()))
                i += 1
            body.append("\\begin{enumerate}[leftmargin=2em,itemsep=0.2em]")
            for item in items:
                body.append("\\item " + inline(item))
            body.append("\\end{enumerate}")
            continue

        if stripped.startswith("- "):
            items = []
            while i < len(src) and src[i].strip().startswith("- "):
                items.append(src[i].strip()[2:])
                i += 1
            body.append("\\begin{itemize}[leftmargin=2em,itemsep=0.2em]")
            for item in items:
                body.append("\\item " + inline(item))
            body.append("\\end{itemize}")
            continue

        body.append("" if stripped == "" else inline(line))
        i += 1

    return "\n".join(body)


def bibliography_block() -> list[str]:
    refs = [
        (
            "ropke2006alns",
            "Ropke S, Pisinger D. An adaptive large neighborhood search heuristic for the pickup and delivery problem with time windows[J]. Transportation Science, 2006, 40(4):455--472.",
        ),
        (
            "pisinger2007general",
            "Pisinger D, Ropke S. A general heuristic for vehicle routing problems[J]. Computers \\& Operations Research, 2007, 34(8):2403--2435.",
        ),
        (
            "ichoua2003time",
            "Ichoua S, Gendreau M, Potvin J Y. Vehicle dispatching with time-dependent travel times[J]. European Journal of Operational Research, 2003, 144(2):379--396.",
        ),
        (
            "bektas2011pollution",
            "Bektaş T, Laporte G. The pollution-routing problem[J]. Transportation Research Part B: Methodological, 2011, 45(8):1232--1250.",
        ),
        (
            "demir2012alns",
            "Demir E, Bektaş T, Laporte G. An adaptive large neighborhood search heuristic for the pollution-routing problem[J]. European Journal of Operational Research, 2012, 223(2):346--359.",
        ),
        (
            "erdogan2012green",
            "Erdoğan S, Miller-Hooks E. A green vehicle routing problem[J]. Transportation Research Part E: Logistics and Transportation Review, 2012, 48(1):100--114.",
        ),
        (
            "schneider2014evrptw",
            "Schneider M, Stenger A, Goeke D. The electric vehicle-routing problem with time windows and recharging stations[J]. Transportation Science, 2014, 48(4):500--520.",
        ),
        (
            "goeke2015mixed",
            "Goeke D, Schneider M. Routing a mixed fleet of electric and conventional vehicles[J]. European Journal of Operational Research, 2015, 245(1):81--99.",
        ),
        (
            "bent2004scenario",
            "Bent R, Van Hentenryck P. Scenario-based planning for partially dynamic vehicle routing with stochastic customers[J]. Operations Research, 2004, 52(6):977--987.",
        ),
        (
            "pillac2013review",
            "Pillac V, Gendreau M, Guéret C, Medaglia A L. A review of dynamic vehicle routing problems[J]. European Journal of Operational Research, 2013, 225(1):1--11.",
        ),
    ]
    block = ["\\begin{thebibliography}{99}"]
    block.extend([f"\\bibitem{{{key}}} {ref}" for key, ref in refs])
    block.append("\\end{thebibliography}")
    return block


def latex_preamble() -> str:
    return r"""% !TeX program = xelatex
\documentclass[UTF8,zihao=-4,a4paper]{ctexart}
\usepackage[a4paper,top=2.5cm,bottom=2.5cm,left=2.6cm,right=2.6cm]{geometry}
\usepackage{amsmath,amssymb,bm}
\usepackage{graphicx}
\usepackage{booktabs,tabularx,array,longtable,multirow}
\usepackage{float}
\usepackage{caption,subcaption}
\usepackage{xcolor}
\usepackage{enumitem}
\usepackage{listings}
\usepackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=black,citecolor=black,urlcolor=blue}
\graphicspath{{figures/}}
\captionsetup{font=small,labelfont=bf,labelsep=quad}
\renewcommand{\contentsname}{目录}
\renewcommand{\figurename}{图}
\renewcommand{\tablename}{表}
\setcounter{tocdepth}{2}
\linespread{1.18}
\setlist{nosep}
\title{基于时变异构车辆路径与滚动重优化的城市绿色物流配送调度研究}
\author{}
\date{}
\begin{document}
\maketitle
\vspace{-2em}
"""


def build() -> None:
    text = MD_PATH.read_text(encoding="utf-8")
    text = remove_draft_blocks(text)
    text = add_citations(text)
    text = add_cross_reference_phrases(text)
    text = replace_figure_placeholders(text)
    text = insert_extra_figures(text)
    body = convert_markdown_to_latex(text)
    latex = latex_preamble() + body + "\n\\end{document}\n"
    OUT_PATH.write_text(latex, encoding="utf-8")

    print(OUT_PATH)
    print(f"figures={latex.count('\\begin{figure}')}")
    print(f"tables={latex.count('\\begin{table}')}")
    print(f"bibitems={latex.count('\\bibitem')}")


if __name__ == "__main__":
    build()
