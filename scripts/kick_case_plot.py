"""Plot case results without rerunning the integrations."""
from pathlib import Path
import json
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({'font.family':'Times New Roman','font.weight':'bold','axes.labelweight':'bold','axes.titleweight':'bold'})
p=Path('results/kick_cases_linear_spin'); r=json.loads((p/'cases.json').read_text(encoding='utf8'))['cases']
fig,ax=plt.subplots(figsize=(8,3.6),constrained_layout=True); x=np.arange(len(r));width=.36
for shift,key,label,color in [(-width/2,'M1_error_m','M1: gravity only','#a45c3c'),(width/2,'M4_zero_error_m','M4: zero-spin assumption','#697e62')]:
    ax.bar(x+shift,[item[key] if item[key] is not None else 0 for item in r],width,label=label,color=color)
ax.set_xticks(x,[item['case'] for item in r]);ax.set_ylabel('Goal-plane error (m)');ax.grid(axis='y',alpha=.2);ax.legend(prop={'family':'Times New Roman','weight':'bold','size':9})
fig.savefig(p/'case_errors.pdf');fig.savefig(p/'case_errors.png',dpi=240)
