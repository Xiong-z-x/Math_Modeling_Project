# 城市绿色物流配送调度 - 第二问深度研究计划与改进方案

## 1. 问题本质与项目现状深度诊断

基于第一问（P1）的坚实基础（总成本 48644.68，4迟到），系统已具备优秀的路线评价与调度内核。但在引入第二问“燃油车 8:00-16:00 限行绿区”的硬性政策后，当前代码架构暴露出了深层的**“物理运力与订单颗粒度错位”**问题：

* **预检冲突警报**：第一问最优解中，燃油车在限行时段内执行了 12 个绿区节点。
* **颗粒度致盲 E2 运力**：目前 `data_processing/loader.py` 的拆分逻辑是基于最大载重 **3000kg**（`split_count = ceil(max(weight/3000, volume/15))`）。这导致拆分出的虚拟节点往往在 1500kg - 3000kg 之间。这种“大颗粒度”订单使得 15 辆新能源小车 E2（限重 1250kg）完全无法接单。
* **物理规律推演**：绿区总需求约为 35970 kg。在 E2 无法参战的情况下，压力全给到了仅有的 10 辆新能源大车 E1（总单趟载重 30000 kg）。**10 辆 E1 单趟无法吃下整个绿区。** 这必然导致 E1 必须回程重装（多趟复用），在早高峰时变路网下，极易引发大面积晚到惩罚；或者迫使燃油车在 16:00 之后扎堆进场。

---

## 2. 第二问核心改进方案 (基于 TD-VRPTW-GZ 框架)

结合最新的运筹学顶级文献（如 *European Journal of Operational Research*），我为您设计了以下兼具前沿性与可解释性的四层重构策略：

### 策略一：绿区订单“细粒度”重构 (Dynamic Demand Splitting)
* **操作思路**：修改预处理层，针对绿区客户，强制按 E2 的载重上限（**1250kg**）进行拆分。
* **物理意义**：释放 15 辆 E2 的被动运力。10 辆 E1 + 15 辆 E2 的单趟总运力将达到 **48750 kg**，完美覆盖绿区 35970 kg 的需求。从根本上消灭纯电车队“多趟折返”带来的迟到风险。

### 策略二：引入大尺度政策惩罚机制 (Policy Penalty Relaxation)
* **操作思路**：在 `metrics.py` 中引入 `C_policy`。当燃油车在 `[480, 960]`（即 8:00-16:00）进入绿区时，不直接判为死刑（Infeasible），而是附加一个巨大的成本惩罚（如 100000）。
* **前沿依据**：在 ALNS 搜索早期允许跨越“不可行域障碍”（Infeasible bounds relaxation），是现代元启发式算法解决带时间窗时变路径问题（TDVRPTW）避免陷入局部最优的最佳实践 [cite: 1.2]。

### 策略三：战术延后与时间离散化搜索 (Post-16:00 Delay Shift)
* **操作思路**：引入时间离散搜索法（Time Discretization Search, TDS） [cite: 4.1]。当燃油车必须配送绿区时，设计一个算子人为在其路线起点（Depot）施加 `Wait_Time`，使其“精准”在 16:01 进入绿区。
* **创新亮点**：用晚到惩罚（50元/小时）换取政策合规。这是城市零排放物流限行调度中经典的 "Wait-or-Switch"（等待或换车）策略 [cite: 3.2]。

### 策略四：定向绿区爆破与序列算子 (Targeted ALNS Operators)
* **操作思路**：
    1.  **GreenZone-Conflict Remove**：每次破坏阶段，高概率精准拔除处于时段违规状态的绿区节点。最新研究表明，基于序列特征的破坏算子（Sequence-based removal operators）在解决复杂 VRP 问题时效果最为显著 [cite: 4.3]。
    2.  **EV-Priority Insert**：在修复阶段，被拔出的绿区节点强制优先尝试插入 E1/E2 路线的最低成本位置。

---

## 3. 建模严谨性声明 (必须写入论文)

**防幻觉与客观事实对齐**：题目要求“燃油车不得进入绿色配送区”。然而，赛题仅提供了 O-D 距离矩阵，**缺乏城市路网的多边形几何轨迹数据（Polyline）**。这意味着我们无法在物理上判定一条连接两个“非绿区”客户的弧段是否穿过了绿区。
**论文话术建议**：“鉴于路网几何数据缺失，本模型合理假设并等效转换限行约束为：燃油车不得在限行时段内对坐标位于绿区内的客户执行配送服务。途经判定留作未来高精度 GIS 数据的拓展研究。”

---

## 4. Deep Search 与代码实施路线图 (Research Plan)

* **Phase 1: 数据层突围 (Data Refactoring)**
    * 在 `green_logistics/data_processing/loader.py` 中，为绿区客户增加独立的分流规则，按 1250kg 切分。并更新相关测试用例。
* **Phase 2: 政策评价器组装 (Evaluator Integration)**
    * 完善 `green_logistics/policies.py`，串接惩罚函数，使 P1 的基线解在 P2 评价下暴露出极高的 Policy Penalty。
* **Phase 3: 专属算子开发 (Operator Development)**
    * 在 `green_logistics/operators.py` 中实现 `GreenZone_Conflict_Remove` 和 `Post-16:00_Delay_Insert`。
* **Phase 4: 多场景对冲实验 (Scenario Analysis)**
    * 比较 P1 与 P2 的结果，提取出核心结论：“为满足限行政策，企业总运营成本上升了 X%，但碳排放量急剧下降了 Y%，体现了环保政策的强效引导作用”。

---
**参考文献来源：**
* [1.2] Time Dependent Vehicle Routing Problems: Formulations, Properties and Heuristic Algorithms. Transportation Science.
* [3.2] Zero-emission Delivery Zones: A New Way to Cut Traffic, Air Pollution and Greenhouse Gases. World Resources Institute.
* [4.1] ALNS for time-dependent green vehicle routing problem with time windows.
* [4.3] A review and ranking of operators in adaptive large neighborhood search for vehicle routing problems. European Journal of Operational Research.
