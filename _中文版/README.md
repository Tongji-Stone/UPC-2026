# 中文论文

唯一入口 main.tex，全部正文、表格定义、参考文献、TikZ 路线图及附录代码均直接包含于本文件，不引用其他 tex 文件。数值更新脚本直接刷新 main.tex 中的标记区域，与英文版由相同结果生成，图件直接引用共享目录。正文使用宋体，粗体为黑体，斜体映射为楷体，西文使用 Times New Roman。

在仓库根目录运行 ./scripts/reproduce_report.ps1 -Recompute，可重新计算并生成中英文 PDF。只重算第五章使用 ./scripts/reproduce_sensitivity.ps1 -Recompute。各编译目录执行三遍 XeLaTeX，随后进行双语、数据和 PDF 核查。

当前 M3 为恒合力模型，M4 采用恒定阻力和线性升力。三次真实点球的源帧、输入、反演状态及后续误差随 results/current_report/ 保存；题目三点的灵敏性与蒙特卡洛结果分别保存于 results/sensitivity_linear/、results/monte_carlo_linear/。

完整说明见 ../paper/README.md。表述规则见 ../docs/文章表述修改依据.md，内部资料核查见 ../check.md。

两版目录和误差汇总表统一为正文 12 pt。射门照片并排展示，精准推射增加双例轨迹合图，大力射门保留加宽间距的四面板图。几何比较图使用左右子图，第八章按模型优点和缺点组织。图源记录见 paper/assets/shot_photo_sources.json，排版核查见 results/current_report/layout_revision_verification.json。

本次叙述修订同步英文稿：背景仅介绍点球和研究方向；问题重述完整覆盖题目 B，删除三阶段划分；基本假设只描述物理条件。新增短推导和符号解释，最终力学关系及数值结果保持不变。实际图表与参考文献的正文引用核查见 results/current_report/narrative_verification.json。
