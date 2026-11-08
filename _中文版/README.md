# 中文版

入口 `main.tex`，XeLaTeX 编译三遍。正文宋体（SimSun），粗体黑体（SimHei），斜体楷体（KaiTi）；英文及数学保持现有字体，图内与路线图标注使用英文。

第四章译文为 `sections/model_solving.tex`。数值表由 `scripts/four_model_paper_values.py` 与英文版同时生成；两版直接引用同一套图表和风洞材料。翻译校验不依赖旧逐段 SHA 锁定，改由 `scripts/verify_bilingual_reports.py` 比较展开公式、引用及表格数字，并检查 PDF 字体、引用、页面和共享图路径。

完整计算和编译步骤见 `../paper/README.md`；运行 `../scripts/reproduce_report.ps1` 可同步刷新两版。旧稿通过 Git 历史回溯。


第五章固定球体质量与半径，保留题目三点参考算例的九参数分析。设置、冻结参考状态、结果及程序分别位于原有 configs、data、results、scripts 目录；两版通过共享图路径引用六组图件。缓存重建使用 `./scripts/reproduce_sensitivity.ps1`，完整重算加 `-Recompute`。详见 [灵敏性分析与复现](../docs/灵敏性分析与复现.md)。

三次点球的起始帧已更正；三例拟合时刻均为 0、0.04、0.08 s。原汇总 Table 8 由各例的实测表和模型反演/预测表替代，交点指标为偏离距离（m）。
