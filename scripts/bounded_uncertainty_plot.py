from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plt.rcParams.update({'font.family':'Times New Roman','font.weight':'bold','axes.labelweight':'bold','axes.titleweight':'bold'})
p=Path('results/bounded_uncertainty');d=pd.read_csv(p/'samples.csv');d=d[d.event=='plane'];fig,ax=plt.subplots(figsize=(6,4.5),constrained_layout=True)
ax.scatter(d.y,d.z,s=6,color='#aa6245',alpha=.35);ax.add_patch(Rectangle((-3.66,0),7.32,2.44,fill=False,color='black'))
ax.set(xlabel='Goal-plane y (m)',ylabel='Goal-plane z (m, assumed)',title='Bounded spin, wind and drag scenarios');ax.grid(alpha=.2)
fig.savefig(p/'region.pdf');fig.savefig(p/'region.png',dpi=200)
