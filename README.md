# 足球飞行模型与真实点球对照

当前分支使用 M1 重力、M2 重力与恒定阻力、M3 恒合力，以及 M4 重力、阻力和线性马格努斯力。M4 在单次飞行内保持 CD 与 alpha 恒定，CL=alpha Sp，自旋方向保持不变。

- 英文论文：paper/main.tex、paper/main.pdf。
- 中文论文：_中文版/main.tex、_中文版/main.pdf。
- 实测原始数据及选帧：data/current_report/。
- 模型与计算设置：configs/current_report.json、configs/sensitivity_v2.json。
- 正向、反演及阻尼结果：results/current_report/。
- 题目三点参考反演：results/structure_linear_spin/problem/。
- 单参数扫描：results/sensitivity_linear/。
- 图13的位置约束补充搜索：results/chapter5_review/fig13/，采用17×17组气动系数与33个自旋分量切片，共5049条满足约束的轨迹。
- 十万次联合扰动：results/monte_carlo_linear/。

## 重新计算

需要 Python 3.10+、XeLaTeX、Times New Roman；中文另用 SimSun、SimHei、KaiTi。

    python -m pip install -e ".[report,test]"
    ./scripts/reproduce_report.ps1 -Recompute

上述命令重算 24 条给定初态轨迹、三例共 12 组反演、阻尼与风估算、题目三点参考状态、九参数扫描、位置约束网格及十万条蒙特卡洛轨迹，随后生成图表、两版数值表及 PDF 并核查。默认不加 -Recompute 时复用指纹相同的反演和已保存的灵敏性结果；-RefreshFiguresOnly 刷新图表及论文。

只更新第五章：

    ./scripts/reproduce_sensitivity.ps1 -Recompute

脚本支持 -Python 指定解释器。科学计算与绘图分开，随机种子、输入、候选状态、数值积分核查和原始样本随结果保存。

## 数据与文章说明

三次真实点球共有 39 个源帧。WMX、WR9 选原第 3--5 点，WOH 选第 2--4 点，拟合时刻均为 0、0.04、0.08 s。源 CSV 保留原字节和来源署名：Deutsche Fußball Liga (DFL)，CC BY 4.0；Bassek 等 (2025)，DOI 10.1038/s41597-025-04505-y。

论文质量固定为 0.43 kg，半径固定为 0.11 m。写作修改依据见 [文章表述修改依据](docs/文章表述修改依据.md)，资料核查及内部说明见 [check.md](check.md)。复现步骤见 [论文说明](paper/README.md)，模型和结果见 [复算记录](docs/linear_spin_recalculation.md)，探索过程见 [探索树](探索树.html)。
