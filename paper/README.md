# 论文编译与复现

英文入口为 paper/main.tex，中文入口为 _中文版/main.tex。两版各自只有一个 main.tex，内嵌全部章节、数值表定义、参考文献、TikZ 路线图和附录代码；无外部 tex 或代码摘录依赖。数值更新脚本直接写入 main.tex 中的注释标记区，不再生成子 tex 文件。图件共用 paper/assets/、paper/aerodynamics/、results/current_report/figures/ 和 results/sensitivity_linear/figures/。

## 完整运行

仓库根目录执行：

    python -m pip install -e ".[report,test]"
    ./scripts/reproduce_report.ps1 -Recompute

默认运行复用与输入和源码指纹相同的反演缓存；-Recompute 强制重新反演并运行全部灵敏性计算。-RefreshFiguresOnly 复用数据更新图表、数值表与 PDF。-Python 可指定解释器路径。

分步运行计算：

    python -B scripts/four_model_compute.py prepare
    python -B scripts/four_model_compute.py forward
    python -B scripts/four_model_compute.py inverse --force
    python -B scripts/four_model_compute.py other
    python -B scripts/four_model_compute.py collect
    python -B scripts/chapter4_compute.py
    python -B scripts/sensitivity_reference_compute.py
    python -B scripts/sensitivity_v2_compute.py
    python -B scripts/sensitivity_v2_check.py
    python -B scripts/sensitivity_monte_carlo_compute.py

以上命令需把 src 加入 PYTHONPATH。inverse --case J03WMX --force 可单独重算一个事件。绘图和数值表生成分别使用 four_model_plot.py、four_model_paper_values.py、build_sensitivity_assets.py。

各编译目录执行三次：

    xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex

## 模型和核查

M3 解出三维恒加速度，六个反演量；M4 采用恒定 CD、CL=alpha Sp，以 30 rad/s 为自旋参考模长，拟合三维速度、两个方向角和两个系数，共七个量。M4 采用六组确定性初值，选位置残差最小者。速度分量及系数范围随输入保存；后续位置用于预测比较。

真实点球源帧：WMX 为 152602--152604，WOH 为 128955--128957，WR9 为 176245--176247。源时间起点分别为 0.08、0.04、0.08 s，均换算为拟合时刻 0、0.04、0.08 s。

four_model_verify.py 核查输入、源帧、拟合、后续评分及物理恒等式；four_model_pdf_check.py 检查编译、字体与页面边界；verify_bilingual_reports.py 比较两版公式、引用和数值表；verify_sensitivity_integration.py 核查线性模型的第五章数据、图件、数字与引用。

package_report.py 生成完整项目包及散列清单，排除缓存、编译辅助文件和 QA 页面图。写作规则和内部资料核查分别保存在 docs/文章表述修改依据.md、check.md。

## 排版与示例照片

目录与球门交点误差表采用正文的 `normalsize`（12 pt）。两张用户提供的射门照片保存在 `assets/`，来源文件与SHA256见 `shot_photo_sources.json`。照片在案例分析开头组成等宽等高的左右子图，分别展示精准推射与大力射门；各例轨迹图独立排列。大力射门四面板图采用 2×2 排列、加宽面板间距及放大的标注；两次精准推射三维图左右并排，可用 `python scripts/four_model_plot.py --placement-only` 从现有结果生成。接缝球示意与六种足球表面细节采用左右子图，共用图号；旋转阻尼小节保留模型来源与物理结论，数值沿用既有计算。

第八章按“Model Strengths / Model Weaknesses”重写，中文对应“模型优点 / 模型缺点”，两版保持相同论述结构。

最终排版核验：`results/current_report/layout_revision_verification.json` 记录两版12 pt字号、子图编号和第八章结构；`pdf_verification.json`、`bilingual_verification.json` 保存编译、引用及字体核查。当前英文成品为 `main.pdf`，旧备用构建 `main_local.pdf` 已移除。

## 单文件 LaTeX

分别进入 paper/ 与 _中文版/，运行三遍 `xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex` 即可。图片仍引用项目内共享文件，全部正文均可在各自 main.tex 中直接编辑。注释标记用于定位自动生成的数值表区域，不是外部模块。核查记录见 results/current_report/single_tex_verification.json。

## 面向评委的叙述与引用

两版重写问题背景、完整赛题重述和物理假设，保留四模型及全部计算结果。阻力与马格努斯力各增加无编号推导，最终式（3）至式（7）保持不变。正文明确介绍附录数据来源及表格；所有实际出现的图表均在正文引用，参考文献均在正文使用。未调用的分案例重复表格宏已从生成脚本删除。

仓库内运行 `python scripts/verify_report_narrative.py`，可核对实际编译图表的正文引用、文献使用、假设术语、单文件结构、路线图，以及相对 d86d90c 的物理公式和原始数值结果；同时核对已确认提交30d0dea中的摘要、第五章分析、第八章和图13复算结果得到保留。第五章开头改为引用第四章题给算例。结果保存于 results/current_report/narrative_verification.json。

## 第四章两类点球对照

当前章节、最终图件布局、题设重算与核验入口见 [第四章两类点球对照](../docs/第四章两类点球对照.md)。新增 `chapter4_compute.py` 重新核验题设 M4；`four_model_plot.py --chapter4-only` 仅重画第四章；`verify_chapter4.py` 执行 101 项源文件与数值检查。最终在编辑器编译中英文 `main.tex`，不以旧导出 PDF 作为本轮编译依据。

2026-11-09合并后已重新导出并核对中英文PDF，分别为29页和31页。题给位置与反演状态在第四章呈现，第五章引用该结果；新版发布核对记录见 `results/current_report/github_publication_verification.json`。

## 第六章简化假设检验

第六章改用题设三点在固定 Cangular=1.5 下的七参数旋转阻尼反演，以及5 cm交点判据下的风速界限。数据、图表及核验集中在 `results/chapter6/`，独立复现入口为 `scripts/reproduce_chapter6.ps1`；详见 [复现说明](../docs/第六章简化假设检验与复现.md)。旧自设弧线球阻尼图和24 m/s风速表退出正文。
