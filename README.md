# 足球三维轨迹预测

项目从球心位置观测出发，计算足球在指定平面的预测位置。代码分为正向物理仿真、简化模型、参数反演、数据处理和评价模块。当前阶段的计算结果与图分开保存。

## 环境与运行

需要 Python 3.10 以上、NumPy、SciPy、Matplotlib、Pandas 和 pytest。在仓库根目录的 PowerShell 中：

```powershell
python -m pip install -e . pytest
python -m pytest -q
python scripts/predict_problem_b.py
python scripts/plot_problem_b.py
python scripts/predict_observations.py configs/problem_b.json --model M3
python scripts/predict_physical_probability.py --samples 5000
python scripts/plot_physical_probability.py
python scripts/validate_synthetic_probability.py --cases 20 --samples 500
python scripts/plot_calibration.py
```

题目案例的计算输出在 `results/problem_b.json` 和 `results/prediction_*.npz`；绘图脚本读取这些中间结果。自定义输入格式见 `configs/problem_b.json`，位置单位为米，时间为秒，角速度为弧度每秒。自定义物理反演当前估计初速度，给定自旋和气动参数，并输出首次到达平面或触地的事件。

## 已实现的方法

`football.physics` 的统一方程支持 M0、M1、M3、M4、M5 的受力组合及连续事件检测。M5 可选择 Linthorne–Patel 论文系数关系，也可传入实测系数表；默认参数仍为常数。M2 是独立的匀加速度拟合，至少需要三个观测点。`football.inference.physical_fit` 使用固定物理配置和自旋估计初速度；`football.inference.kinematic` 则用带先验的匀加速度模型产生题目案例的概率预测，两者是不同方法。

`football.inference.physical_probability` 使用重要性采样，在论文气动关系下同时考虑速度、自旋和阻力参数的不确定性。先验、误差假设、样本有效数量和合成覆盖率检查见 `docs/概率预测与验证.md`。DFL 真实数据验证及复现方法见 `docs/数据与验证阶段报告.md`。

落点概率结果以采样总数为分母，同时记录先到达预测平面的样本数、球心在门框内的样本数、球完整通过门框的样本数。分布、均值和区域只针对先到达平面的样本。预测区域采用样本协方差椭圆，边界由样本马氏距离的 68% 和 95% 分位数确定。

方法、假设与进度见 `docs/`。真实轨迹验证和完整模型比较的进度以其中记录及实际结果为准。
