"""Render individual case trajectories from saved computation output."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'Times New Roman','font.weight':'bold','axes.labelweight':'bold','axes.titleweight':'bold'})
p=Path('results/kick_cases_linear_spin');d=pd.read_csv(p/'trajectories.csv')
for name in ['Power','Placement','Curved','Topspin','Backspin','Chip']:
 fig=plt.figure(figsize=(6.5,4.3),constrained_layout=True);ax=fig.add_subplot(111,projection='3d')
 # Coordinates retain the competition convention: x points at the goal.
 for kind,color,style,label in [('truth','#536d91','-','Simulated flight'),('zero_spin','#b26946','--','M4, zero spin')]:
  q=d[(d['case']==name)&(d.kind==kind)];ax.plot(q.x,q.y,q.z,color=color,ls=style,lw=2,label=label)
 q=d[(d['case']==name)&(d.kind=='observation')];ax.scatter(q.x,q.y,q.z,color='#272727',s=20,label='Three input positions')
 for y in [-3.66,3.66]:ax.plot([11,11],[y,y],[0,2.44],color='#586b52',lw=1.5)
 ax.plot([11,11],[-3.66,3.66],[2.44,2.44],color='#586b52',lw=1.5)
 ax.set(xlabel='x (m)',ylabel='y (m)',zlabel='z (m)',xlim=(0,11.5),ylim=(-4,4),zlim=(0,3));ax.view_init(elev=22,azim=-60)
 ax.legend(loc='upper left',prop={'family':'Times New Roman','weight':'bold','size':8});fig.savefig(p/f'{name.lower()}_3d.pdf');fig.savefig(p/f'{name.lower()}_3d.png',dpi=200);plt.close(fig)
