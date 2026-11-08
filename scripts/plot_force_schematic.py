"""Draw the relative airflow and force directions for the model section."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse

plt.rcParams.update({'font.family': 'Times New Roman', 'font.weight': 'bold',
                     'mathtext.fontset': 'custom', 'mathtext.rm': 'Times New Roman',
                     'mathtext.it': 'Times New Roman:italic',
                     'mathtext.bf': 'Times New Roman:bold', 'mathtext.default': 'bf'})

fig, axes = plt.subplots(1, 2, figsize=(9, 2.8), constrained_layout=True)
for ax in axes:
    ax.set(xlim=(-3.0, 3.3), ylim=(-1.8, 2.1), aspect='equal')
    ax.axis('off')
    ax.add_patch(Circle((0, 0), 0.75, fill=False, lw=1.35))
    ax.add_patch(Ellipse((0, 0), .35, 1.5, fill=False, lw=.8, ls='--'))

a, b = axes
a.plot(0, 0, 'ko', ms=2)
for y in (-.9, -.35, .35, .9):
    for x in (-2.75, 1.0):
        a.annotate('', xy=(x, y), xytext=(x+1.4, y),
                   arrowprops={'arrowstyle': '->', 'lw': .9})
a.annotate('', xy=(1.9, 1.48), xytext=(.1, 1.48),
           arrowprops={'arrowstyle': '->', 'lw': 1.1})
a.text(.9, 1.59, r'$\mathbf{u}$', ha='center', fontsize=11)
a.text(-2.65, 1.2, 'Relative airflow', fontsize=9)
a.text(0, -1.55, r'(a) Airflow in the ball frame', ha='center', fontsize=10)

b.annotate('', xy=(-2.3, 0), xytext=(-.75, 0), arrowprops={'arrowstyle': '->', 'lw': 1.2})
b.text(-2.35, .15, r'$\mathbf{F}_D$', fontsize=11)
b.annotate('', xy=(2.25, 0), xytext=(.75, 0), arrowprops={'arrowstyle': '->', 'lw': 1.2})
b.text(2.28, .14, r'$\mathbf{u}$', fontsize=11)
b.annotate('', xy=(0, 1.8), xytext=(0, .75), arrowprops={'arrowstyle': '->', 'lw': 1.2})
b.text(.15, 1.64, r'$\mathbf{F}_L$', fontsize=11)
b.plot(0, 0, marker='o', ms=9, markerfacecolor='white', markeredgecolor='black')
b.plot(0, 0, 'ko', ms=2)
b.text(.25, -.35, r'$\boldsymbol{\omega}$', fontsize=11)
b.text(0, -1.55, r'(b) Example: spin out of the page', ha='center', fontsize=10)

out = Path('paper/assets')
out.mkdir(parents=True, exist_ok=True)
fig.savefig(out/'force_schematic.pdf', bbox_inches='tight', facecolor='white')
fig.savefig(out/'force_schematic.png', dpi=240, bbox_inches='tight', facecolor='white')
