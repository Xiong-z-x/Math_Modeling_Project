# Paper Section Rules

## Format Priority

Use the latest HuaZhong Cup notice and local template folder first. Current known priority:

1. `论文模板案例/“华中杯”大学生数学建模挑战赛论文格式规范_1646985301187(1).pdf`
2. official eighteenth-competition notice found online
3. `论文模板案例/A题4.26-09.20(1).docx`
4. `论文模板案例/华中杯论文.pdf` and `C202508300363(1).pdf` as style references only

The eighteenth notice indicates: no table of contents, main body no more than 30 pages excluding abstract and appendices. The old 2022 format note says the first page is the abstract and references/support materials must be listed. If constraints differ, prefer the current competition notice.

## Title

Title should be specific and model-bearing. Good candidates:

- 基于时变异构车辆路径与滚动重优化的城市绿色物流配送调度研究
- 考虑绿色限行与动态扰动的时变异构车队配送调度模型
- 基于 TD-HFVRPTW-LD-GZ-DYN 模型的城市绿色物流配送优化

Avoid vague titles such as “城市物流问题研究”.

## Abstract

Keep within one page. Use four compact paragraphs:

1. Problem background and model scope.
2. Problem 1 method and result.
3. Problem 2 method, policy-compliant result, and service-quality tradeoff.
4. Problem 3 dynamic response and final validation/evaluation.

Mention exact results sparingly but clearly:

- P1 cost `48644.68`, vehicles `E1:10,F1:33`, late `4/31.60`.
- P2 cost `49239.78`, policy conflict `0`, vehicles `E1:10,F1:35`, late `12/129.44`.
- P2 service-quality contrast cost `50770.72`, late `2/5.93`.
- P3 scenario costs `48711.28`, `49237.36`, `49263.35`, `49207.47`, all hard-feasible.

Keywords: 城市绿色物流；异构车辆路径；软时间窗；时变路网；ALNS；滚动优化.

## Problem Restatement

Do not copy the statement verbatim. Restate:

- company serves 98 customer points using fuel and electric vehicles;
- orders have weight/volume, coordinates, distance matrix, and time windows;
- speed varies by time period and energy depends on speed/load;
- Problem 1 asks static no-policy minimum-cost scheduling;
- Problem 2 adds green-zone restriction;
- Problem 3 asks dynamic response to cancellations/new orders/address changes/time-window changes.

## Problem Analysis

Write one paragraph per problem. Each paragraph should identify the key mathematical difficulty and the chosen response.

- P1: not ordinary VRP; combines dual capacity, soft TW, time-dependent ETA, load-dependent energy, carbon cost, physical vehicle reuse.
- P2: green-zone policy couples location, vehicle type, and arrival time; formal feasibility requires zero policy conflict.
- P3: event time splits past facts from future decisions; rolling repair protects execution stability.

## Assumptions

Use concise numbered assumptions:

1. 17:00 after-speed extension uses normal period distribution.
2. Green-zone membership uses Euclidean distance to `(0,0)`.
3. Policy conflict checks service events only, because no road geometry exists.
4. Customer demand may be split into virtual service nodes.
5. A physical vehicle may execute multiple depot-to-depot trips.
6. Soft time windows allow early waiting and late penalty.
7. EVs include electricity carbon emissions.
8. Problem 3 dynamic events are representative assumptions.

## Symbols

Use one global symbol table plus short problem-specific additions. Include:

- original customer set \(C\), virtual service set \(S\), vehicle type set \(K\), route/trip set \(R\);
- original customer mapping \(c(i)\);
- demand \(q_i,u_i\), capacities \(Q_k,V_k\);
- time window \([e_i,l_i]\), arrival \(a_i\), service start \(b_i\), waiting \(W_i\), lateness \(L_i\);
- distance \(d_{ab}\), time-dependent travel time \(\tau_{ab}(t)\);
- vehicle-use variable \(u_m\), trip-type variable \(y_{rk}\), arc variable \(x_{ijr}\);
- dynamic event time \(t_e\), frozen/done/free service sets.

## Data Preprocessing

Must include:

- raw orders to active customers to virtual service nodes;
- split rule:

\[
n_i=\left\lceil \max\{Q_i/3000,V_i/15\}\right\rceil.
\]

- green-zone indicator:

\[
g_c=\mathbf 1\{x_c^2+y_c^2\le 10^2\}.
\]

- time conversion to absolute minutes;
- reminder that `service_node_id` and `customer_id` are different.

## Model And Solution Sections

For each problem, use the same internal rhythm:

1. modeling objective;
2. key constraints;
3. algorithm or search design;
4. result table;
5. result interpretation;
6. limitation or tradeoff.

### Problem 1

Core formulas:

\[
\min C=C_{\mathrm{fixed}}+C_{\mathrm{energy}}+C_{\mathrm{carbon}}+C_{\mathrm{tw}}.
\]

\[
C_{\mathrm{fixed}}=400\sum_m u_m.
\]

\[
W_i=\max(e_i-a_i,0),\quad L_i=\max(a_i-l_i,0).
\]

\[
C_{\mathrm{tw}}=\sum_i(20W_i/60+50L_i/60).
\]

Use piecewise time-dependent ETA and Jensen energy correction:

\[
E[v^2]=\mu^2+\sigma^2.
\]

State ALNS at a high level: initial construction, removal/repair operators, adaptive weights, local evaluation.

### Problem 2

Add policy constraint:

\[
x_{ijr}=1,\ c(j)\in G,\ k(r)\in K_F \Rightarrow a_j\notin[480,960).
\]

Explain that zero policy conflict is a hard pass/fail condition, not a cost item.

Present formal variant comparison and the service-quality sensitivity contrast.

### Problem 3

Use event-time partition:

\[
S=S^{done}(t_e)\cup S^{lock}(t_e)\cup S^{free}(t_e).
\]

Only \(S^{free}\) and new/canceled/changed nodes are reoptimized. Stability is a diagnostic, not official cost.

## Validation And Evaluation

Use `docs/results/model_validation_and_evaluation_sections.md` as the mother draft. Required subsections:

- feasibility validation;
- stability and sensitivity;
- statistical/error analysis;
- old/new model or old/new scheme comparison;
- advantages, limitations, and improvement directions.

## Tables

Use concise three-line-table style:

- data preprocessing facts;
- vehicle parameters;
- symbol table;
- P1 result table;
- P2 candidate comparison;
- P2 formal vs service-quality sensitivity;
- P3 scenario comparison;
- feasibility validation matrix;
- model advantages/limitations.

## Figures

Reserve figure slots, do not invent images. For every figure, include:

- figure name;
- data source;
- axes / color / size mapping;
- design intent;
- placement;
- GPT image prompt if needed.

Use `outputs/gpt_pro_visual_pack/` for advanced image-generation handoff.

## References

Include references for:

- ALNS;
- dynamic VRP review;
- pollution-routing problem / energy-carbon routing;
- mathematical modeling contest format/official references;
- HuaZhong Cup statement and supplement as problem sources.

Do not cite online template pages as scientific evidence.
