# 足球三力模型与四类模型对照

> 当前分支为中文版。中文 PDF 和 LaTeX 位于 [_中文版/](./_中文版/)，英文稿保留在 [paper/](paper/)。普通正文译文为宋体、原粗体译文为黑体、原斜体译文为楷体；图和路线图保留英文。

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

## 中英文论文版本

英文稿位于 `paper/`，分支为 `codex/report-english-20261108`。中文版位于单独分支 [`codex/report-chinese-20261108`](https://github.com/Tongji-Stone/UPC-2026/tree/codex/report-chinese-20261108/_%E4%B8%AD%E6%96%87%E7%89%88)，编译目录名为 `_中文版`。正文样式对应宋体、黑体和楷体，图与路线图保留英文。详见 [中英版本说明](docs/中英版本说明.md)。
