"""Combine the nine saved time-response scans on a single pair of axes."""
import csv,hashlib,json,shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
STYLE=[
 ('speed','Launch speed','#0072B2','-','o',.05),
 ('yaw','Velocity azimuth','#D55E00','-','s',2.),
 ('pitch','Velocity elevation','#D55E00','--','^',2.),
 ('spin','Spin magnitude','#0072B2','--','v',.10),
 ('spin_yaw','Spin-axis azimuth','#D55E00',':','D',2.),
 ('spin_pitch','Spin-axis elevation','#D55E00','-.','P',2.),
 ('ad','Drag coefficient','#009E73','-','<',.10),
 ('al','Lift parameter','#009E73','--','x',.10),
 ('rho','Air density','#009E73','-.','>',.10)]

def build_time_response(root=ROOT):
    source=root/'results/sensitivity_linear/one_factor.csv'
    with source.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
    plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],
        'font.size':10,'font.weight':'bold','axes.labelweight':'bold','axes.titleweight':'bold','axes.spines.right':False,'axes.spines.top':False,
        'pdf.fonttype':42,'svg.fonttype':'none'})
    fig,ax=plt.subplots(figsize=(6.4,3.8),layout='constrained')
    record=[]
    for i,(key,label,color,style,marker,half) in enumerate(STYLE):
        group=sorted([r for r in rows if r['parameter']==key],key=lambda r:float(r['delta']))
        x=np.array([float(r['delta'])/half for r in group])
        y=np.array([1000*float(r['dt']) for r in group])
        assert len(group)==41 and np.allclose([x[0],x[-1]],[-1,1])
        assert abs(y[np.argmin(abs(x))])<1e-6
        ax.plot(x,y,label=label,color=color,ls=style,lw=1.45,
                marker=marker,markersize=3.9,markevery=(2+i%5,9),
                markerfacecolor='white' if marker!='x' else color,markeredgewidth=.8)
        record.append(dict(parameter=key,half_width=half,points=41,
                           x=x.tolist(),arrival_time_change_ms=y.tolist()))
    ax.axhline(0,color='#454B4B',lw=.65,zorder=0)
    ax.axvline(0,color='#454B4B',lw=.65,ls=':',zorder=0)
    ax.set(xlabel='Perturbation / scan half-width',ylabel='Arrival-time change (ms)',
           xlim=(-1.03,1.03),xticks=[-1,-.5,0,.5,1])
    fig.legend(loc='outside lower center',ncol=3,frameon=False,fontsize=8,
               handlelength=2.5,columnspacing=1.3)
    target=root/'results/sensitivity_linear';figdir=target/'figures';figdir.mkdir(parents=True,exist_ok=True)
    for ext in ['pdf','png','svg']:
        fig.savefig(figdir/f'one_factor_time_response.{ext}',dpi=300,bbox_inches='tight')
    svg=figdir/'one_factor_time_response.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    plt.close(fig)
    result=dict(layout='one axes; nine overlaid curves',normalized_x='perturbation divided by original scan half-width',
                y_units='milliseconds',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                no_new_simulation=True,curves=record)
    (target/'time_response_overlay_record.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    r=build_time_response()
    print('Nine arrival-time curves combined on one axes; all 369 saved points retained')
