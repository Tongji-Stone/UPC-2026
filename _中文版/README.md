# 中文版编译说明

本目录由修改后的完整英文 LaTeX 编译目录复制，正文、表格与图注译为中文，图内文字和路线图保留英文。数值、公式和引用编号与英文稿一致。

字体按原英文样式对应：普通正文译文使用宋体（SimSun），原加粗内容译文使用黑体（SimHei），原斜体内容译文使用楷体（KaiTi）。西文字母和数学符号保持原字体。

在本目录执行三次 `xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex`。需安装宋体、黑体、楷体和 Times New Roman。附录引用同一仓库 `../src/` 下的计算程序；图表均随本目录保存。

`translation_catalog.json` 记录英文源稿 SHA256 和段落译文；`archive/` 保留复制时的历史源稿。更新译文可在仓库根目录运行 `python scripts/build_chinese_report.py`，图像和路线图的英文标注保持不变。
