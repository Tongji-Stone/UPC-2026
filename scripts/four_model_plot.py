"""Publication figures from cached report-v2 results; no fitting or integration."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/structure_v2';FIG=OUT/'figures'
MODELS=['M1','M2','M3','M4'];COLORS=['#454B4B','#0072B2','#D55E00','#009E73'];STYLES=['-', '--','-.',':']
def js(p):return json.loads((OUT/p).read_text(encoding='utf-8'))
def rows(p):
    with p.open(encoding='utf-8') as f:return list(csv.DictReader(f))
def column(r,k):return np.array([float(a[k]) for a in r])
def trace(group,case,model):return rows(OUT/f'{group}/{case}_{model}.csv')
def save(fig,name):
    fig.tight_layout()
    for ext in ['pdf','svg','png']:fig.savefig(FIG/f'{name}.{ext}',dpi=300)
    plt.close(fig)
def lines(ax,group,case,x,y):
    for m,c,s in zip(MODELS,COLORS,STYLES):
        if not (OUT/f'{group}/{case}_{m}.csv').exists():continue
        if group in ['problem','matches'] and js(f'{group}/{case}_{m}.json')['record']['status']=='fit_failure':continue
        r=trace(group,case,m);ax.plot(column(r,x),column(r,y),label=m,color=c,ls=s,lw=1.5)

def main():
    FIG.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],'font.size':10,
        'axes.spines.right':False,'axes.spines.top':False,'pdf.fonttype':42,'svg.fonttype':'none'})
    forward=js('forward/summary.json')
    fig,axes=plt.subplots(1,2,figsize=(6.4,2.7))
    lines(axes[0],'forward','zero_spin','x_m','z_m')
    obs=rows(ROOT/'data/report_v2/zero_spin.csv')
    axes[0].scatter(column(obs,'x_m'),column(obs,'z_m'),s=10,color='black',label='Measured early path',zorder=5)
    axes[0].scatter([21.9],[.109],s=35,marker='x',color='black',label='Measured landing')
    axes[0].set(xlabel='x (m)',ylabel='z (m)');axes[0].legend(fontsize=7,frameon=False)
    rr=[r for r in forward['records'] if r['case']=='zero_spin']
    axes[1].axhline(21.9,color='black',lw=1,label='Measured 21.9 m')
    for i,r in enumerate(rr):axes[1].scatter(i,r['predicted_range_m'],s=40,color=COLORS[i],marker=['o','s','^','D'][i])
    axes[1].set(xticks=range(4),xticklabels=MODELS,ylabel='Landing x (m)');axes[1].legend(fontsize=8,frameon=False)
    save(fig,'forward_range')
    fig,axes=plt.subplots(2,2,figsize=(6.4,4.6))
    for ax,case in zip(axes.flat,forward['cases'][1:]):
        for m,c,s in zip(MODELS,COLORS,STYLES):
            r=trace('forward',case['case'],m);mask=column(r,'x_m')<=1.5
            ax.plot(column(r,'x_m')[mask],column(r,'z_m')[mask],color=c,ls=s,label=m,lw=1.3)
        obs=rows(ROOT/'data/report_v2'/case['observations'])
        ax.scatter(column(obs,'x_m'),column(obs,'z_m'),color='black',s=10,label='Digitized measurements',zorder=5)
        ax.set(xlabel='x (m)',ylabel='z (m)',xlim=(-.02,1.3),title=case['case'].replace('_',' ').title())
    axes[0,0].legend(frameon=False,fontsize=7)
    save(fig,'forward_topspin')
    fig,axes=plt.subplots(2,3,figsize=(6.4,4.6))
    for i,case in enumerate(['zero_spin','topspin_b']):
        for j,(field,label) in enumerate([('speed_m_s','Speed (m/s)'),('drag_N','Drag (N)'),('lift_N','Lift (N)')]):
            lines(axes[i,j],'forward',case,'time_s',field)
            axes[i,j].set(xlabel='Time (s)',ylabel=label,title=('Zero spin' if i==0 else 'Topspin b'))
    axes[0,0].legend(frameon=False,fontsize=8)
    save(fig,'forward_dynamics')
    fig,axes=plt.subplots(1,3,figsize=(6.4,2.5))
    for ax,coord in zip(axes[:2],['y_m','z_m']):
        lines(ax,'problem','problem_b','x_m',coord);ax.set(xlabel='x (m)',ylabel=coord[0]+' (m)')
        p=js('problem/problem_b_M4.json')['input']['positions_m'];p=np.array(p)
        ax.scatter(p[:,0],p[:,1 if coord=='y_m' else 2],color='black',s=15,zorder=5)
    axes[2].add_patch(Rectangle((-3.66,0),7.32,2.44,fill=False,color='gray'))
    for i,m in enumerate(MODELS):
        e=js(f'problem/problem_b_{m}.json')['record']['event']
        if e['type']=='plane':axes[2].scatter(e['position'][1],e['position'][2],color=COLORS[i],marker=['o','s','^','D'][i],s=25,label=m)
    axes[0].legend(fontsize=7,frameon=False);axes[2].set(xlabel='Goal y (m)',ylabel='Goal z (m)',xlim=(-3.9,3.9),ylim=(0,2.7))
    save(fig,'problem_prediction')
    fig,axes=plt.subplots(1,3,figsize=(6.4,2.5))
    for ax,(field,label) in zip(axes,[('speed_m_s','Speed (m/s)'),('drag_N','Drag (N)'),('lift_N','Lift (N)')]):
        lines(ax,'problem','problem_b','time_s',field);ax.set(xlabel='Time (s)',ylabel=label)
    axes[0].legend(frameon=False,fontsize=8);save(fig,'problem_dynamics')
    fig,axes=plt.subplots(1,3,figsize=(6.4,2.5))
    r=trace('problem','problem_b','M4')
    for ax,field,label in zip(axes,['CD','CL','Sp'],[r'$C_D$',r'$C_L$',r'$Sp$']):
        ax.plot(column(r,'time_s'),column(r,field),color=COLORS[3],lw=1.5)
        ax.set(xlabel='Time (s)',ylabel=label)
    save(fig,'problem_coefficients')
    matches=js('matches/summary.json')['records'];cases=list(dict.fromkeys(r['case'] for r in matches))
    fig,ax=plt.subplots(figsize=(6.4,3))
    for j,(m,c) in enumerate(zip(MODELS,COLORS)):
        rs=[next(r for r in matches if r['case']==case and r['model']==m) for case in cases]
        for i,r in enumerate(rs):
            x=i+(j-1.5)*.14
            if r['error_m'] is not None:ax.scatter(x,r['error_m'],color=c,marker=['o','s','^','D'][j],label=m if i==0 else None,s=30)
            else:ax.plot(x,-.3,marker='x',color=c,ms=6)
    labels=[('Penalty' if case.startswith('penalty') else ('WOH ' if case.startswith('J03WOH') else 'WQQ ')+case[-4:]) for case in cases]
    ax.set(xticks=range(len(cases)),xticklabels=labels,
        ylabel='Goal-plane error (m)');ax.axhline(0,color='gray',lw=.5);ax.legend(frameon=False,ncol=4,fontsize=8)
    save(fig,'inverse_errors')
    fig,axes=plt.subplots(1,2,figsize=(6.4,2.8))
    for ax,field in zip(axes,['y_m','z_m']):
        lines(ax,'matches','penalty_18232100000995','x_m',field)
        rr=rows(ROOT/'data/report_v2/penalty.csv');xx=column(rr,'x_m');yy=column(rr,'y_m' if field=='y_m' else 'z_raw')
        if field=='y_m':yy-=yy[0]
        ax.scatter(xx-xx[0],yy,color='black',s=13,label='Tracking measurements',zorder=5)
        ax.set(xlabel='Local x (m)',ylabel=field[0]+' (m)')
    axes[0].legend(fontsize=7,frameon=False);save(fig,'penalty_prediction')
    fig,axes=plt.subplots(1,3,figsize=(6.4,2.6))
    for label,color,style in [('constant_spin',COLORS[1],'-'),('inertial_torque',COLORS[2],'--')]:
        r=rows(OUT/f'other/{label}.csv');name='Constant spin' if label=='constant_spin' else 'Quadratic torque'
        axes[0].plot(column(r,'time_s'),column(r,'omega_rad_s'),color=color,ls=style,label=name)
        for ax,field in zip(axes[1:],['y_m','z_m']):ax.plot(column(r,'x_m'),column(r,field),color=color,ls=style,label=name)
    axes[0].set(xlabel='Time (s)',ylabel='Spin (rad/s)');axes[1].set(xlabel='x (m)',ylabel='y (m)');axes[2].set(xlabel='x (m)',ylabel='z (m)')
    axes[0].legend(frameon=False,fontsize=7);save(fig,'torque_comparison')
    # Figure contract and audit make the link from quantities to claims explicit.
    (FIG/'figure_contract.json').write_text(json.dumps(dict(width_inches=6.4,formats=['pdf','svg','png'],dpi=300,
        palette=COLORS,encoding='colour plus line style or marker',
        claims={'forward_range':'range response to gravity, constant and variable drag',
        'forward_topspin':'measured local curvature and model differences',
        'forward_dynamics':'physical speed and force evolution',
        'inverse_errors':'individual event errors; crosses denote no goal-plane prediction',
        'torque_comparison':'same initial state, changed angular damping'},
        uncertainty='No synthetic error bars; individual experiments and deterministic simulations'),indent=2),encoding='utf-8')
    print('nine figure groups exported as PDF/SVG/300-dpi PNG')

if __name__=='__main__':main()
