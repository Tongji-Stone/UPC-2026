"""Plot saved real penalty measurements and fitted trajectories."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
root=Path('results/real_penalty_fit'); d=pd.read_csv(root/'trajectory_fit.csv')
fig,axs=plt.subplots(1,2,figsize=(11,4.5),constrained_layout=True)
for model,color in [('observed','#332d27'),('M1','#a88d77'),('M3','#a45b40'),('M5_fitted','#637e60')]:
    x=d[d.model==model]; label={'observed':'Observed','M1':'Gravity','M3':'Gravity + drag','M5_fitted':'M5 fitted'}[model]
    for ax,col in zip(axs,['y_m','z_assumed_m']):
        ax.plot(x.x_m,x[col],marker='o' if model=='observed' else None,markersize=3,label=label,color=color)
for ax,y in zip(axs,['y (m)','z (m, assumed)']):
    ax.axvline(52.5,color='#968b7d',linestyle='--',label='Goal plane');ax.set(xlabel='Pitch x (m)',ylabel=y);ax.grid(alpha=.2)
axs[0].legend();fig.suptitle('Recorded penalty: complete-flight fit')
fig.savefig(root/'trajectory_fit.png',dpi=200);fig.savefig(root/'trajectory_fit.svg')
