"""Plot the saved early observations and model prediction."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plt.rcParams.update({'font.family':'Times New Roman','font.weight':'bold','axes.labelweight':'bold','axes.titleweight':'bold'})
root=Path('results/model_solving');traj=np.loadtxt(root/'trajectory.csv',delimiter=',',skiprows=1);obs=np.loadtxt(root/'observations.csv',delimiter=',',skiprows=1)
fig,axs=plt.subplots(1,3,figsize=(11,3.5),constrained_layout=True)
for ax,j,label in [(axs[0],2,'y (m)'),(axs[1],3,'z (m)')]:
    ax.plot(traj[:,1],traj[:,j],color='#a55235',lw=2,label='M3 prediction');ax.scatter(obs[:,1],obs[:,j],s=27,color='black',zorder=3,label='Input observations');ax.axvline(11,color='.45',ls='--');ax.set(xlabel='x (m)',ylabel=label);ax.grid(alpha=.2)
axs[0].legend(prop={'family':'Times New Roman','weight':'bold','size':8})
ax=axs[2]
for x in [i*3.66/8 for i in range(-7,8)]:ax.plot([x,x],[0,2.44],color='.83',lw=.5)
for z in [i*2.44/5 for i in range(1,5)]:ax.plot([-3.66,3.66],[z,z],color='.83',lw=.5)
ax.add_patch(Rectangle((-3.66,0),7.32,2.44,fill=False,color='black',lw=1.4));ax.scatter(traj[-1,2],traj[-1,3],color='#a55235',s=45,zorder=3);ax.set(xlabel='Goal-plane y (m)',ylabel='Goal-plane z (m)',xlim=(-4,4),ylim=(-.2,2.8));ax.set_aspect('equal')
fig.savefig(root/'prediction.pdf');fig.savefig(root/'prediction.png',dpi=240)
