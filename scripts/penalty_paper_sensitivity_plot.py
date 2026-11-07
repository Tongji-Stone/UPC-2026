"""Draw the previously calculated one-factor penalty scans."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'Times New Roman','font.weight':'bold','axes.labelweight':'bold','axes.titleweight':'bold','mathtext.fontset':'custom','mathtext.rm':'Times New Roman','mathtext.it':'Times New Roman:italic','mathtext.bf':'Times New Roman:bold','mathtext.default':'bf'})
p=Path('results/penalty_paper_sensitivity'); df=pd.read_csv(p/'scan.csv')
fig,axes=plt.subplots(2,2,figsize=(8.5,5.8),constrained_layout=True)
labels={'speed':'Speed multiplier','azimuth_deg':'Azimuth change (deg)','spin_scale':'Spin multiplier','cd0':'Zero-spin drag coefficient'}
for ax,(name,label) in zip(axes.flat,labels.items()):
    d=df[(df.factor==name)&(df.event=='plane')]; ax.plot(d.value,d.y_m,color='#a55235',label='y');ax.plot(d.value,d.z_m_assumed,color='#647a60',label='z')
    ax.set(xlabel=label,ylabel='Goal-plane coordinate (m)');ax.grid(alpha=.2)
axes[0,0].legend(prop={'family':'Times New Roman','weight':'bold'});fig.savefig(p/'scan.pdf');fig.savefig(p/'scan.png',dpi=200)
