"""Illustrate a rotating ball using idealized two-dimensional flow lines."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patches import Circle, FancyArrowPatch

plt.rcParams.update({'pdf.fonttype':42,'font.family': 'Times New Roman', 'font.weight': 'bold',
                     'mathtext.fontset': 'custom', 'mathtext.rm': 'Times New Roman',
                     'mathtext.it': 'Times New Roman:italic',
                     'mathtext.bf': 'Times New Roman:bold', 'mathtext.default': 'bf'})
x = np.linspace(-3.7, 3.7, 420)
y = np.linspace(-2.1, 2.1, 260)
X, Y = np.meshgrid(x, y)
r2 = X*X + Y*Y
safe = np.maximum(r2, 1e-8)
circulation = .70
ux = -(1 - (X*X-Y*Y)/safe**2) - circulation*Y/safe
uy = -2*X*Y/safe**2 + circulation*X/safe
mask = r2 <= 1.025**2
u = np.ma.array(ux, mask=mask)
v = np.ma.array(uy, mask=mask)
speed = np.ma.sqrt(u*u + v*v)

fig, ax = plt.subplots(figsize=(8.4, 4.6), constrained_layout=True)
ax.streamplot(x, y, u, v, color=speed, cmap='viridis', norm=Normalize(0, 2.3),
              density=.82, minlength=.08, maxlength=.30, linewidth=1.0,
              arrowsize=.75, zorder=1)
ax.add_patch(Circle((0, 0), 1, facecolor='white', edgecolor='black', lw=1.1, zorder=4))
ball = plt.imread('paper/assets/magnus_ball.png')
ball_image = ax.imshow(ball, extent=(-1.64, 1.64, -1.094, 1.094), zorder=5)
ball_image.set_clip_path(Circle((0, 0), 1, transform=ax.transData))
for a, b in [((.65, .77), (-.25, 1.07)), ((-.66, -.76), (.27, -1.07))]:
    ax.add_patch(FancyArrowPatch(a, b, connectionstyle='arc3,rad=.35',
                                arrowstyle='->', mutation_scale=15,
                                color='#b34931', lw=2, zorder=7))
ax.annotate('', xy=(0, 1.70), xytext=(0, .88),
            arrowprops={'arrowstyle': '->', 'color': '#b34931', 'lw': 2}, zorder=8)
ax.text(.15, 1.48, r'$\mathbf{F}_L$', color='#b34931', fontsize=14, zorder=9)
ax.text(.86, .53, r'$\boldsymbol{\omega}$', color='#b34931', fontsize=13, zorder=9)
ax.text(-3.6, 1.88, 'Relative airflow', fontsize=11,
        bbox={'facecolor':'white', 'edgecolor':'none', 'alpha':.85, 'pad':2})
ax.set(xlim=(-3.7, 3.7), ylim=(-2.1, 2.1), aspect='equal')
ax.axis('off')
out=Path('paper/assets');out.mkdir(parents=True,exist_ok=True)
fig.savefig(out/'magnus_streamlines.pdf', bbox_inches='tight', facecolor='white')
