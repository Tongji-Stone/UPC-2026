"""Plot saved real-shot records and M5 reconstruction without recomputation."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams.update({'font.family':'Times New Roman','font.weight':'bold','axes.labelweight':'bold',
 'axes.titleweight':'bold','mathtext.fontset':'custom','mathtext.rm':'Times New Roman',
 'mathtext.bf':'Times New Roman:bold','mathtext.it':'Times New Roman:italic','mathtext.default':'bf'})
p=Path('results/dfl_real_shot_validation'); data=pd.read_csv(p/'positions.csv',dtype={'event_id':str})
fit=pd.read_csv(p/'fitted_positions.csv',dtype={'event_id':str}); samples=pd.read_csv(p/'samples.csv',dtype={'event_id':str})
fig,axes=plt.subplots(2,len(samples),figsize=(12,6),constrained_layout=True)
for j,row in samples.iterrows():
    d=data[data.event_id==row.event_id]; m=fit[(fit.event_id==row.event_id)&(fit.model=='M5')]
    for ax,col,label in zip(axes[:,j],['y_m','z_assumed_m'],['y (m)','z (m, assumed)']):
        ax.plot(d.x_m,d[col],'o',color='#292521',ms=3,label='Tracked');ax.plot(m.x_m,m[col],color='#a35c40',lw=1.5,label='M5 fit')
        ax.axvline(row.goal_x_m,color='#918a80',linestyle='--',lw=1,label='Goal plane')
        ax.set(xlabel='x (m)',ylabel=label);ax.grid(alpha=.15)
    axes[0,j].set_title(f"{row.type_of_shot}: {row.event_outcome}\nEvent ...{row.event_id[-4:]}")
axes[0,0].legend(fontsize=8);fig.savefig(p/'real_shot_fits.png',dpi=200)
