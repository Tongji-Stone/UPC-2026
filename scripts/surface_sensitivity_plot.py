"""Plot precomputed coefficient-law trajectories using bold Times New Roman."""
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
plt.rcParams.update({'font.family':'Times New Roman','font.weight':'bold','axes.labelweight':'bold',
 'axes.titleweight':'bold','mathtext.fontset':'custom','mathtext.rm':'Times New Roman',
 'mathtext.it':'Times New Roman:italic','mathtext.bf':'Times New Roman:bold','mathtext.default':'bf'})
p=Path('results/surface_sensitivity');df=pd.read_csv(p/'trajectories.csv')
fig,ax=plt.subplots(figsize=(6,3.4),constrained_layout=True)
for law,label,colour in [('smooth_sphere_drag','Smooth-sphere drag law','#485e75'),('soccer_ball_drag','Soccer-ball drag table','#a05239')]:
 d=df[df.law==law];ax.plot(d.x_m,d.z_assumed_m,label=label,color=colour,linewidth=2)
ax.axvline(11,color='#888',linestyle='--',label='Goal plane');ax.set(xlabel='x (m)',ylabel='Height z (m)');ax.grid(alpha=.2);ax.legend(prop={'family':'Times New Roman','weight':'bold','size':9})
fig.savefig(p/'comparison.png',dpi=240);fig.savefig(p/'comparison.pdf')
