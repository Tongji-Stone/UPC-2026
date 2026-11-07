# 论文编译与复现

当前入口为 `main.tex`，使用 XeLaTeX、Times New Roman 和 TikZ。应保留完整目录：正文引用 `report_results.tex`、`aerodynamics/`、`assets/`、`../results/structure_v2/figures/`、几何图和共享动力学代码。

## 编译已有论文

在 paper 目录执行三次：

```powershell
xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex
```

## 逐步复现

在仓库根目录安装 `python -m pip install -e '.[report,test]'`，随后执行：

```powershell
$env:PYTHONPATH='src'
python scripts/four_model_compute.py prepare
python scripts/four_model_compute.py forward
python scripts/four_model_compute.py problem
python scripts/four_model_compute.py matches
python scripts/four_model_compute.py other
python scripts/four_model_refresh_traces.py
python scripts/four_model_plot.py
python scripts/four_model_paper_values.py
python scripts/four_model_verify.py
python -m pytest -q
```

也可运行 `./scripts/reproduce_report.ps1` 完成计算、绘图、核查和编译。`-RefreshFiguresOnly` 从缓存结果更新图表及 PDF。逆向计算跳过已有 JSON；修改模型、拟合或输入后，先归档相关案例 JSON/CSV，再重算。

## 数据和来源

- `data/report_v2/Goff_Carre_2009.pdf` 为受控实验来源；`digitization.json` 记录页码、图号、坐标标定及源文件 SHA256。五个 CSV 保存原图红色实测标记。
- 无旋转算例采用文献约 18 m/s、22° 的初始条件和 21.9 m 实测落距。旋转算例由公开 Re、Sp 和早期轨迹切线重建初始条件，比较空间轨迹片段。
- `match_cases.json` 冻结四个既有事件和一个点球的完整坐标及验证目标。拟合接口只接收前三帧，采用真实的 0、0.04、0.08 s 采样时刻。
- `configs/four_model_problem_b.json` 定义题目输入，`configs/problem_b.json` 为相同内容的便捷入口。

## 图表与结构

第三章为几何、三力和总动力学方程；第四章比较正向和逆向计算；第五章留待完成；第六章讨论表面、旋转阻尼和风；第七、八章为结论与评价。

技术路线图由 `assets/workflow_tikz.tex` 直接绘制，保留暖橙色配色、无紫色。可在 assets 目录编译独立的 `workflow_vector.tex`。2007 年 CD、CL 两图各有两条曲线，数据和复现方法位于 `aerodynamics/`。

新结果在 `results/structure_v2/`；论文数值宏由 JSON 生成，绘图读取缓存结果。此前耦合模型目录保持原样。

## 本次编辑修订

Figure 1 已移除底部三力文字条；CD、CL 的经验式及参数解释收入加粗物理量开头的 enumerate 条目，随后仅保留精简风洞对照。完整中文翻译见单独的中文版分支，字体与复现约定见 `../docs/中英版本说明.md`。
