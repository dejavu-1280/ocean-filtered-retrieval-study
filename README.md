# 海洋时空过滤检索：提前尾段缩批实验

公开仓库：[https://github.com/dejavu-1280/ocean-filtered-retrieval-study](https://github.com/dejavu-1280/ocean-filtered-retrieval-study)

- **[实验报告](REPORT.md)**：创新点拆解、三轮迭代、完整结果、局限及复现入口。
- **[完整AI协作聊天记录](collaboration/chat.md)**：原始对话顺序，含学生的质疑、取舍与阈值8选择。
- [实验代码与结果](experiments/)：13500个合成查询、67500条配对观测；15项正确性测试。
- [课件阅读与选题笔记](notes/课件阅读与选题.md)。
- **[按教师要求交叉核查](REQUIREMENTS_CHECK.md)**：逐项证据、核查边界与剩余局限。

本项目是合成候选流机制实验，不声称已验证真实海洋数据或ANN性能。学生选定阈值8，AI提出具体尾批32并实现；贡献详见报告第9节。公开材料不含原始课件、视频、账户凭据或应用私有日志。

```bash
python -m pip install -r experiments/requirements.txt
python -m unittest discover -s experiments -p "test_*pilot.py"
```

查看每轮`manifest.json`可核对环境、种子、冻结方案和结果校验和。第二、三轮不覆盖旧输出；复现实验请使用独立副本。

聊天为持续更新快照，截止消息数见`collaboration/export_manifest.json`；发布回执可能晚于当前导出截止时间。

在保有原始Codex会话日志的本机，可运行 `python tools/export_chat.py` 更新聊天快照；公开仓库本身不包含应用原始日志。导出会保留可见提问工具的问题参数，排除其他工具执行日志。
