# 电脑 C：数据接口与复现

足球追踪数据按帧给出位置。验证时把前几帧交给预测器，再用后面的真实记录检查落点。两部分通过独立接口传递，模型之间共用一份固定样本清单。

本次工作在 `codex/data-validation`，从 `main` 的 `af7ef79` 建立分支并合入 `codex/collaboration-tasks` 的 `3a4b621`。新增内容集中于数据与评价模块；物理与反演模块继续使用仓库已有实现。公共文件仅增加探索树中的数据验证节点。

## 直接核验已提交的处理结果

在仓库根目录打开 PowerShell：

```powershell
$env:PYTHONPATH='src'
python -m pytest -q --basetemp=.pytest_tmp
python scripts/benchmark_data_validation.py
python scripts/plot_data_validation.py
python scripts/validate_data_protocol.py
```

默认读取 `data/processed/data_validation/manifest.json` 与 `selected_tracks.csv`。无需重新下载大型原始文件。真实结果写入 `results/data_validation/`，合成结果写入 `results/data_validation_synthetic/`，绘图只读取已保存的结果。

依赖沿用 `pyproject.toml`，缺少时运行 `python -m pip install -e . pytest`。实际使用的 Python、NumPy、SciPy 版本和计算开始时的 Git 提交号在真实结果 `summary.json` 的 `configuration` 中。

## 从公开原始文件复现

```powershell
python scripts/download_validation_data.py --source mirror --workers 16
$env:PYTHONPATH='src'
python scripts/prepare_validation_data.py data/raw/data_validation/DFL_04_03_positions_raw_observed_DFL-COM-000002_DFL-MAT-J03WOH.xml --z-scale 1
python scripts/benchmark_data_validation.py
python scripts/plot_data_validation.py
```

也可用 `--source figshare` 从官方文件地址获取。本次官方 API 正常，整文件下载流停滞，改用公开镜像的分块请求。程序先核对官方公布的 348,945,715 字节和 MD5，再写入最终原始文件，并保存 SHA256、实际地址、镜像提交版本和获取时间。原始 XML 留在 `data/raw/data_validation/`，该目录由仓库原有规则忽略。

`--z-scale 1` 是显式的高度换算假设。论文明确 X、Y 使用米，Z 称为球高；本次同时核对的 kloppy Sportec 解析器直接读取 Z。正式的 Z 单位及球心参考定义仍需数据提供方确认。程序保留原始 Z，不通过轨迹结果反向调整换算比例。

## 数据格式和固定规则

`selected_tracks.csv` 每行保存 `sample_id, source_frame, source_timestamp, t_s, x_m, y_m, z_m`。`t_s` 为当前片段相对首帧的真实时间差，原始时间戳和帧号另列保留。X、Y 平移到首帧水平位置，再按前两帧水平位移旋转：x 沿早期运动方向，y 向其左侧，z 保留原始高度。

`manifest.json` 保存原始文件校验值、样本编号、源行范围、变换方向、平面种类及参考答案。普通飞行样本的平面标为 `virtual`，距首帧前方 11 米。它们按比赛原始顺序选取，无真实点球球门标签。

筛选规则写入 `SelectionConfig` 并随清单保存：连续 21 帧、帧号相邻、间隔 0.04 秒、全程比赛进行中；球高在 0.3–15 米之间、逐帧速度为 2–45 m/s、相邻速度变化对应加速度不超过 80 m/s²、首两帧水平位移至少 0.2 米；0.10 秒后存在由后续帧夹住的前向穿越。选中后至少跳过 50 个源行，按 25 Hz 对应首帧间隔 2 秒，同时保持片段不重叠。检查到前 30 个合格片段后停止。

`selection_audit.csv` 记录扫描范围内每个起点的首次排除原因，以及间隔跳过的起点；未扫描的尾部数量另列。完整片段只用于筛选和答案生成，预测器仅收到截断后的输入。此次样本是符合规则且有穿越答案的普通飞行片段；下一步可结合比赛事件进一步确认片段间的独立性和中途触球。

0.05 秒窗口使用 0、0.04 秒两帧；0.10 秒窗口使用 0、0.04、0.08 秒三帧。输入不插值。答案由 0.10 秒之后的两帧线性求交，两个窗口共用同一答案。

## Python 接口

```python
from football.data.validation import early_observations
from football.data.ball3d import load_ball3d_tracks
from football.evaluation.benchmark import Prediction, run_benchmark, summarize_benchmark

observed_t, observed_p = early_observations(times, positions, duration=.05)
tracks = load_ball3d_tracks('track/ball_3d-gt.csv', 'sequence_metadata.json')

def predictor(request, rng):
    # request.times_s: (N,), seconds; request.positions_m: (N,3), metres
    # request.cutoff_s: decision time; request.plane_x_m: prediction plane
    # Neither the full trajectory nor the answer is present in request.
    return Prediction(status='plane', yz_m=[1.0, 2.0], crossing_probability=1.0)

records = run_benchmark(samples, {'model_name': predictor}, seed=20261107)
summary = summarize_benchmark(records)
```

每个 `samples` 元素有 `sample_id, times, positions, truth_yz_m`；真值未穿越时 `truth_yz_m=None`。时间可以保留非零首时刻，两个窗口从首时刻起算。每次调用预测器时复制输入并设为只读，按样本编号、模型名、窗口和总种子生成独立随机数流。

`Prediction.status` 可取 `plane, ground, none, insufficient_observations`。成功穿越提供二维 `[y,z]`。可选 `crossing_probability` 表示包含未穿越样本在内的事件概率；可选 `samples_yz_m` 是穿越条件下的等权落点样本。异常单独记为 `error`，保留异常类型与信息。

`football.evaluation.predictors.physical_predictor('M0' ... 'M5')` 对接已有模块，统一拟合窗口内初速度，预测至 2 秒或首次事件。M2 至少需要三帧；M4、M5 固定竖直自旋 30 rad/s。M4 使用 Cd=0.25、Cl=0.2，M5 使用已有 Linthorne–Patel 关系且 Cd0=0.18。它们的配置固定，不按测试答案选择。

`gravity_ensemble(sigma_m=.01, samples=256)` 提供附加的 M1 测量误差传播基线：只扰动已观测位置，再拟合初速度并解析求交。误差为每轴独立高斯、标准差 0.01 米；预测平面与坐标方向固定。统计所有 256 次试验的穿越比例，落点云仅保留先到平面的样本。

## 评价口径

二维欧氏误差汇总平均值、中位数和 90% 分位数，单位为米。每组同时列出总例数、真实穿越数、预测穿越数、事件分布和有效配对数；共同样本表另取当前窗口可运行模型成功穿越的交集。M2 的两帧不足按观测不足保留。

`energy_score(samples, truth, weights=None)` 为经验分布能量评分，越小越好，单位米，也支持非负归一化权重。68% 和 95% 区域由落点云的协方差椭圆及经验马氏距离分位数确定。区域退化或样本过少时不计算覆盖率，记录原因与分母。确定性模型不生成区域。

`brier_score(probabilities, outcomes)` 检查穿越事件的概率，使用全部提供概率的案例，包括真实未穿越。区域覆盖率与能量评分在有真实穿越的案例上评价相应条件分布。各组均明确有效样本数。耗时只计预测器调用，包含拟合与传播，评分和绘图另行执行。

原始数据资料与访问情况见 `data/sources/data_validation.json`，本次实际结果与剩余工作见 `C_数据与验证阶段报告.md`。
