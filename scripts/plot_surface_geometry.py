"""Conceptual redraw of smooth and seamed geometries after Paudel & Yan Fig. 3."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Polygon
plt.rcParams.update({'font.family':'Times New Roman','font.weight':'bold','axes.labelweight':'bold','axes.titleweight':'bold'})
out=Path('results/surface_geometry');out.mkdir(parents=True,exist_ok=True)
fig,axes=plt.subplots(1,2,figsize=(7.5,3.5),constrained_layout=True)
for ax,title in zip(axes,['Smooth sphere','Seamed football']):
    ax.add_patch(Circle((0,0),1,facecolor='#faf9f6',edgecolor='#35312d',lw=2))
    ax.set(xlim=(-1.2,1.2),ylim=(-1.25,1.25),aspect='equal',title=title);ax.axis('off')
ax=axes[1]; angles=np.deg2rad(np.arange(90,450,72)); inner=np.c_[.36*np.cos(angles),.36*np.sin(angles)]
ax.add_patch(Polygon(inner,closed=True,facecolor='#ded9d1',edgecolor='#35312d',lw=1.4))
for i in range(5):
    v=inner[i];theta=angles[i]; end=.97*np.array([np.cos(theta),np.sin(theta)])
    mid=.68*np.array([np.cos(theta+.22),np.sin(theta+.22)])
    ax.plot([v[0],mid[0],end[0]],[v[1],mid[1],end[1]],color='#35312d',lw=1.2)
    nextv=inner[(i+1)%5]; a=(angles[i]+angles[i+1])/2 if i<4 else (angles[i]+angles[0]+2*np.pi)/2
    tip=.98*np.array([np.cos(a),np.sin(a)])
    ax.plot([v[0],tip[0],nextv[0]],[v[1],tip[1],nextv[1]],color='#35312d',lw=1.2)
fig.savefig(out/'surface_geometry.pdf');fig.savefig(out/'surface_geometry.png',dpi=240);fig.savefig(out/'surface_geometry.svg')
