# 海洋时空过滤检索中候选批次的提前缩减

《海洋数据挖掘》课程论文。本项目通过三轮合成候选流实验，比较在相同检查上限下，找到 8 条或 9 条合格结果时缩小候选批次，对检查数量和调用次数的影响。

## 提交材料

- **[论文版 Word 报告](海洋数据挖掘实验报告.docx)**
- **[AI 协作记录](collaboration/chat.md)**
- [实验代码与原始结果](experiments/)

## 实验材料

| 实验 | 核心问题 | 结果 |
|---|---|---|
| 第一轮 | 比较一次性取候选与迭代批次 | [结果汇总](experiments/results/pilot_v01/summary.csv) |
| 第二轮 | 检验找到 9 条时缩批的效果 | [结果汇总](experiments/results/pilot_v02/summary.csv) |
| 第三轮 | 比较找到 8 条和 9 条时缩批 | [结果汇总](experiments/results/pilot_v03/summary.csv) |

三轮共 13,500 个合成查询。各轮目录保存逐查询结果、方案与代码校验信息。更多说明见 [实验目录说明](experiments/README.md)。

## 补充材料

- [课件阅读与选题笔记](notes/课件阅读与选题.md)
- [早期 Markdown 稿](REPORT.md)与[扩写稿](REPORT_REVISED.md)
- [作业要求核查表](REQUIREMENTS_CHECK.md)与[历史文件核查记录](notes/archive/)
