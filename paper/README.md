# 论文编译

在仓库根目录的 PowerShell 中运行：

```powershell
cd paper
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
```

`main.tex` 使用项目 `results/` 中已保存的轨迹与敏感性图，并在附录读取 `scripts/fit_real_penalty.py`。修改数值结果后，先在仓库根目录按需运行相应计算与绘图脚本，再编译论文。
