# 中文版

入口 `main.tex`，XeLaTeX 编译三遍。正文宋体（SimSun），粗体黑体（SimHei），斜体楷体（KaiTi）；英文及数学保持现有字体，图内与路线图标注使用英文。

第四章译文为 `sections/model_solving.tex`。数值表由 `scripts/four_model_paper_values.py` 与英文版同时生成；两版直接引用同一套图表和风洞材料。翻译校验不依赖旧逐段 SHA 锁定，改由 `scripts/verify_bilingual_reports.py` 比较展开公式、引用及表格数字，并检查 PDF 字体、引用、页面和共享图路径。

完整计算和编译步骤见 `../paper/README.md`；运行 `../scripts/reproduce_report.ps1` 可同步刷新两版。旧稿通过 Git 历史回溯。
