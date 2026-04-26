# GPT Pro 上传包使用说明

上传本文件夹给 GPT Pro 后，优先阅读：

1. `gpt_pro_round3_figure_generation_guide.md`
2. `metadata.json`
3. `data/` 下全部 CSV

推荐流程：

1. 将 `gpt_pro_round3_figure_generation_guide.md` 中的“总控提示词”作为第一条消息发送。
2. 每次只生成一张图，复制对应“逐图提示词”。
3. 要求 GPT Pro 先读取 CSV、列出字段核对，再绘图。
4. 图生成后要求它列出图中所有数字与 CSV 字段的对应关系。
5. 对包含中文标题、图例、坐标轴的图，人工检查错字和数值精度。

核心红线：

- 不修改 CSV 数值。
- 不编造实验结果。
- 路线折线只表示访问顺序，不表示真实道路。
- 政策冲突和扰动指标不计入官方成本。
- 服务质量对照方案只用于灵敏度/Pareto 权衡，不写成第二问正式推荐。
