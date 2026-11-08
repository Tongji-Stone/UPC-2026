"""English free-body diagram; run with Python + NumPy + Matplotlib.

Source: Tongji-Stone/UPC-2026, commit 3035c5bfc56e38ddfd8d05e7cdfacdd986fd89bc,
paper/main.tex, Force Analysis. Arrow lengths are deliberately schematic.
"""
from pathlib import Path
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
for font_file in ('times.ttf', 'timesbd.ttf', 'timesi.ttf', 'timesbi.ttf'):
    font_manager.fontManager.addfont(str(Path('C:/Windows/Fonts') / font_file))
from matplotlib.patches import Circle, Polygon, FancyArrowPatch, Arc
import numpy as np

OUT = Path(__file__).resolve().parents[1] / 'paper/assets'
plt.rcParams.update({
    'font.family': 'Times New Roman', 'font.size': 11,
    'mathtext.fontset': 'custom',
    'mathtext.rm': 'Times New Roman',
    'mathtext.it': 'Times New Roman:italic',
    'mathtext.bf': 'Times New Roman:bold',
    'mathtext.bfit': 'Times New Roman:bold:italic',
    'mathtext.sf': 'Times New Roman',
    'mathtext.tt': 'Times New Roman',
    'mathtext.cal': 'Times New Roman:italic',
    'mathtext.fallback': 'stix', 'svg.fonttype': 'none',
    'pdf.fonttype': 42, 'savefig.facecolor': 'white',
})
C = {'g': '#BB513C', 'b': '#008B83', 'd': '#366B97',
     'l': '#94702C', 'ink': '#29333B', 'muted': '#69757D'}
fig = plt.figure(figsize=(7.5, 6.12), facecolor='white')
ax = fig.add_axes([.02, .025, .96, .95])
ax.set(xlim=(-3.1, 2.8), ylim=(-2.4, 2.48), aspect='equal')
ax.axis('off')

# A quiet, vector soccer-ball drawing behind the free-body arrows.
R = .54
ball = Circle((0, 0), R, facecolor='#F3F2EE', edgecolor='#889096', lw=1.15, zorder=2)
ax.add_patch(ball)
angles = np.deg2rad(90 + np.arange(5)*72)
pent = np.column_stack((.205*np.cos(angles), .205*np.sin(angles)))
ax.add_patch(Polygon(pent, facecolor='#B8BCBD', edgecolor='#92999B', lw=.7, zorder=3))
for a, p in zip(angles, pent):
    q = R*np.array([np.cos(a+.18), np.sin(a+.18)])
    ax.plot([p[0], q[0]], [p[1], q[1]], color='#A8ADAF', lw=.9, zorder=3)
for a in np.deg2rad(np.arange(5)*72+24):
    q = R*np.array([np.cos(a), np.sin(a)])
    local = np.array([q*.74, R*np.array([np.cos(a-.25), np.sin(a-.25)]),
                      R*np.array([np.cos(a+.25), np.sin(a+.25)])])
    patch = Polygon(local, facecolor='#CDD0D0', edgecolor='#A2A9AA', lw=.55, zorder=3)
    patch.set_clip_path(ball)
    ax.add_patch(patch)

def arrow(end, color, dashed=False, width=2.6, start=(0,0), scale=17, z=6):
    p = FancyArrowPatch(start, end, arrowstyle='-|>', mutation_scale=scale,
                        lw=width, color=color, linestyle=(0,(5,4)) if dashed else '-',
                        shrinkA=0, shrinkB=0, zorder=z)
    ax.add_patch(p)

# Page coordinates (horizontal x, vertical z). Out-of-page spin is -e_y.
# Thus omega x u points up and left, exactly perpendicular to u.
theta = np.deg2rad(22)
u = np.array([np.cos(theta), np.sin(theta)])
lift = np.array([-np.sin(theta), np.cos(theta)])
assert abs(np.dot(u, lift)) < 1e-12
u3 = np.array([u[0], 0., u[1]])
omega3 = np.array([0., -1., 0.])
assert np.allclose(np.cross(omega3, u3)[[0,2]], lift)
arrow((0,-1.92), C['g'])
arrow((0,1.82), C['b'])
arrow(-2.23*u, C['d'])
arrow(2.15*lift, C['l'])
arrow(2.44*u, C['muted'], dashed=True, width=1.7, scale=14)

ax.text(.14,-1.91, 'Gravity', color=C['g'], va='center', size=12, weight='normal')
ax.text(.14,-2.16, r'$\mathbfit{F}_g$', color=C['g'], va='center', size=13)
ax.text(.15,1.84, 'Buoyancy', color=C['b'], va='center', size=12, weight='normal')
ax.text(.15,1.57, r'$\mathbfit{F}_B$', color=C['b'], va='center', size=13)
ax.text(-1.12,2.20, 'Magnus force', color=C['l'], ha='right', va='center', size=12, weight='normal')
ax.text(-1.12,1.92, r'$\mathbfit{F}_L$', color=C['l'], ha='right', va='center', size=13)
ax.text(-2.17,-1.20, 'Air drag', color=C['d'], ha='center', size=12, weight='normal')
ax.text(-2.17,-1.48, r'$\mathbfit{F}_D$', color=C['d'], ha='center', size=13)
ax.text(1.64,1.32, r'$\mathbfit{v}$',
        color=C['muted'], ha='center', size=12)
ax.text(1.68,1.05, 'Ball velocity (still air)', color=C['muted'], ha='center', size=10)

# Out-of-page spin marker and counterclockwise rotational sense.
ax.add_patch(Circle((0,0), .083, facecolor='white', edgecolor=C['ink'], lw=1.2, zorder=9))
ax.plot(0,0,'.', color=C['ink'], ms=4.5, zorder=10)
rr = .70
ax.add_patch(Arc((0,0), 2*rr, 2*rr, theta1=-68, theta2=18,
                 color=C['ink'], lw=1.2, zorder=5))
a0, a1 = np.deg2rad([10,19])
arrow(rr*np.array([np.cos(a1),np.sin(a1)]), C['ink'], width=1.2,
      start=rr*np.array([np.cos(a0),np.sin(a0)]), scale=11, z=5)
ax.add_patch(Circle((.945,-.425), .035, facecolor='white', edgecolor=C['ink'], lw=.85))
ax.plot(.945,-.425,'.', color=C['ink'], ms=1.8)
ax.text(1.04,-.47, r'$\mathbfit{\omega}$ out of page', color=C['ink'], size=11)
ax.text(.90,-.74, 'Counterclockwise spin', color=C['muted'], size=9.5)

# A small orientation key (x,z), separate from force arrows.
origin = np.array([-2.83, -2.03])
arrow(origin+np.array([.52,0]), C['muted'], width=1, start=origin, scale=8)
arrow(origin+np.array([0,.52]), C['muted'], width=1, start=origin, scale=8)
ax.text(origin[0]+.60,origin[1]-.02,'$x$', color=C['muted'], size=10, va='center')
ax.text(origin[0],origin[1]+.62,'$z$', color=C['muted'], size=10, ha='center')

# Enlarge every label by another 30 percent relative to the previous version.
for label in ax.texts:
    label.set_fontsize(label.get_fontsize() * 1.82)

for extension in ['pdf']:
    path = OUT / f'ball_force_diagram_times_xlarge.{extension}'
    fig.savefig(path, dpi=450)
    print(path)
preview=Path(__file__).resolve().parents[1]/'results/current_report/qa'
preview.mkdir(parents=True,exist_ok=True)
fig.savefig(preview/'ball_force_still_air.png',dpi=140)
plt.close(fig)
