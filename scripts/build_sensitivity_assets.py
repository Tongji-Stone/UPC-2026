"""Build paper-ready sensitivity tables and figures from reviewed saved results.

No fitting, trajectory integration or random sampling is performed here.
Mass and radius are excluded from the paper's perturbation analysis.
"""
import csv
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse,Rectangle

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'results/sensitivity_v2'; MC=ROOT/'results/monte_carlo'
OUT=ROOT/'results/sensitivity_v2'
BLUE='#0072B2';ORANGE='#D55E00';GRAY='#454B4B'

def js(path):return json.loads(path.read_text(encoding='utf-8'))
def csvrows(path):
    with path.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def scientific(value):
    a,b=f'{value:.2e}'.split('e')
    return a+r'\times10^{'+str(int(b))+'}'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    figdir=OUT/'figures';figdir.mkdir(exist_ok=True)
    comparison=[r for r in csvrows(DATA/'comparison.csv') if r['parameter'] not in ('mass','radius')]
    assert len(comparison)==9
    summary=js(MC/'summary.json');verification=js(MC/'verification.json')
    profile=js(DATA/'refinement_summary.json');convergence=js(MC/'convergence.json')
    assert verification['mass_kg']==.43 and verification['radius_m']==.11
    common={
        'SensitivityFixedRuns':'369',
        'SensitivityMaxDirection':'20.247',
        'SensitivityConditionalShift':f"{profile['wide']['max_displacement']:.4f}",
        'SensitivityConditionalResidual':scientific(profile['wide']['max_residual_m']),
        'MCCount':str(summary['count']),'MCSeed':str(verification['seed']),
        'MCMeanY':f"{summary['mean'][0]:.4f}",'MCMeanZ':f"{summary['mean'][1]:.4f}",
        'MCStdY':f"{summary['std'][0]:.4f}",'MCStdZ':f"{summary['std'][1]:.4f}",
        'MCMaxDisplacement':f"{summary['max_displacement']:.3f}",
        'MCClearCount':str(summary['clear']),'MCOverCount':str(summary['nonclear_at_plane']),
        'MCClearPercent':f"{100*summary['clear_fraction']:.2f}",
        'MCOverPercent':f"{100*(1-summary['clear_fraction']):.2f}",
        'MCJointThreshold':f"{summary['ellipse_95']['empirical_d2_threshold']:.4f}",
        'MCAdaptiveError':scientific(verification['maximum_adaptive_difference_m']),
        'MCHalfStepError':scientific(verification['maximum_half_step_difference_m']),
        'MCCheckCount':str(len(verification['adaptive_integrator_comparisons']))}
    for key in ('y','z','t'):
        change=max(abs(np.array(convergence[-1][key+'_central_95'])-convergence[-2][key+'_central_95']))
        common['MCConvergence'+key.upper()]=f'{change*1000:.3f}'
    labels={'speed':('Launch speed','初速度大小'),'yaw':('Velocity azimuth','初速度水平角'),
        'pitch':('Velocity elevation','初速度仰角'),'spin':('Spin magnitude','自旋大小'),
        'spin_yaw':('Spin-axis azimuth','旋转轴方位角'),'spin_pitch':('Spin-axis elevation','旋转轴仰角'),
        'ad':('Drag multiplier','阻力修正系数'),'al':('Lift multiplier','升力修正系数'),'rho':('Air density','空气密度')}
    for language,directory in [('en',ROOT/'paper'),('zh',ROOT/'_中文版')]:
        zh=language=='zh'
        text='% Generated from reviewed sensitivity data; keep mass and radius fixed.\n'
        text+='\n'.join('\\newcommand{\\'+key+'}{'+value+'}' for key,value in common.items())+'\n'
        caption=('单参数扰动对球门交点和到达时间的影响。' if zh else
                 'Goal-plane displacement and arrival-time change under one-factor perturbations.')
        header=(r'参数 & 比较扰动 & $\max D_g$ (cm) & $\max|\Delta t_g|$ (ms)' if zh else
                r'Parameter & Perturbation & $\max D_g$ (cm) & $\max|\Delta t_g|$ (ms)')
        body='\n'.join(labels[r['parameter']][int(zh)]+' & '+
                       (r'$\pm1^\circ$' if r['unit']=='degree' else r'$\pm5\%$')+
                       f" & {100*float(r['max_displacement']):.3f} & {float(r['max_time_ms']):.3f}"+r'\\' for r in comparison)
        text+=r'\newcommand{\SensitivityOneFactorTable}{\begin{table}[H]\centering\small'+'\n'+r'\caption{'+caption+r'}\label{tab:sensitivity-one-factor}'+'\n'+r'\begin{tabular}{p{.32\textwidth}crr}\toprule'+'\n'+header+r'\\\midrule'+'\n'+body+'\n'+r'\bottomrule\end{tabular}\end{table}}'+'\n'
        caption=('早期位置约束下的球门交点范围。' if zh else
                 'Ranges of goal-plane crossings compatible with the early positions.')
        header=('两项修正系数范围 & $y_g$ (m) & $z_g$ (m) & $t_g$ (s)' if zh else
                'Range of each multiplier & $y_g$ (m) & $z_g$ (m) & $t_g$ (s)')
        body=[]
        for title,key in [('[0.9,1.1]','inner'),('[0.8,1.2]','wide')]:
            r=profile[key]
            body.append('$'+title+'$ & '+' & '.join(f'{r[k][0]:.4f}--{r[k][1]:.4f}' for k in
                                              ['refined_y_range','refined_z_range','refined_t_range'])+r'\\')
        text+=r'\newcommand{\SensitivityProfileTable}{\begin{table}[H]\centering\small'+'\n'+r'\caption{'+caption+r'}\label{tab:sensitivity-profile}'+'\n'+r'\begin{tabular}{lrrr}\toprule'+'\n'+header+r'\\\midrule'+'\n'+'\n'.join(body)+'\n'+r'\bottomrule\end{tabular}\end{table}}'+'\n'
        caption=('10 万条蒙特卡洛轨迹的交点与到达时间。' if zh else
                 'Monte Carlo crossing positions and arrival times (100,000 trajectories).')
        header=(r'输出量 & 样本最小值--最大值 & 单坐标中心 95\% 区间' if zh else
                r'Output & Sample minimum--maximum & Central 95\% interval, one coordinate')
        body=[]
        for name,key in [('$y_g$ (m)','y'),('$z_g$ (m)','z'),('$t_g$ (s)','t')]:
            body.append(name+' & '+' & '.join(f'{summary[k][0]:.4f}--{summary[k][1]:.4f}' for k in [key+'_range',key+'_central_95'])+r'\\')
        text+=r'\newcommand{\SensitivityMonteCarloTable}{\begin{table}[H]\centering\small'+'\n'+r'\caption{'+caption+r'}\label{tab:sensitivity-mc}'+'\n'+r'\begin{tabular}{lrr}\toprule'+'\n'+header+r'\\\midrule'+'\n'+'\n'.join(body)+'\n'+r'\bottomrule\end{tabular}\end{table}}'+'\n'
        (directory/'sensitivity_results.tex').write_text(text,encoding='utf-8')
    plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],'font.size':10,
        'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
    def save(fig,name):
        fig.savefig(figdir/f'{name}.pdf',bbox_inches='tight')
        fig.savefig(figdir/f'{name}.png',bbox_inches='tight',dpi=220)
        plt.close(fig)
    scans=[r for r in csvrows(DATA/'one_factor.csv') if r['parameter'] not in ('mass','radius')]
    assert len(scans)==369 and all(r['event']=='plane' for r in scans)
    order=['speed','yaw','pitch','spin','spin_yaw','spin_pitch','ad','al','rho']
    for quantity in ['position','time']:
        if quantity=='time':
            from build_time_response_plot import build_time_response
            build_time_response(ROOT)
            continue
        fig,axes=plt.subplots(3,3,figsize=(6.4,5.9),layout='constrained')
        for i,(ax,key) in enumerate(zip(axes.flat,order)):
            group=sorted([r for r in scans if r['parameter']==key],key=lambda r:float(r['delta']))
            relative=group[0]['unit']=='relative'
            x=np.array([float(r['delta']) for r in group])*(100 if relative else 1)
            if quantity=='position':
                ax.plot(x,[100*float(r['dy']) for r in group],color=BLUE,lw=1.3,label=r'$\Delta y_g$')
                ax.plot(x,[100*float(r['dz']) for r in group],color=ORANGE,lw=1.3,ls='--',label=r'$\Delta z_g$')
            else:
                ax.plot(x,[1000*float(r['dt']) for r in group],color=GRAY,lw=1.3,label=r'$\Delta t_g$')
            ax.axhline(0,color=GRAY,lw=.5,alpha=.7)
            ax.axvline(0,color=GRAY,lw=.5,ls=':',alpha=.7)
            ax.set_title('('+chr(97+i)+') '+labels[key][0],fontsize=9)
            ax.set_xlabel('Change (%)' if relative else 'Change (degrees)',fontsize=8)
            ax.tick_params(labelsize=8)
            ax.locator_params(axis='y',nbins=4)
        if quantity=='position':
            handles,legend=axes[0,0].get_legend_handles_labels()
            fig.legend(handles,legend,loc='outside upper center',ncol=2,frameon=False,fontsize=9)
            fig.supylabel('Goal-plane position change (cm)',fontsize=10)
        else:fig.supylabel('Arrival-time change (ms)',fontsize=10)
        save(fig,'one_factor_'+quantity+'_response')
    points=[r for r in csvrows(DATA/'profile.csv') if r['event']=='plane']
    points += [r for r in csvrows(DATA/'extrema.csv') if r['scope']=='wide']
    fig,ax=plt.subplots(figsize=(6.4,2.9),layout='constrained')
    sc=ax.scatter([float(r['y']) for r in points],[float(r['z']) for r in points],
        c=[float(r['ad']) for r in points],cmap='cividis',s=18)
    ax.scatter([2.682644507905514],[1.9592312099350713],marker='*',s=90,color=ORANGE,zorder=5)
    ax.set(xlabel='Goal y (m)',ylabel='Goal z (m)')
    fig.colorbar(sc,ax=ax,label='Drag multiplier')
    save(fig,'conditional_crossings')
    sample=np.load(MC/'samples.npz');p=sample['point'][sample['event']==0,1:3]
    fig,ax=plt.subplots(figsize=(6.4,3.7),layout='constrained')
    hb=ax.hexbin(p[:,0],p[:,1],gridsize=55,mincnt=1,bins='log',cmap='cividis',linewidths=0)
    ax.scatter([2.682644507905514],[1.9592312099350713],marker='*',s=85,color=ORANGE,
               edgecolor='white',linewidth=.4,label='Paper representative',zorder=5)
    e=summary['ellipse_95'];values,vectors=np.linalg.eigh(e['covariance']);order=values.argsort()[::-1]
    values=values[order];vectors=vectors[:,order]
    angle=np.degrees(np.arctan2(vectors[1,0],vectors[0,0]))
    ax.add_patch(Ellipse(e['center'],2*np.sqrt(e['empirical_d2_threshold']*values[0]),
        2*np.sqrt(e['empirical_d2_threshold']*values[1]),angle=angle,fill=False,lw=1.2,color=GRAY,label='95% joint sample ellipse'))
    ax.axhline(2.33,color=ORANGE,ls='--',lw=1,label='Ball-centre upper clearance')
    ax.set(xlabel='Goal y (m)',ylabel='Goal z (m)')
    fig.colorbar(hb,ax=ax,label='Samples per hexagon (log scale)')
    fig.legend(loc='outside upper center',ncol=2,frameon=False,fontsize=8)
    save(fig,'monte_carlo_crossings')
    fig,axes=plt.subplots(1,2,figsize=(6.4,2.6),layout='constrained')
    ns=np.array([r['n'] for r in convergence])
    for ax,key in zip(axes,['y','z']):
        ranges=np.array([r[key+'_range'] for r in convergence]);central=np.array([r[key+'_central_95'] for r in convergence])
        ax.fill_between(ns,ranges[:,0],ranges[:,1],color=BLUE,alpha=.12,label='Sample min-max')
        for i in (0,1):
            ax.plot(ns,ranges[:,i],color=BLUE,ls=':',marker='.',lw=1)
            ax.plot(ns,central[:,i],color=ORANGE,marker='o',ms=3,lw=1,
                    label='Central 95%, one coordinate' if i==0 else None)
        ax.set(xscale='log',xlabel='Number of samples',ylabel='Goal '+key+' (m)')
    axes[0].legend(frameon=False,fontsize=7,loc='center')
    save(fig,'monte_carlo_convergence')
    from build_monte_carlo_parallel import build_parallel_coordinates
    build_parallel_coordinates(ROOT)
    sources=[DATA/'comparison.csv',DATA/'one_factor.csv',DATA/'refinement_summary.json',DATA/'profile.csv',DATA/'extrema.csv',
             MC/'summary.json',MC/'verification.json',MC/'samples.npz',MC/'convergence.json',
             ROOT/'data/sensitivity_v2/parallel_display.json']
    record=dict(fixed_mass_kg=.43,fixed_radius_m=.11,one_factor_parameters=9,
        one_factor_runs=369,monte_carlo_primary_count=summary['count'],monte_carlo_seed=verification['seed'],
        sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        policy='Publication assets reuse reviewed computations; no refitting or new samples',
        provenance='Saved deterministic M4 sensitivity and seeded Monte Carlo results')
    (OUT/'asset_manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Bilingual sensitivity tables and six paper figure sets created')

if __name__=='__main__':main()
