# 论文模板使用说明

暂定题目：**时序反事实增强：面向少样本双臂灵巧操作的协同敏感数据生成**。

## 文件结构

- `main.tex`：标题、摘要、关键词和总入口。
- `sections/01_introduction.tex`：问题矛盾、研究问题与贡献。
- `sections/02_related_work.tex`：模仿学习、数据生成、跨具身及时序增强。
- `sections/03_method.tex`：数学定义、核心算法、训练目标和整体图占位。
- `sections/04_experiments.tex`：RQ、基线、指标、表格和消融。
- `sections/05_conclusion.tex`：结论模板、局限和未来工作。
- `references.bib`：已核对的核心参考文献。

红色 `[TODO]` 表示必须由后续实验或投稿要求确定的内容。当前文字刻意区分了已实现模块与尚待验证的训练方案。

## 编译

建议使用 XeLaTeX：

```powershell
xelatex main.tex
bibtex main
xelatex main.tex
xelatex main.tex
```

如果本机尚未安装 TeX Live，可将整个 `paper` 文件夹上传到 Overleaf，并将编译器切换为 XeLaTeX。

## 下一步写作顺序

1. 先运行 50 条示范的敏感性实验，确定延迟和阶段网格。
2. 实现 Source Only、Random Delay、Positive Only 和完整方法四组最小训练对比。
3. 根据结果决定是否保留协同判别头；若没有显著收益，论文可收缩为“反事实筛选的数据增强”。
4. 增加第二个双臂任务后再定稿贡献范围。
5. 最后根据目标期刊替换文档类、页数和参考文献格式。

## 已实现与待实现边界

已实现：完整数据下载与校验、动作完整后缀延迟、物理回放、稳定保持检查、多示范批处理、断点续跑、配对统计和可视化。

待实现：关键实体接触图、反事实样本导出为策略训练格式、协同判别头、第二任务、完整少样本训练曲线和实机校准。论文正文中的红色标记必须在投稿前逐项关闭。

投稿前必须逐项通过 `SUBMISSION_READINESS.md` 中的证据门槛。论文文字完成不等于研究闭环完成。
