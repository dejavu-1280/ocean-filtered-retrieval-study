# 海洋时空过滤检索：候选数量的自适应调整

当前完成到阶段 1：三轮探索性机制实验。尚无真实海洋数据、ANN 引擎性能结论、正式报告或公开仓库链接。

学生已选定题目，并选择“同样可靠地拿够 10 条时，怎样减少扫描”为优先问题；随后质疑“只差 1 条仍取 128 条”，并确认“担心缩批的代价，仍优先减少检查数”。尾段缩批方向来自这段讨论，具体算法、32 条参数和实现由 AI 起草；贡献范围与原话见第二轮记录。

先读 [第一轮结果与解释](PILOT_FINDINGS.md) 和 [实验方案](PROTOCOL.md)。本阶段 `checked` 仅为检查过的候选个数，不能当作真实向量距离计算数或毫秒延迟。模拟假定前缀可以复用，真实引擎未必如此。

第二轮见 [尾段缩批结果与过程记录](TAIL_FINDINGS.md) 和 [v0.2 方案](PROTOCOL_V02.md)：使用 4500 个新查询，六种方法配对比较，保留第一轮全部产物。

第三轮由学生选择“找到8条就缩批”，见 [提前触发结果](EARLY_FINDINGS.md) 和 [v0.3方案](PROTOCOL_V03.md)。使用4500个新查询，对比固定128、固定32、阈值9和阈值8；程序为 `run_early_pilot.py`，结果位于 `results/pilot_v03/`，同样拒绝覆盖旧结果。

本机已存在的 Python、NumPy、SciPy 即可运行；没有安装或改动系统环境。

```powershell
py -m unittest discover -s filtered_retrieval -p 'test_*pilot.py'
py filtered_retrieval/run_pilot.py
py filtered_retrieval/run_tail_pilot.py
```

结果位于 `results/pilot_v01/`：逐查询明细、分场景汇总、随机序列指纹、环境与代码校验和。相同代码允许复跑，若改代码必须另存版本，避免抹掉旧结果。

第二轮结果位于 `results/pilot_v02/`，脚本会拒绝覆盖已有结果。独立复现第二轮时使用不含该结果目录的项目副本；不要为了复跑删除原始实验记录。

聊天原文记录在工作区的 `study_workspace/collaboration/chat.md`，由该目录下的导出工具持续更新。最后回复要等本轮结束落盘后再导出。

项目流程使用了 experimental-design 与 scientific-critical-thinking 技能，方法辅助文献已列入实验方案；它们不是检索算法的原创性依据。
