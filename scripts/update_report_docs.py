"""Refresh current reproduction notes and the exploration tree from cached results."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/structure_v2'
def js(p):return json.loads((OUT/p).read_text(encoding='utf-8'))
root_readme='''# 足球三力模型与四类模型对照

当前论文以恒定自旋、无风的三力模型为主线：重力、空气阻力和 Magnus 升力。M1 仅含重力，M2 加入恒定阻力系数，M3 使用恒定阻力和升力系数，M4 使用 Kiratidis–Leinweber 完整经验式。正向计算的两项力修正系数均为 1；逆向计算根据三个早期位置估计初始运动和相应修正系数。

报告分八章，第五章灵敏性分析留待完成。旋转阻尼放在第六章，以题目反演状态作相同初始条件的对照。当前结果目录为 `results/structure_v2/`，PDF 和 LaTeX 位于 `paper/`。

## 快速使用

需要 Python 3.10+、XeLaTeX 和 Times New Roman 字体。在仓库根目录安装依赖：

```powershell
python -m pip install -e '.[report,test]'
./scripts/reproduce_report.ps1 -RefreshFiguresOnly
```

完整计算并编译使用 `./scripts/reproduce_report.ps1`。脚本支持 `-Python '解释器完整路径'`。逆向计算逐案例缓存；重算时先将对应案例 JSON/CSV 移到存档目录。逐步命令见 [论文复现说明](paper/README.md)。

自定义三点反演与测试：

```powershell
$env:PYTHONPATH='src'
python scripts/predict_observations.py configs/problem_b.json --model M4
python -m pytest -q
```

## 数据与计算

受控实验来自 Goff–Carré 2009：一个具有实测落距的无旋转案例，以及四组旋转轨迹片段。实测标记直接从原 PDF 提取，标定和原始点保存在 `data/report_v2/`。五个比赛案例沿用固定的既有筛选结果；仅前三帧进入反演，后续坐标用于球门交点比较。

反演按位置残差、修正系数接近 1、M4 自旋最小的顺序选解。M1 估计 3 项，M2 估计 4 项，M3 估计 7 项，M4 估计 8 项。M3 的自旋模长不参与恒定升力系数计算。选择容差、初值、阶段结果和 Jacobian 奇异值均保存于案例 JSON。

计算、绘图和正文数值生成分离；图表导出 PDF、SVG 和 300 dpi PNG。论文数字由结果文件生成。结果摘要见 [重构与计算记录](docs/报告结构与四模型重算.md)。

## 历史材料

`results/coupled_model/` 和其他旧目录保持原样，记录此前包含旋转阻尼的探索。M5 和 coupled 系列脚本用于该历史版本；本次论文使用 four_model 系列入口。旧版源稿保存在 `paper/archive/`，完整重构前存档位于项目同级压缩包。
'''
paper_readme='''# 论文编译与复现

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
'''
def main():
    r=js('problem/problem_b_M4.json')['record'];e=r['event'];o=js('other/summary.json')
    matches=js('matches/summary.json')['records']
    summary=f'''# 报告结构与四模型重算

本次报告重组为八章，主模型采用恒定自旋三力方程，旋转阻尼移入第六章，第五章灵敏性分析待做。Introduction 保留主体内容，1.2 增加章节导读。

题目 M4 初速度为 {r['initial_state'][:3]} m/s，自旋为 {r['initial_state'][3:]} rad/s，两项力修正为 {r['drag_scale']:.6f}、{r['lift_scale']:.6f}。球门交点为 ({e['position'][1]:.6f}, {e['position'][2]:.6f}) m，时间 {e['time']:.6f} s。详细残差和分级选解记录保存在 problem 案例 JSON。

受控无旋转实测落距 21.9 m，M4 预测 21.871 m。旋转实验仅比较已公开的空间轨迹片段；原 PDF、实测标记、坐标标定及制图代码均随项目保留。

相同初始条件加入二次旋转阻尼后，球门交点移动 {o['goal_displacement_m']:.6f} m，为 11 m 距离的 {o['displacement_pct_of_11m']:.3f}%；自旋减少 {o['spin_loss_pct']:.3f}%。黏性/惯性力矩比约 {o['viscous_to_inertial_torque_ratio_at_launch']:.3g}。正文按实际结果陈述其影响。

比赛对照逐项记录所有五个案例和四类模型，包括触地、提前终止与拟合失败。后续帧只用于验证目标。原有耦合模型结果通过 SHA256 检查保存原样。

## 反演选解

先最小化两次位置的六个坐标残差，再选择修正系数最接近 1 的解；M4 在等价解中选自旋最小者。位置目标允许差额 6e-12 m²，系数目标允许差额 1e-8。M3 用单位旋转轴表示方向，不将其单位模长解释为实测转速。

## 复现文件

输入位于 data/report_v2；结果位于 results/structure_v2；数值宏为 paper/report_results.tex。four_model_compute 计算，four_model_plot 制图，four_model_paper_values 更新正文数字，four_model_verify 核验。详见根目录和 paper 目录 README。
'''
    for m in ['M1','M2','M3','M4']:
        rs=[x for x in matches if x['model']==m];n=sum(x['status']=='plane' for x in rs)
        summary+=f'\n{m}：五个案例中 {n} 个到达平面。\n'
    (ROOT/'README.md').write_text(root_readme,encoding='utf-8')
    (ROOT/'paper/README.md').write_text(paper_readme,encoding='utf-8')
    (ROOT/'docs/报告结构与四模型重算.md').write_text(summary,encoding='utf-8')
    tree=ROOT/'探索树.html';s=tree.read_text(encoding='utf-8')
    if '<!-- report-v2 -->' not in s:
        node=f'''<!-- report-v2 --><article class="node"><span class="tag">当前报告</span><h2>恒定自旋三力与四模型对照</h2><p>按八章重构，M1–M4 从重力逐步加入恒定及变化的气动力。正向与逆向计算共用动力学；反演加入两项非负力修正并按分级规则选解。题目 M4 交点 ({e['position'][1]:.3f}, {e['position'][2]:.3f}) m。</p><div class="children"><article class="node"><h2>分层实测对照</h2><p>公开受控实验：1个实测落距案例、4组旋转轨迹；比赛：4个固定事件和1个点球，前三帧拟合、后续验证。</p></article><article class="node"><h2>省略因素与待做工作</h2><p>表面几何按文献定性分析；同状态旋转阻尼使交点移动 {o['goal_displacement_m']:.3f} m；风作动压估算。第五章灵敏性分析待做。</p></article></div><p><a href="docs/报告结构与四模型重算.md">结构与结果</a> · <a href="paper/main.pdf">当前PDF</a> · <a href="results/structure_v2/verification.json">验证记录</a></p></article>'''
        s=s.replace('<div class="tree">','<div class="tree">'+node,1)
        s=s.replace('当前主模型','此前耦合模型记录')
    tree.write_text(s,encoding='utf-8');print('reproduction notes and exploration tree updated')
if __name__=='__main__':main()
