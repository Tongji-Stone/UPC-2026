"""Render paper figures from saved coupled-model results, without integration."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT=Path(__file__).resolve().parents[1]/'results/coupled_model'
FIG=ROOT/'figures'
COLORS=['#0072B2','#D55E00','#009E73','#CC79A7']


def js(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def rows(path):
    with (ROOT/path).open(encoding='utf-8') as f:return list(csv.DictReader(f))
def xy(data,x,y):return [float(r[x]) for r in data],[float(r[y]) for r in data]
def finish(fig,name):
    fig.tight_layout()
    for ext in ('pdf','png','svg'):fig.savefig(FIG/f'{name}.{ext}',dpi=300)
    plt.close(fig)


def main():
    FIG.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],
        'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
        'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none'})
    s=js('problem/summary.json');obs=rows('problem/observations.csv')
    traces=[rows(f'problem/trajectory_candidate_{i}.csv') for i in range(len(s['candidate_predictions']))]
    fig,axes=plt.subplots(1,3,figsize=(7.2,2.7))
    for i,trace in enumerate(traces):
        label=f'Fit {chr(65+i)}';color=COLORS[i%len(COLORS)];style=['-','--'][i%2]
        axes[0].plot(*xy(trace,'x_m','y_m'),color=color,ls=style,label=label)
        axes[1].plot(*xy(trace,'x_m','z_m'),color=color,ls=style)
        e=s['candidate_predictions'][i]['event']
        if e['type']=='plane':axes[2].plot(e['position'][1],e['position'][2],marker=['o','s'][i%2],color=color,ls='none',label=label)
    for ax,coord in zip(axes[:2],('y_m','z_m')):
        ax.scatter(*xy(obs,'x_m',coord),color='#333333',s=14,zorder=4)
        ax.axvline(11,color='#777777',lw=.7,ls=':');ax.set_xlabel('x (m)')
    axes[0].set_ylabel('y (m)');axes[1].set_ylabel('z (m)')
    axes[2].add_patch(Rectangle((-3.66,0),7.32,2.44,fill=False,lw=1,color='#777777'))
    axes[2].set(xlabel='Goal y (m)',ylabel='Goal z (m)',xlim=(-3.9,3.9),ylim=(0,2.7))
    axes[0].legend(frameon=False,fontsize=8);axes[2].legend(frameon=False,fontsize=8,loc='upper left')
    finish(fig,'prediction')

    fig,axes=plt.subplots(2,3,figsize=(7.2,4.6))
    fields=[('omega_rad_s',r'Spin $|\omega|$ (rad/s)'),('CD',r'$C_D$'),('CL',r'$C_L$'),
            ('CQ_v',r'$C_{Q,v}$'),('torque_Nm','Torque magnitude (N m)'),('Sp','Spin parameter Sp')]
    for ax,(field,label) in zip(axes.flat,fields):
        for i,trace in enumerate(traces):ax.plot(*xy(trace,'time_s',field),color=COLORS[i%4],ls=['-','--'][i%2],label=f'Fit {chr(65+i)}')
        ax.set(xlabel='Time (s)',ylabel=label)
    axes[0,0].legend(frameon=False,fontsize=8)
    finish(fig,'state_evolution')

    fig,axes=plt.subplots(1,2,figsize=(6.5,2.8))
    for i,c in enumerate(s['fit']['candidates']):
        sv=np.array(c['singular_values']);axes[0].semilogy(range(1,7),sv,color=COLORS[i%4],marker=['o','s'][i%2],ls=['-','--'][i%2],label=f'Fit {chr(65+i)}')
        e=s['candidate_predictions'][i]['event']
        if e['type']=='plane':
            y,z=e['position'][1:];axes[1].plot(y,z,marker=['o','s'][i%2],color=COLORS[i%4]);axes[1].annotate(f' {chr(65+i)}',(y,z),xytext=(4,4),textcoords='offset points')
    axes[0].set(xlabel='Singular-value index',ylabel='Scaled Jacobian singular value',xticks=range(1,7));axes[0].legend(frameon=False,fontsize=8)
    axes[1].set(xlabel='Goal y (m)',ylabel='Goal z (m)');axes[1].ticklabel_format(useOffset=False)
    finish(fig,'identifiability')

    scan=rows('sensitivity/scan.csv');factors=list(js('sensitivity/summary.json')['groups'])
    labels=dict(speed_scale='Launch-speed multiplier',azimuth_deg='Horizontal rotation (deg)',
                spin_scale='Initial-spin multiplier',angular_drag_scale='Angular-drag multiplier')
    fig,axes=plt.subplots(2,2,figsize=(7.2,4.8))
    for ax,factor in zip(axes.flat,factors):
        group=[r for r in scan if r['factor']==factor and r['event']=='plane']
        ax.plot(*xy(group,'value','y_m'),color=COLORS[0],label='y',lw=1.5)
        ax.plot(*xy(group,'value','z_m'),color=COLORS[1],ls='--',label='z',lw=1.5)
        ax.set(xlabel=labels[factor],ylabel='Goal-plane coordinate (m)')
        ax.legend(frameon=False,fontsize=8)
    finish(fig,'sensitivity')

    real=js('real/summary.json');fig,axes=plt.subplots(1,2,figsize=(7.2,2.8))
    x=np.arange(len(real['records']))
    for i,record in enumerate(real['records']):
        if record.get('error_m') is not None:axes[0].bar(i,record['error_m'],width=.6,color=COLORS[0])
        else:axes[0].text(i,.2,record['status'],ha='center',rotation=90,fontsize=8)
        axes[1].bar(i,record.get('max_fit_residual_m',0),width=.6,color=COLORS[1])
    for ax in axes:ax.set(xticks=x,xticklabels=[f'Event {i+1}' for i in x])
    axes[0].set_ylabel('Goal-plane error (m)');axes[1].set_ylabel('Maximum input residual (m)')
    finish(fig,'real_validation')

    data=rows('surface/trajectories.csv');fig,ax=plt.subplots(figsize=(5.8,2.9))
    for i,name in enumerate(('Teamgeist KL18','Smooth sphere')):
        group=[r for r in data if r['law']==name];ax.plot(*xy(group,'x_m','z_m'),color=COLORS[i],ls=['-','--'][i],label=name)
    ax.set(xlabel='x (m)',ylabel='z (m)');ax.legend(frameon=False,fontsize=9)
    finish(fig,'surface_comparison')
    print('Saved six figure groups (vector PDF/SVG and 300 DPI PNG).')


if __name__=='__main__':main()
