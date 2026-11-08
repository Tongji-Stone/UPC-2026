"""Render parallel coordinates using reproducible display sample IDs."""
import hashlib,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D

ROOT=Path(__file__).resolve().parents[1]

def build_parallel_coordinates(root=ROOT):
    mc=root/'results/monte_carlo'
    source=mc/'samples.npz'
    preview=root/'data/sensitivity_v2/parallel_display.json'
    record=json.loads(preview.read_text(encoding='utf-8'))
    data=np.load(source)
    ids=np.array(record['selected_ids'],dtype=int)
    assert len(ids)==400 and len(np.unique(ids))==400
    assert np.array_equal(ids,np.sort(np.random.default_rng(record['display_seed']).choice(100000,400,replace=False)))
    half=np.array(record['input_half_widths'])
    outputs=np.column_stack([data['point'][:,1],data['point'][:,2],data['time']])
    lo,hi=outputs.min(axis=0),outputs.max(axis=0)
    normalized=np.column_stack([(data['delta'][ids]+half)/(2*half),(outputs[ids]-lo)/(hi-lo)])
    reference=np.r_[np.full(9,.5),(np.array([2.682644507905514,1.9592312099350713,.40264914833815935])-lo)/(hi-lo)]
    clear=data['clear'][ids]
    assert int(clear.sum())==382 and int((~clear).sum())==18
    assert normalized.min()>=0 and normalized.max()<=1
    blue,orange,gray='#0072B2','#D55E00','#454B4B'
    plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],
        'font.size':9,'pdf.fonttype':42,'svg.fonttype':'none'})
    fig=plt.figure(figsize=(6.4,3.6),facecolor='white')
    ax=fig.add_axes([.075,.235,.90,.57])
    x=np.arange(12)
    ax.axvspan(8.55,11.4,color='#f6e9df',alpha=.65,zorder=-5)
    for v in [0,.25,.5,.75,1]:ax.axhline(v,color='#d9dedd',lw=.5,zorder=-4)
    for v in x:ax.vlines(v,0,1,color='#b7beba',lw=.6,zorder=-3)
    for ok,color,alpha,width in [(True,blue,.075,.45),(False,orange,.48,.65)]:
        traces=normalized[clear==ok]
        segments=np.stack([np.broadcast_to(x,traces.shape),traces],axis=2)
        ax.add_collection(LineCollection(segments,colors=color,alpha=alpha,linewidths=width,zorder=1 if ok else 2))
    ax.plot(x,reference,color=gray,ls=(0,(4,2)),lw=1.1,zorder=4)
    labels=[r'$v_0$',r'$\phi_v$',r'$\theta_v$',r'$\omega_0$',r'$\phi_\omega$',r'$\theta_\omega$',
            r'$\alpha_D$',r'$\alpha_L$',r'$\rho$',r'$y_g$',r'$z_g$',r'$t_g$']
    lower=['-5%',r'$-2^\circ$',r'$-2^\circ$','-10%',r'$-2^\circ$',r'$-2^\circ$','-10%','-10%','-10%',
           f'{lo[0]:.3f} m',f'{lo[1]:.3f} m',f'{lo[2]:.4f} s']
    upper=['+5%',r'$+2^\circ$',r'$+2^\circ$','+10%',r'$+2^\circ$',r'$+2^\circ$','+10%','+10%','+10%',
           f'{hi[0]:.3f} m',f'{hi[1]:.3f} m',f'{hi[2]:.4f} s']
    ax.set(xlim=(-.30,11.38),ylim=(-.02,1.025),xticks=x,xticklabels=labels,
           yticks=[0,.25,.5,.75,1],yticklabels=['0','.25','.50','.75','1'])
    ax.tick_params(axis='x',length=0,pad=24,labelsize=10)
    ax.tick_params(axis='y',length=0,labelsize=8)
    ax.set_ylabel('Scaled axis value',fontsize=9,labelpad=6)
    for spine in ax.spines.values():spine.set_visible(False)
    for i,(a,b) in enumerate(zip(lower,upper)):
        ax.text(i,-.035,a,ha='center',va='top',fontsize=6.7,transform=ax.get_xaxis_transform())
        ax.text(i,1.055,b,ha='center',va='bottom',fontsize=6.7,transform=ax.get_xaxis_transform())
    ax.text(4,1.20,'Nine input perturbations',ha='center',fontsize=9,transform=ax.get_xaxis_transform())
    ax.text(10,1.20,'Three outcomes',ha='center',fontsize=9,color=orange,transform=ax.get_xaxis_transform())
    handles=[Line2D([0],[0],color=blue,lw=1.3,label='Clears goal (382)'),
             Line2D([0],[0],color=orange,lw=1.3,label='Too high (18)'),
             Line2D([0],[0],color=gray,ls='--',lw=1.1,label='Paper representative')]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.52,.025),ncol=3,frameon=False,
               fontsize=8,handlelength=2,columnspacing=1.2)
    out=root/'results/sensitivity_v2';figdir=out/'figures';figdir.mkdir(parents=True,exist_ok=True)
    for ext in ['pdf','svg','png']:
        fig.savefig(figdir/f'monte_carlo_parallel_coordinates.{ext}',dpi=300,bbox_inches='tight',facecolor='white')
    svg=figdir/'monte_carlo_parallel_coordinates.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    plt.close(fig)
    detail=dict(display_seed=record['display_seed'],display_count=400,selected_ids=ids.tolist(),
        displayed_clear=382,displayed_high=18,full_count=100000,
        input_half_widths=half.tolist(),output_min=lo.tolist(),output_max=hi.tolist(),
        all_scaled_values_within_unit_interval=True,
        display_sample_ids_preserved=True,
        representative_input_axes_at_half=True,
        displayed_high_elevation_range_degrees=[float(data['delta'][ids[~clear],2].min()),float(data['delta'][ids[~clear],2].max())],
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        display_selection_sha256=hashlib.sha256(preview.read_bytes()).hexdigest(),
        normalization='Input perturbation limits; full-sample outcome extrema; linear scaling to [0,1]',
        shown_component='Parallel coordinates')
    (out/'parallel_coordinates_record.json').write_text(json.dumps(detail,ensure_ascii=False,indent=2),encoding='utf-8')
    return detail

if __name__=='__main__':
    r=build_parallel_coordinates()
    print('Paper parallel coordinates rendered:',r['display_count'],'traces; seed',r['display_seed'])
