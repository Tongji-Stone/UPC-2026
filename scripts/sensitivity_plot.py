"""从已保存的 CSV 绘图，不重新运行轨迹积分。"""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results' / 'sensitivity'
plt.rcParams.update({'font.sans-serif': ['Microsoft YaHei', 'DejaVu Sans'],
                     'axes.unicode_minus': False, 'figure.facecolor': '#faf9f5',
                     'axes.facecolor': '#faf9f5', 'axes.spines.top': False,
                     'axes.spines.right': False})
with (OUT / 'single_factor.csv').open(encoding='utf-8', newline='') as f:
    single = list(csv.DictReader(f))
with (OUT / 'random_scan.csv').open(encoding='utf-8', newline='') as f:
    random = list(csv.DictReader(f))
labels = {'speed': '球速 (m/s)', 'yaw_deg': '水平角 (°)', 'pitch_deg': '仰角 (°)',
          'cd0': '零自旋阻力系数', 'density': '空气密度 (kg/m³)', 'lift_scale': '升力倍率',
          'spin_x': 'x 轴自旋 (rad/s)', 'spin_y': 'y 轴自旋 (rad/s)', 'spin_z': 'z 轴自旋 (rad/s)',
          'spin_decay': '自旋衰减率 (1/s)', 'wind_x': 'x 向风 (m/s)',
          'wind_y': 'y 向风 (m/s)', 'wind_z': 'z 向风 (m/s)'}
fig, axes = plt.subplots(4, 4, figsize=(15, 12), constrained_layout=True)
for ax, (key, label) in zip(axes.flat, labels.items()):
    rows = [r for r in single if r['parameter'] == key and r['event'] == 'plane']
    ax.plot([float(r[key]) for r in rows], [float(r['y']) for r in rows], color='#bd674b', label='横向 y')
    ax.plot([float(r[key]) for r in rows], [float(r['z']) for r in rows], color='#68856d', label='高度 z')
    ax.set_xlabel(label)
    ax.set_ylabel('球门平面位置 (m)')
    ax.grid(alpha=.15)
axes.flat[0].legend(loc='best')
for ax in list(axes.flat)[len(labels):]:
    ax.axis('off')
fig.suptitle('单因素扫描：其余参数固定', fontsize=15)
fig.savefig(OUT / 'single_factor.png', dpi=160)
plt.close(fig)
plane = [r for r in random if r['event'] == 'plane']
fig, ax = plt.subplots(figsize=(7, 5.5), constrained_layout=True)
ax.scatter([float(r['y']) for r in plane], [float(r['z']) for r in plane],
           s=18, alpha=.55, color='#bd674b', edgecolors='none')
ax.axvline(-3.66, color='#8a8276', linestyle='--'); ax.axvline(3.66, color='#8a8276', linestyle='--')
ax.axhline(2.44, color='#8a8276', linestyle='--'); ax.axhline(0, color='#8a8276', linestyle='--')
ax.set(xlabel='横向 y (m)', ylabel='高度 z (m)', title=f'随机参数扫描：到达球门平面的 {len(plane)} 次')
ax.grid(alpha=.15)
fig.savefig(OUT / 'random_scan.png', dpi=160)
plt.close(fig)
print(f'Wrote plots to {OUT}')
