"""Plot empirical synthetic coverage from saved calculation results."""
import json
from pathlib import Path
import matplotlib.pyplot as plt
root=Path('results/synthetic_calibration'); d=json.loads((root/'results.json').read_text())
fig,ax=plt.subplots(figsize=(5.5,5),constrained_layout=True)
ax.plot([0,1],[0,1],color='#999085',linestyle='--',label='Nominal')
for key,color in [('005','#be7350'),('010','#6a8067')]:
    s=d['summary'][key]; ax.plot([.68,.95],[s['covered68'],s['covered95']],marker='o',color=color,label=key+' s')
ax.set(xlim=(.5,1.01),ylim=(.5,1.01),xlabel='Nominal coverage',ylabel='Observed coverage',title=f"Synthetic coverage ({d['cases']} shots)")
ax.grid(alpha=.2); ax.legend(); fig.savefig(root/'coverage.png',dpi=200); fig.savefig(root/'coverage.svg')
