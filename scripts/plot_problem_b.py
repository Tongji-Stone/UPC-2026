"""Render precomputed results without rerunning inference."""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Ellipse, Rectangle

out = Path('results')
report = json.loads((out/'problem_b.json').read_text(encoding='utf-8'))
fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
for ax, key, title in zip(axes, ['005', '010'], ['Observations through 0.05 s', 'Observations through 0.10 s']):
    p = np.load(out/f'prediction_{key}.npz')['points']
    ax.hexbin(p[:, 0], p[:, 1], gridsize=45, mincnt=1, cmap='YlOrBr', bins='log')
    info = report[key]; mean = np.array(info['mean']); cov = np.array(info['covariance'])
    vals, vec = np.linalg.eigh(cov); order = np.argsort(vals)[::-1]; vals, vec = vals[order], vec[:, order]
    angle = np.degrees(np.arctan2(vec[1,0], vec[0,0]))
    for q, ls in zip(info['ellipse_mahalanobis2'], ['-', '--']):
        ax.add_patch(Ellipse(mean, *(2*np.sqrt(vals*q)), angle=angle, fill=False, edgecolor='#803c25', linestyle=ls, linewidth=1.5))
    ax.add_patch(Rectangle((-3.66,0), 7.32, 2.44, fill=False, edgecolor='#333333'))
    ax.scatter(*mean, marker='+', color='#23211e', label='Mean'); ax.scatter(*info['mode'], marker='x', color='#a03b23', label='Estimated mode')
    ax.set(xlabel='y (m)', ylabel='z (m)', title=title); ax.legend(); ax.grid(alpha=.15)
fig.suptitle('Predicted crossing locations; ellipses contain 68% and 95% of samples')
fig.savefig(out/'problem_b_predictions.png', dpi=200); fig.savefig(out/'problem_b_predictions.svg')
