# 足球三力模型：正向算例与三次真实点球

主模型使用重力、阻力和 Magnus 升力，保持自旋恒定、无风、球形几何。四模型 M1–M4 分别使用重力、恒定阻力、恒定阻力与升力、完整 Kiratidis–Leinweber 系数。正向修正系数为 1，反演使用论文列明的有界分级选解。

- 英文 PDF / LaTeX：`paper/main.pdf`、`paper/main.tex`。
- 中文 PDF / LaTeX：中文版分支的 `_中文版/main.pdf`、`_中文版/main.tex`。
- 当前数据与来源：`data/current_report/`；配置：`configs/current_report.json`。
- 当前结果、候选、图表与核验：`results/current_report/`。
- 两版共用 `paper/aerodynamics/`、`paper/assets/` 和当前结果图目录，图中文字为英文。

## 计算内容

第四章 4.1 给定五类、六组初始状态，直接计算 24 次正向飞行。4.2 使用三次真实点球 J03WMX、J03WOH、J03WR9 的 39 个原始帧；前三个指定位置反演，其后位置评分。坐标转换为 x=X−41.5、y=Y、z=Z原值，球门 x=11 m。WR9 采用非等间隔 0、0.08、0.12 s，保留重复帧。第五章已完成题目三点参考算例的灵敏性与联合扰动分析。第六章以正向弧线球比较旋转阻尼，并估算风的作用。

源数据署名 Deutsche Fußball Liga (DFL)，CC BY 4.0；引用 Bassek 等 (2025)，DOI 10.1038/s41597-025-04505-y，官方数据 DOI 10.6084/m9.figshare.28196177。逐帧来源及冻结版本见数据目录说明。

## 复现

需要 Python 3.10+、XeLaTeX、Times New Roman；中文另需 SimSun、SimHei、KaiTi。

```powershell
python -m pip install -e '.[report,test]'
./scripts/reproduce_report.ps1
```

仅刷新图表和编译：`./scripts/reproduce_report.ps1 -RefreshFiguresOnly`。脚本支持 `-Python '解释器完整路径'`。反演按源码及输入指纹缓存；相关源码变化时自动重算。计算、制图、数值表生成分开执行。

逐步命令、指标和文件索引见 [复现说明](paper/README.md) 和 [计算记录](docs/报告结构与四模型重算.md)。核验命令 `python -m unittest discover -s tests -v`。探索过程见 [探索树](探索树.html)。

## 版本

英文分支 `codex/report-english-20261108`，中文分支 `codex/report-chinese-20261108`。中文正文宋体、粗体黑体、斜体楷体；公式、数值和共享英文图表同步核验。旧的当前报告算例和重复编译资源已删除，旧稿通过 Git 历史回溯。`results/coupled_model/` 等独立历史研究保留，coupled 系列入口只服务对应历史材料。


第五章固定球体质量与半径，保留题目三点参考算例的九参数分析。设置、冻结参考状态、结果及程序分别位于原有 configs、data、results、scripts 目录；两版通过共享图路径引用六组图件。缓存重建使用 `./scripts/reproduce_sensitivity.ps1`，完整重算加 `-Recompute`。详见 [灵敏性分析与复现](docs/灵敏性分析与复现.md)。
