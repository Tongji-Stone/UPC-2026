# 论文编译与复现

英文入口为 paper/main.tex，中文入口为 _中文版/main.tex。两版分别维护正文、sections/model_solving.tex 和 sensitivity.tex；report_results.tex 与 sensitivity_results.tex 由相同结果生成。图件共用 paper/assets/、paper/aerodynamics/、results/current_report/figures/ 和 results/sensitivity_linear/figures/。

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
