"""Plot only from saved CSVs; run compute_aerodynamic_comparison.py first."""
import csv
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/processed/aerodynamic_parameters'
SRC=ROOT/'data/sources/aerodynamic_parameters'
OUT=ROOT/'results/aerodynamic_parameters'
FONT=Path('C:/Windows/Fonts/msyh.ttc')
if FONT.exists():
    font_manager.fontManager.addfont(str(FONT))
    plt.rcParams['font.family']=font_manager.FontProperties(fname=FONT).get_name()
plt.rcParams.update({'font.size':10,'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','savefig.facecolor':'white','axes.titlepad':12})
COLORS=['#b65b3e','#3b7568','#62778d','#9a7d3b','#6f596c']


def read_csv(path):
    with path.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))


def numbers(rows,x,y):return np.array([float(r[x]) for r in rows]),np.array([float(r[y]) for r in rows])


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=read_csv(DATA/'参数对照.csv');points=read_csv(SRC/'asai2007_digitized.csv');summary=json.loads((DATA/'summary.json').read_text(encoding='utf-8'))
    def select(case,model,coefficient=None):return [r for r in rows if r['case']==case and r['model']==model and (coefficient is None or r['coefficient']==coefficient)]
    def measured(fig):return [r for r in points if r['ball']=='Teamgeist' and r['figure']==fig]
    def curve(ax,case,model,label,color,style='-',coefficient=None,max_sp=None):
        q=select(case,model,coefficient)
        if max_sp is not None:q=[r for r in q if float(r['Sp'])<=max_sp]
        x,y=numbers(q,'v_m_s' if case=='nonspin_curve' else 'Sp','model_value')
        ax.plot(x,y,label=label,color=color,linestyle=style,lw=1.8)
    def finish(fig,name,caption):
        fig.text(.02,.012,caption,ha='left',va='bottom',fontsize=8,color='#555555')
        fig.tight_layout(rect=(0,.07,1,1),h_pad=2.5,w_pad=2.5)
        for ax in fig.axes:ax.grid(alpha=.15);ax.tick_params(direction='out')
        fig.savefig(OUT/f'{name}.png',dpi=300)
        fig.savefig(OUT/f'{name}.svg')
        plt.close(fig)
    # 1: distinguish the original Re coordinates from the reconstructed v scale.
    fig,axs=plt.subplots(1,2,figsize=(11.5,4.5))
    for ax in axs:
        curve(ax,'nonspin_curve','G10_CD_v','Goff 2010 式(3)',COLORS[0])
        curve(ax,'nonspin_curve','KL18_CD_v','Kiratidis 2018 式(5)',COLORS[1],'--')
        p=measured('fig4');x=np.array([float(q['Re'])*1.45e-5/.22 for q in p]);y=np.array([float(q['value']) for q in p])
        ax.scatter(x,y,s=25,marker='^',facecolors='white',edgecolors='#252525',label='Asai 2007 图4：Teamgeist',zorder=4)
        ax.axvspan(30.377,32.560,color='#bbb8b1',alpha=.25,label='题目初段速度范围')
        ax.set(xlabel='相对空气速度 v (m/s)',ylabel=r'$C_D$')
    axs[0].set(title='(a) 无旋转阻力：整体关系',xlim=(5,35),ylim=(.10,.55));axs[0].legend(fontsize=8)
    axs[1].set(title='(b) 题目速度附近',xlim=(25,35),ylim=(.13,.17))
    finish(fig,'01_nonspin_drag','实验点速度按原图 Re 与 22–30 m/s 图例对应关系换算；球径 0.22 m，重建 ν≈1.45e-5 m²/s。原始 Re 保留在 CSV。')
    # 2: main and auxiliary plots; adjacent-Re data are not relabeled as problem-Re data.
    fig,axs=plt.subplots(2,2,figsize=(11.5,8.7))
    for ax,coef in zip(axs[0],['CD','CL']):
        if coef=='CD':
            curve(ax,'problem_main','G10_CD_piecewise','Goff 2010 分段式',COLORS[0],max_sp=.35)
            curve(ax,'problem_main','KL18_CD_ReSp','Kiratidis 2018 完整式',COLORS[1],'--',max_sp=.35)
        else:
            curve(ax,'problem_main','KL18_CL_ReSp','2018 式(9)：完整升力',COLORS[1],max_sp=.35)
            curve(ax,'problem_main','KL18_CL_Sp','2018 式(8)：参考幂律',COLORS[0],':',max_sp=.35)
        q=[r for r in points if r['ball']=='Teamgeist' and r['figure']==('fig8' if coef=='CD' else 'fig9') and float(r['Re'])==455172]
        x,y=numbers(q,'Sp','value');ax.scatter(x,y,facecolors='white',edgecolors='#252525',s=40,label='邻近实测 Re=455172',zorder=5)
        # Auxiliary viscosity scenario has an in-domain, piecewise-linear experimental reference.
        q=[r for r in rows if r['case']=='problem_nu154' and r['model']==('KL18_CD_ReSp' if coef=='CD' else 'KL18_CL_ReSp') and r['reference_value']]
        x,y=numbers(q,'Sp','reference_value');ax.plot(x,y,color=COLORS[2],lw=2.2,label='实测插值 Re=449446（辅助情景）')
        ax.set(xlabel='旋转参数 Sp',ylabel=r'$C_'+coef[1]+r'$',xlim=(0,.35),ylim=(0,.5 if coef=='CL' else .4),title=f'({"a" if coef=="CD" else "b"}) 题目主情景 Re={summary["representative_Re"]:.0f}')
        ax.legend(fontsize=8,loc='upper left')
    for ax,coef in zip(axs[1],['CD','CL']):
        models=['G10_CD_piecewise','KL18_CD_ReSp'] if coef=='CD' else ['KL18_CL_ReSp','KL18_CL_Sp']
        colors=COLORS[:2] if coef=='CD' else [COLORS[1],COLORS[0]]
        labels=['2010 分段阻力','2018 完整阻力'] if coef=='CD' else ['2018 完整升力','2018 参考幂律']
        for m,color,style,label in zip(models,colors,['-','--'],labels):curve(ax,'problem_main',m,label,color,style)
        ax.axvspan(.35,1,color='#e8e1d8',alpha=.6)
        ax.set(xlabel='旋转参数 Sp',ylabel=r'$C_'+coef[1]+r'$',xlim=(0,1),title=f'({"c" if coef=="CD" else "d"}) 大旋转参数延伸：着色区为外推展示')
        ax.legend(fontsize=8)
    finish(fig,'02_spin_coefficients','v=31.461 m/s；主 ν=1.50e-5，辅助 ν=1.54e-5 m²/s。邻近实测点与主情景 Re 不同；实测插值仅画共同覆盖区。')
    # 3: residual scatter by Re; high-Re RMSE comparison.
    fig,axs=plt.subplots(2,2,figsize=(11.5,8.7))
    for ax,case,model in [(axs[0,0],'experimental_fig8','G10_CD_piecewise'),(axs[0,1],'experimental_fig8','KL18_CD_ReSp'),(axs[1,0],'experimental_fig9','KL18_CL_ReSp')]:
        q=select(case,model)
        for re,col,marker in zip(sorted(set(float(r['Re']) for r in q)),COLORS,['s','^','v','o','D']):
            group=[r for r in q if float(r['Re'])==re];x,y=numbers(group,'Sp','difference')
            ax.scatter(x,y,color=col,marker=marker,label=f'Re={re:.0f}',s=34)
        bound=max(float(r['reference_read_bound']) for r in q)
        ax.axhspan(-bound,bound,color='#dedbd5',alpha=.6);ax.axhline(0,color='#666',lw=.7)
        ax.set(xlabel='原实验 Sp',ylabel='公式值 − 实测提点值',title=model.replace('_',' '),ylim=(-.09,.09))
    axs[0,0].legend(fontsize=7,ncol=2)
    ax=axs[1,1];metrics=[m for m in summary['metrics'] if m['scope']=='high_Re_ge394482' and m['case'] in ['experimental_fig8','experimental_fig9'] and m['model']!='KL18_CL_Sp']
    labels=[m['model'].replace('Repo_','原默认 ').replace('_',' ') for m in metrics]
    y=np.arange(len(metrics));ax.barh(y,[m['RMSE'] for m in metrics],color=[COLORS[0] if m['case'].endswith('8') else COLORS[1] for m in metrics],height=.6)
    ax.set(yticks=y,yticklabels=labels,xlabel='RMSE（系数）',title='邻近高 Re 三组数据：每模型 n=15',xlim=(0,.10));ax.tick_params(axis='y',labelsize=8);ax.invert_yaxis()
    finish(fig,'03_experimental_residuals','各公式在原实验 Re、Sp 上评估；灰带仅表示 ±1 PDF pt 的纵坐标读取界限，不是实验置信区间。共享拟合数据的比较属于重现误差。')
    # 4: distinguish dimensionless coefficients and dimensional torque.
    fig,axs=plt.subplots(2,2,figsize=(11.5,8.5))
    for ax,coef,title in [(axs[0,0],'CQ_v','(a) 平动动压归一化'),(axs[0,1],'CQ_omega','(b) 旋转动压归一化'),(axs[1,0],'Q_Nm','(c) 实际阻尼力矩大小')]:
        for m,c,style,lab in [('MuJoCo381_highRe',COLORS[0],'-','高 Re 二次项'),('MuJoCo381_total',COLORS[1],'--','二次项 + 黏性项')]:
            q=[r for r in select('torque',m,coef) if float(r['Sp'])<=.35 and r['model_value']!='']
            x,y=numbers(q,'Sp','model_value');ax.plot(x,y,color=c,ls=style,label=lab,lw=1.8)
        ax.set(xlabel='Sp',ylabel={'CQ_v':r'$C_{Q,v}$','CQ_omega':r'$C_{Q,\omega}$','Q_Nm':'|Q| (N m)'}[coef],title=title,xlim=(0,.35));ax.legend(fontsize=8)
    axs[0,1].set_ylim(1.598,1.616)
    ax=axs[1,1];decay=read_csv(DATA/'spin_decay_sensitivity.csv')
    for ca,c in zip([.75,1.5,3],COLORS):
        q=[r for r in decay if float(r['Cangular'])==ca]
        t,fraction=numbers(q,'t_s','omega_fraction')
        ax.plot(t,fraction,color=c,label=f'Cangular={ca:g}')
    ax.axhline(1,color='#666',ls=':',label='固定旋转参考')
    ax.set(xlabel='时间 (s)',ylabel=r'$\omega(t)/\omega_0$',title='(d) 二次阻尼的转速敏感性（初始 Sp=0.2）',ylim=(0,1.04));ax.legend(fontsize=8)
    finish(fig,'04_spin_damping','软件默认 Cangular=1.5；v=31.461 m/s。右下假定薄球壳 I=2mr²/3、仅二次力矩；0.75 与 3 是敏感性情景，无足球力矩实测标定。')
    print('Saved 4 figure groups: SVG + 300 DPI PNG.')


if __name__=='__main__':main()
