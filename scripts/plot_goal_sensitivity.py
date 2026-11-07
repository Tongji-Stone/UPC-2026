"""Show one-factor goal-plane positions from the saved sensitivity scan."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patches import Rectangle
plt.rcParams.update({'font.family':'Times New Roman','font.weight':'bold','axes.labelweight':'bold','axes.titleweight':'bold','mathtext.fontset':'custom','mathtext.rm':'Times New Roman','mathtext.it':'Times New Roman:italic','mathtext.bf':'Times New Roman:bold','mathtext.default':'bf'})
root=Path('results/penalty_paper_sensitivity'); d=pd.read_csv(root/'scan.csv');fig,axes=plt.subplots(2,2,figsize=(9,7),constrained_layout=True)
labels={'speed':'Speed multiplier','azimuth_deg':'Azimuth change (deg)','spin_scale':'Spin multiplier','cd0':'Zero-spin drag coefficient'}
for ax,(factor,label) in zip(axes.flat,labels.items()):
    a=d[(d.factor==factor)&(d.event=='plane')];lo,hi=a.value.min(),a.value.max()
    for x in [i*3.66/8 for i in range(-7,8)]:ax.plot([x,x],[0,2.44],color='.82',lw=.6,zorder=0)
    for z in [i*2.44/5 for i in range(1,5)]:ax.plot([-3.66,3.66],[z,z],color='.82',lw=.6,zorder=0)
    ax.add_patch(Rectangle((-3.66,0),7.32,2.44,fill=False,color='black',lw=1.5))
    p=ax.scatter(a.y_m,a.z_m_assumed,c=a.value,cmap='coolwarm',norm=Normalize(lo,hi),edgecolors='black',linewidths=.2,s=22,zorder=3)
    ax.set(xlabel='Goal-plane y (m)',ylabel='Goal-plane z (m)',title=label,xlim=(-4,6.6),ylim=(-.25,2.85));ax.set_aspect('equal')
    bar=fig.colorbar(p,ax=ax,pad=.02,shrink=.82);bar.set_label(label,fontweight='bold')
fig.savefig(root/'goal_plane_sensitivity.pdf');fig.savefig(root/'goal_plane_sensitivity.png',dpi=240)
