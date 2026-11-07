"""Plot paired errors using the same successful cases for each model."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

root=Path('results/dfl_benchmark')
df=pd.read_csv(root/'samples_and_predictions.csv')
fig,axes=plt.subplots(1,2,figsize=(12,5),constrained_layout=True)
for ax,window in zip(axes,[.05,.10]):
    d=df[df.duration_s.eq(window)]; models=['M0','M1','M3','M4','M5'] if window==.05 else ['M0','M1','M2','M3','M4','M5']
    sets=[set(d[(d.model==m)&(d.event=='plane')]['sample']) for m in models]
    common=set.intersection(*sets)
    data=[d[(d.model==m)&d['sample'].isin(common)].sort_values('sample')['error_assumed_m'].to_numpy() for m in models]
    box=ax.boxplot(data,tick_labels=models,patch_artist=True,showfliers=True)
    for patch in box['boxes']: patch.set(facecolor='#d3a181',edgecolor='#734b37')
    ax.set(title=f'Window {window:.2f} s; {len(common)} shared cases',ylabel='2D error (m, Z unit assumed)'); ax.grid(axis='y',alpha=.2)
fig.suptitle('DFL virtual-plane predictions, common valid cases')
fig.savefig(root/'paired_errors.png',dpi=200); fig.savefig(root/'paired_errors.svg')
