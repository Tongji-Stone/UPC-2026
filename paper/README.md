# 当前论文编译与复现

英文入口 `paper/main.tex`；中文入口 `_中文版/main.tex`。第四章分置于各版 `sections/model_solving.tex`；数值表 `report_results.tex` 由同一个脚本分别生成。正文的几何图、路线图及风洞对照在 `paper/assets/` 和 `paper/aerodynamics/`；全部当前数值图在 `results/current_report/figures/`。保持项目目录结构即可编译。

## 分步执行（仓库根目录）

```powershell
$env:PYTHONPATH="src;$env:PYTHONPATH"
python scripts/four_model_compute.py prepare
python scripts/four_model_compute.py forward
python scripts/four_model_compute.py inverse
python scripts/four_model_compute.py other
python scripts/four_model_compute.py collect
python scripts/four_model_plot.py
python scripts/four_model_paper_values.py
python scripts/four_model_verify.py
```

`inverse --case J03WMX` 可按事件计算。反演结果按输入及共享动力学/反演源码指纹缓存。原始 CSV 以字节哈希冻结；坐标转换、实际选帧和门线插值在 `data/current_report/inputs.json` 保存。外部原始目录缺席时使用随项目分发的冻结文件。

在各编译目录运行三遍：

```powershell
xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
```

之后在根目录运行 `python scripts/four_model_pdf_check.py`；中文分支另运行 `python scripts/verify_bilingual_reports.py`。后者比对展开的显示公式、引用键、表格数字和共享图路径，检查中文三种字体并渲染每一页。`scripts/package_report.py` 生成项目压缩包，排除构建缓存和 QA 页面图。

## 保存结果

- `forward/summary.json`：6×4 条航迹的设置、终止点、时间和流动覆盖范围；CSV 保存速度、自旋、系数和力。
- `inverse/<event>_<model>.json`：指定输入、分量边界、多初值、各阶段参数/目标、Jacobian、代表状态、收敛与触地状态。
- `inverse/*_validation.csv`：有效飞行区间内的后续实测点误差；`summary.json` 汇总 12 组。
- `other/summary.json`：24 m/s、10°、(0,0,35) rad/s 弧线球的力矩与风估算。
- `verification.json`、`bilingual_verification.json`、`pdf_verification.json`、`unit_tests.txt`：核验记录。

反演量依次为 3、4、7、8 项。初速度分量 vx∈[0,35]、vy/vz∈[−35,35] m/s，M4 自旋各分量∈[−20π,20π] rad/s，修正系数∈[0.5,1.5]。M3 的两个角定义单位自旋轴。按位置残差、系数接近一、M4 最小自旋选解；数值等价容差为 6×10⁻¹² m² 和 10⁻⁸。原始后续数据只评分。

当前正文无独立 4.3、旧比赛/题目数值算例或 Goff 正向实测对照；Goff 的研究背景引用仍保留。第三章 Asai 风洞对照与数据保持原有来源。第五章已完成题目三点参考算例的单参数响应、约束搜索和蒙特卡洛联合扰动。


第五章固定球体质量与半径，保留题目三点参考算例的九参数分析。设置、冻结参考状态、结果及程序分别位于原有 configs、data、results、scripts 目录；两版通过共享图路径引用六组图件。缓存重建使用 `./scripts/reproduce_sensitivity.ps1`，完整重算加 `-Recompute`。详见 [灵敏性分析与复现](../docs/灵敏性分析与复现.md)。

## 更正起点后的反演

原始两份 CSV 及来源说明保持字节不变。当前选帧以 `inputs.json` 和配置中的 `fit_sample_ordinals` 为准，原始 CSV 的汇总选帧字段保留其源信息。WMX/WR9 使用原第 3–5 点，WOH 使用原第 2–4 点；源时间起点依次平移 0.08、0.04、0.08 s。处理后的样本同时保存 `source_time_s`、新 `time_s`、原序号和当前选择标记；起点前样本的新时间为负，绘图从零时刻开始。

按需更新本次反演与图表：`inverse` → `collect` → `four_model_plot.py --inverse-only` → `four_model_paper_values.py`。每例正文使用实测数据表与模型状态/交点表，偏离距离为球门平面上的二维欧氏距离；不报告准确率。M3 自旋列为单位轴，M4 为 rad/s。

J03WR9 最新窗口为源帧176245、176246、176247，原始时间0.08、0.12、0.16 s；该例单独重算与作图使用 `four_model_compute.py inverse --case J03WR9` 和 `four_model_plot.py --inverse-only --case J03WR9`。
