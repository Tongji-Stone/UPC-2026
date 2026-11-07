"""Plot physical posterior samples previously computed by the inference script."""
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Rectangle
root=Path('results/physical_probability'); summary=json.loads((root/'summary.json').read_text(encoding='utf8'))
fig, axes=plt.subplots(1,2,figsize=(12,5),constrained_layout=True)
for ax, key, label in zip(axes, ('005','010'), ('0.05 s','0.10 s')):
    p=np.load(root/f'points_{key}.npz')['points']; s=summary[key]
    ax.hexbin(p[:,0],p[:,1],gridsize=45,mincnt=1,cmap='YlOrBr',bins='log')
    m=np.array(s['mean']); vals,vec=np.linalg.eigh(s['covariance']); order=np.argsort(vals)[::-1]; vals=vals[order]; vec=vec[:,order]
    angle=np.degrees(np.arctan2(vec[1,0],vec[0,0]))
    for q,style in zip(s['ellipse_mahalanobis2'],('-','--')):
        ax.add_patch(Ellipse(m,*(2*np.sqrt(vals*q)),angle=angle,fill=False,edgecolor='#803c25',linestyle=style))
    ax.add_patch(Rectangle((-3.66,0),7.32,2.44,fill=False,edgecolor='#333'))
    ax.scatter(*m,marker='+',color='#222',label='Mean'); ax.scatter(*s['mode'],marker='x',color='#a03b23',label='Estimated mode')
    ax.set(xlabel='y (m)',ylabel='z (m)',title='Observations through '+label); ax.grid(alpha=.15); ax.legend()
fig.suptitle('Physical model posterior; 68% and 95% sample ellipses')
fig.savefig(root/'prediction.png',dpi=200); fig.savefig(root/'prediction.svg')
