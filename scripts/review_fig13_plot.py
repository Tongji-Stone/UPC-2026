"""Render the review's feasible crossing samples without rerunning inference."""
from pathlib import Path
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/chapter5_review/fig13'
rows=list(csv.DictReader((OUT/'feasible_crossings.csv').open(encoding='utf-8-sig')))
summary=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],'font.size':10,'font.weight':'bold',
                     'axes.labelweight':'bold','axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
fig,ax=plt.subplots(figsize=(6.4,3.1),layout='constrained')
sc=ax.scatter([float(r['y']) for r in rows],[float(r['z']) for r in rows],c=[float(r['ad']) for r in rows],
              s=6,cmap='cividis',linewidths=0,alpha=.82)
b=summary['baseline']
ax.scatter([b['y']],[b['z']],marker='*',s=110,color='#D55E00',edgecolors='white',linewidths=.6,zorder=8,label='Reference')
ax.set(xlabel='Goal y (m)',ylabel='Goal z (m)')
ax.legend(frameon=False,loc='upper right',fontsize=9)
fig.colorbar(sc,ax=ax,label='Drag multiplier')
fig.savefig(OUT/'conditional_crossings_review.pdf',bbox_inches='tight')
fig.savefig(OUT/'conditional_crossings_review.png',bbox_inches='tight',dpi=240)
plt.close(fig)
old=list(csv.DictReader((ROOT/'results/sensitivity_linear/profile.csv').open(encoding='utf-8-sig')))
record=dict(points=len(rows),old_spin_x_at_boundary=sum(abs(abs(float(r['s3']))-60)<1e-5 for r in old),
            old_points=len(old),points_filling_old_gap=summary['new_points_in_old_y_gap'],
            x='goal-plane lateral coordinate (m)',y='goal-plane centre height (m)',color='drag coefficient multiplier',
            interpretation='The former blank band is populated by states satisfying the unchanged 2 mm constraint; one optimum per coefficient pair selected spin-boundary solutions.')
(OUT/'figure_record.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=True))
